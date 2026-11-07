"""SQLModel tables for bookings, escrow ledger and deposits (extended in Phase 5)."""
from datetime import date, datetime
from typing import Optional

from pydantic import NaiveDatetime
from sqlmodel import Field, Session, SQLModel, create_engine

from .config import settings

engine = create_engine(settings.database_url, connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {})


class Booking(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner: str = Field(index=True)  # anonymous per-browser id
    program: str  # program id or "tech-kit"
    amount_inr: int
    usd_cents: int
    slot_start: Optional[NaiveDatetime] = None  # IST wall-clock
    status: str = "pending"  # pending | escrow_funded | paid | payout_failed | released | cancelled
    paypal_order_id: Optional[str] = Field(default=None, index=True)
    capture_id: Optional[str] = None
    payout_batch_id: Optional[str] = None
    note: Optional[str] = None
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)


class LedgerEntry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    booking_id: int = Field(foreign_key="booking.id", index=True)
    kind: str  # funded | released | refunded
    amount_usd_cents: int
    paypal_ref: Optional[str] = Field(default=None, unique=True)  # idempotency key (NFR-07)
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)


class WebhookEvent(SQLModel, table=True):
    id: str = Field(primary_key=True)  # PayPal event id: processed once only (NFR-07)
    event_type: str
    received_at: NaiveDatetime = Field(default_factory=datetime.utcnow)


class Deposit(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner: str = Field(index=True)  # anonymous per-browser id; deposits are never shared across visitors
    college_id: str
    amount_inr: int
    paid_on: date
    closure_date: Optional[date] = None  # the institution's formally notified last date of admission (UGC anchor)
    note: Optional[str] = None


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as s:
        yield s
