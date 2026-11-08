"""Booking, escrow ledger and payouts (FR-10, D-06). 'Escrow' = capture to the platform sandbox account plus an internal
ledger (funded -> released); release happens through the PayPal Payouts API when the session is confirmed complete."""
from datetime import datetime, timedelta
from typing import Optional

from sqlmodel import Session, select

from ..config import settings
from ..db import Booking, LedgerEntry, WebhookEvent
from ..integrations import paypal_mcp, zapier
from ..integrations.paypal import PayPal, PayPalError, inr_to_usd_cents
from .programs import PROGRAMS, slots

ACTIVE = ("escrow_funded", "paid", "payout_failed", "released")
PENDING_TTL = timedelta(minutes=15)


class BookingError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def _own(s: Session, owner: str, bid: int) -> Booking:
    b = s.get(Booking, bid)
    if not b or b.owner != owner:
        raise BookingError("booking not found", 404)
    return b


def taken(s: Session, program_id: str, slot: datetime) -> int:
    rows = s.exec(select(Booking).where(Booking.program == program_id, Booking.slot_start == slot,
                                        Booking.status.in_(ACTIVE))).all()  # type: ignore[attr-defined]
    return len(rows)


def create_booking(s: Session, pp: PayPal, owner: str, program_id: str, slot: Optional[datetime], *, amount_inr: Optional[int] = None,
                   description: Optional[str] = None, mcp_return_url: Optional[str] = None) -> Booking:
    if program_id == "tech-kit":
        if not amount_inr:
            raise BookingError("amount required for tech kit")
        price, desc = amount_inr, description or "EduClear student tech kit"
    else:
        prog = PROGRAMS.get(program_id)
        if not prog:
            raise BookingError("unknown program", 404)
        if slot is None or slot not in slots(prog):
            raise BookingError("choose one of the offered slots", 422)
        if taken(s, program_id, slot) >= prog.capacity:
            raise BookingError("this slot is full", 409)
        price, desc = prog.price_inr, f"EduClear: {prog.title}"
    cents = inr_to_usd_cents(price)
    b = Booking(owner=owner, program=program_id, amount_inr=price, usd_cents=cents, slot_start=slot)
    s.add(b); s.commit(); s.refresh(b)
    try:
        mcp_id = paypal_mcp.create_order(pp, cents, desc, mcp_return_url) if mcp_return_url else None
        order = {"id": mcp_id, "via": "paypal-mcp"} if mcp_id else pp.create_order(cents, f"booking-{b.id}", desc)
    except PayPalError as e:
        b.status, b.note = "cancelled", f"order creation failed: {e}"
        s.add(b); s.commit()
        raise BookingError(str(e), e.status)
    b.paypal_order_id = order["id"]
    if order.get("via") == "paypal-mcp":
        b.note = "order created through the PayPal MCP server"
    s.add(b); s.commit(); s.refresh(b)
    return b


def _mark_funded(s: Session, b: Booking, capture_id: str, usd_cents: int) -> bool:
    """Idempotent: a capture id is recorded once (unique ledger ref)."""
    if s.exec(select(LedgerEntry).where(LedgerEntry.paypal_ref == capture_id)).first():
        return False
    s.add(LedgerEntry(booking_id=b.id, kind="funded", amount_usd_cents=usd_cents, paypal_ref=capture_id))
    b.capture_id = capture_id
    if b.status in ("pending", "cancelled"):
        b.status = "paid" if (b.program == "tech-kit" or not PROGRAMS[b.program].escrow) else "escrow_funded"
    s.add(b); s.commit()
    if b.slot_start and b.program in PROGRAMS:  # calendar/meeting automation, best effort, no PII
        zapier.notify_booked(b.id, b.program, PROGRAMS[b.program].title, b.slot_start.isoformat(), b.amount_inr)
    return True


