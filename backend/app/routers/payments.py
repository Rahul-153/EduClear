from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field, NaiveDatetime
from sqlmodel import Session, select

from ..config import settings
from ..db import Booking, LedgerEntry, get_session
from ..integrations.paypal import MockPayPal, PayPal, PayPalError, get_paypal, inr_to_usd_cents
from ..services import kit as kit_service
from ..services import payments as svc
from ..services.programs import COUNSELLOR, PROGRAMS, slots

router = APIRouter(prefix="/api")


def owner(x_client_id: Optional[str] = Header(None)) -> str:
    if not x_client_id or not 8 <= len(x_client_id) <= 64:
        raise HTTPException(400, "X-Client-Id header (8-64 chars) required")
    return x_client_id


def guard(fn, *a, **k):
    try:
        return fn(*a, **k)
    except svc.BookingError as e:
        raise HTTPException(e.status, str(e))


def view(b: Booking, s: Session) -> dict:
    prog = PROGRAMS.get(b.program)
    led = s.exec(select(LedgerEntry).where(LedgerEntry.booking_id == b.id)).all()
    return {"id": b.id, "program": b.program, "title": prog.title if prog else "Student tech kit", "amount_inr": b.amount_inr,
            "usd": f"{b.usd_cents / 100:.2f}", "slot_start": b.slot_start, "status": b.status, "paypal_order_id": b.paypal_order_id,
            "payout_batch_id": b.payout_batch_id, "note": b.note,
            "ledger": [{"kind": e.kind, "usd": f"{e.amount_usd_cents / 100:.2f}", "ref": e.paypal_ref} for e in led]}


@router.get("/payments/config")
def payments_config(pp: PayPal = Depends(get_paypal)):
    return {"mode": pp.mode, "currency_note": f"Prices are shown in rupees; PayPal sandbox charges USD at a fixed demo rate of 1 INR = {settings.inr_to_usd_rate} USD.",
            "escrow_note": "Escrow here means the sandbox payment is held in the platform's ledger and released to the counsellor through PayPal Payouts after you confirm the session. PayPal has no separate escrow product.",
            "client_id": settings.paypal_client_id if pp.mode == "live-sandbox" else None, "environment": "sandbox",
            "counsellor": COUNSELLOR}


@router.get("/programs")
def programs():
    return [{"id": p.id, "title": p.title, "kind": p.kind, "minutes": p.minutes, "price_inr": p.price_inr,
             "usd": f"{inr_to_usd_cents(p.price_inr) / 100:.2f}", "escrow": p.escrow, "capacity": p.capacity, "summary": p.summary}
            for p in PROGRAMS.values()]


@router.get("/programs/{pid}/slots")
def program_slots(pid: str, s: Session = Depends(get_session)):
    p = PROGRAMS.get(pid)
    if not p:
        raise HTTPException(404, "unknown program")
    return [{"start": sl, "left": max(0, p.capacity - svc.taken(s, pid, sl))} for sl in slots(p)]


class BookIn(BaseModel):
    program_id: str
    slot_start: NaiveDatetime


@router.post("/bookings")
def book(body: BookIn, o: str = Depends(owner), s: Session = Depends(get_session), pp: PayPal = Depends(get_paypal)):
    return view(guard(svc.create_booking, s, pp, o, body.program_id, body.slot_start), s)


@router.get("/bookings")
def my_bookings(o: str = Depends(owner), s: Session = Depends(get_session), pp: PayPal = Depends(get_paypal)):
    svc.expire_stale(s, pp)
    rows = s.exec(select(Booking).where(Booking.owner == o).order_by(Booking.id.desc())).all()  # type: ignore[attr-defined]
    return [view(b, s) for b in rows]


class ApproveIn(BaseModel):
    approve: bool = True


@router.post("/bookings/{bid}/mock-approve")
def mock_approve(bid: int, body: ApproveIn, o: str = Depends(owner), s: Session = Depends(get_session), pp: PayPal = Depends(get_paypal)):
    if not isinstance(pp, MockPayPal):
        raise HTTPException(404, "mock approval exists only in mock mode")
    b = guard(svc._own, s, o, bid)
    try:
        pp.approve(b.paypal_order_id, body.approve)
    except PayPalError as e:
        raise HTTPException(e.status, str(e))
    return {"order_id": b.paypal_order_id, "approved": body.approve}


@router.post("/bookings/{bid}/capture")
def capture_ep(bid: int, o: str = Depends(owner), s: Session = Depends(get_session), pp: PayPal = Depends(get_paypal)):
    return view(guard(svc.capture, s, pp, o, bid), s)


@router.post("/bookings/{bid}/complete")
def complete_ep(bid: int, o: str = Depends(owner), s: Session = Depends(get_session), pp: PayPal = Depends(get_paypal)):
    return view(guard(svc.complete, s, pp, o, bid), s)


@router.post("/bookings/{bid}/cancel")
def cancel_ep(bid: int, o: str = Depends(owner), s: Session = Depends(get_session)):
    return view(guard(svc.cancel, s, o, bid), s)


@router.post("/webhooks/paypal")
async def paypal_webhook(request: Request, s: Session = Depends(get_session), pp: PayPal = Depends(get_paypal)):
    try:
        event = await request.json()
    except ValueError:
        raise HTTPException(400, "webhook body must be JSON")
    return guard(svc.process_webhook, s, pp, dict(request.headers), event)


@router.get("/kit")
def kit_ep(stream: str = "Computer Science"):
    return kit_service.kit(stream)


class KitOrderIn(BaseModel):
    item_ids: List[str] = Field(min_length=1)


@router.post("/kit/order")
def kit_order(body: KitOrderIn, o: str = Depends(owner), s: Session = Depends(get_session), pp: PayPal = Depends(get_paypal)):
    k = kit_service.kit()  # price is recomputed server-side; the client never sets the amount
    chosen = [i for i in k["items"] if i["id"] in set(body.item_ids)]
    if not chosen:
        raise HTTPException(422, "no valid kit items selected")
    total = sum(i["price_inr"] for i in chosen)
    b = guard(svc.create_booking, s, pp, o, "tech-kit", None, amount_inr=total, description="EduClear student tech kit")
    return {**view(b, s), "pay_in_4_usd": f"{b.usd_cents / 400:.2f}", "sample_data": k["sample_data"]}
