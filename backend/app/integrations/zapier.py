"""Optional Zapier catch-hook (INT-08): tells a Zap that a session is paid so it can create the calendar event / meeting link.
Best effort only: it never blocks or fails a booking. The payload carries no personal data (no name, email or phone)."""
import logging

import httpx

from ..config import settings

log = logging.getLogger("educlear.zapier")


def notify_booked(booking_id: int, program: str, title: str, slot_iso: str, amount_inr: int) -> str:
    if not settings.zapier_webhook_url:
        return "not-configured"
    try:
        r = httpx.post(settings.zapier_webhook_url, json={"event": "session_paid", "booking_id": booking_id, "program": program,
                                                           "title": title, "slot_start_ist": slot_iso, "amount_inr": amount_inr}, timeout=5)
        return "sent" if r.status_code < 300 else f"failed-{r.status_code}"
    except Exception as e:  # noqa: BLE001
        log.warning("zapier hook failed: %s", type(e).__name__)
        return "failed"