def capture(s: Session, pp: PayPal, owner: str, bid: int) -> Booking:
    b = _own(s, owner, bid)
    if b.status in ACTIVE:
        return b  # already funded: idempotent
    if b.status == "cancelled":
        raise BookingError("booking was cancelled", 409)
    if b.program != "tech-kit":
        if taken(s, b.program, b.slot_start) >= PROGRAMS[b.program].capacity:
            raise BookingError("this slot was taken by another booking before payment completed", 409)
    try:
        res = pp.capture_order(b.paypal_order_id)
    except PayPalError as e:
        raise BookingError(str(e), e.status)
    if res["status"] != "COMPLETED" or res.get("capture_status") not in ("COMPLETED", None):
        raise BookingError(f"payment not completed ({res['status']})", 402)
    _mark_funded(s, b, res["capture_id"], res["usd_cents"])
    s.refresh(b)
    return b


def expire_stale(s: Session, pp: PayPal) -> int:
    """Close bookings left 'pending' past the TTL so abandoned checkouts do not clutter the calendar. An order the buyer did
    approve (pop-up hung before the app heard back) is captured instead of cancelled, so a paid booking is never lost.
    PayPal outages (5xx) leave the booking pending for the next pass."""
    cutoff = datetime.utcnow() - PENDING_TTL
    stale = s.exec(select(Booking).where(Booking.status == "pending", Booking.created_at < cutoff)).all()  # type: ignore[attr-defined]
    closed = 0
    for b in stale:
        try:
            res = pp.capture_order(b.paypal_order_id) if b.paypal_order_id else None
            if res and res["status"] == "COMPLETED":
                _mark_funded(s, b, res["capture_id"], res["usd_cents"])
                continue
        except PayPalError as e:
            if e.status >= 500:
                continue
        b.status, b.note = "cancelled", "expired: not paid within 15 minutes"
        s.add(b); s.commit(); closed += 1
    return closed


def complete(s: Session, pp: PayPal, owner: str, bid: int) -> Booking:
    b = _own(s, owner, bid)
    if b.status == "released":
        return b
    if b.program == "tech-kit" or not PROGRAMS[b.program].escrow:
        raise BookingError("this booking is paid directly; nothing to release", 409)
    if b.status not in ("escrow_funded", "payout_failed"):
        raise BookingError(f"cannot release funds while booking is '{b.status}'", 409)
    receiver = settings.paypal_counsellor_payout_email or ("counsellor@example.test" if pp.mode == "mock" else "")
    if not receiver:
        raise BookingError("PAYPAL_COUNSELLOR_PAYOUT_EMAIL is not configured", 503)
    batch = f"educlear-booking-{b.id}"
    try:
        res = pp.payout(receiver, b.usd_cents, f"EduClear session payout, booking {b.id}", batch)
    except PayPalError as e:
        b.status, b.note = "payout_failed", f"payout failed: {e}"
        s.add(b); s.commit()
        raise BookingError(str(e), e.status)
    s.add(LedgerEntry(booking_id=b.id, kind="released", amount_usd_cents=b.usd_cents, paypal_ref=res["batch_id"]))
    b.status, b.payout_batch_id, b.note = "released", res["batch_id"], None
    s.add(b); s.commit(); s.refresh(b)
    return b


def cancel(s: Session, owner: str, bid: int) -> Booking:
    b = _own(s, owner, bid)
    if b.status != "pending":
        raise BookingError("only an unpaid booking can be cancelled here", 409)
    b.status = "cancelled"
    s.add(b); s.commit(); s.refresh(b)
    return b


def process_webhook(s: Session, pp: PayPal, headers: dict, event: dict) -> dict:
    if not pp.verify_webhook(headers, event):
        raise BookingError("invalid webhook signature", 401)
    eid, etype = event.get("id"), event.get("event_type", "")
    if not eid:
        raise BookingError("event id missing", 400)
    if s.get(WebhookEvent, eid):
        return {"status": "duplicate"}
    s.add(WebhookEvent(id=eid, event_type=etype)); s.commit()
    if etype == "PAYMENT.CAPTURE.COMPLETED":
        res = event.get("resource", {})
        order_id = res.get("supplementary_data", {}).get("related_ids", {}).get("order_id")
        b = s.exec(select(Booking).where(Booking.paypal_order_id == order_id)).first() if order_id else None
        if b and res.get("id"):
            _mark_funded(s, b, res["id"], round(float(res["amount"]["value"]) * 100))
            return {"status": "funded", "booking": b.id}
        return {"status": "ignored", "reason": "no matching booking"}
    return {"status": "ignored", "event_type": etype}
