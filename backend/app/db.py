"""SQLModel tables for bookings, escrow ledger and deposits (extended in Phase 5)."""
from datetime import date, datetime
from typing import Optional

from pydantic import NaiveDatetime
from sqlalchemy import UniqueConstraint
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


# ---- accounts (PLAN_AUTH.md) ----
class RoundState(SQLModel, table=True):
    """One counselling round as the family recorded it (T-16.09). Owner strings as for Deposit: a family shares one record."""
    __table_args__ = (UniqueConstraint("owner", "year", "round"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    owner: str = Field(index=True)
    year: int
    round: int
    request_json: str  # the saved /api/rounds/advise request: list, ranks, seat type, what was allotted
    action_taken: Optional[str] = None  # freeze | float | slide | withdrew
    fee_paid: bool = False  # seat acceptance fee paid; set by a parent (or a guest), never by a signed-in student
    updated_at: NaiveDatetime = Field(default_factory=datetime.utcnow)


class User(SQLModel, table=True):
    __tablename__ = "app_user"  # "user" is a reserved word in Postgres
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    role: str  # student | parent, fixed at first sign-in
    display_name: str = ""
    is_minor: bool = False  # self-declared at sign-up; a minor cannot hold or create a family alone
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    last_login_at: Optional[NaiveDatetime] = None


class Family(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_by: int = Field(foreign_key="app_user.id")
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)


class FamilyMember(SQLModel, table=True):
    user_id: int = Field(primary_key=True, foreign_key="app_user.id")  # one family per user
    family_id: int = Field(foreign_key="family.id", index=True)
    role: str
    joined_at: NaiveDatetime = Field(default_factory=datetime.utcnow)


class Invite(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    family_id: int = Field(foreign_key="family.id", index=True)
    role_to_join: str
    created_by: int = Field(foreign_key="app_user.id")
    code_hash: str = Field(unique=True, index=True)  # the code itself is shown once and never stored
    expires_at: NaiveDatetime
    used_by: Optional[int] = None
    used_at: Optional[NaiveDatetime] = None


class Consent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    student_user_id: int = Field(foreign_key="app_user.id", index=True)
    parent_user_id: int = Field(foreign_key="app_user.id")
    text_version: str
    given_at: NaiveDatetime = Field(default_factory=datetime.utcnow)


class AuthCode(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True)
    code_hash: str  # HMAC of email + code with the server secret
    role: str  # sign-up role, used only if the email has no account yet
    over18: bool = False
    display_name: str = ""
    ip_hash: str = Field(index=True)
    expires_at: NaiveDatetime
    attempts: int = 0
    used_at: Optional[NaiveDatetime] = None
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)


class LoginSession(SQLModel, table=True):
    id_hash: str = Field(primary_key=True)  # SHA-256 of the cookie token; the token itself is never stored
    user_id: int = Field(foreign_key="app_user.id", index=True)
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)
    expires_at: NaiveDatetime
    last_seen_at: NaiveDatetime = Field(default_factory=datetime.utcnow)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as s:
        yield s
