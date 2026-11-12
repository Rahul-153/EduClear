"""Who is calling, and may they do this? Replaces the anonymous-only `owner` header (D-32) without breaking guests.

Owner strings: a guest is their browser id; a signed-in family is `family:<id>`; a signed-in user with no family is
`user:<id>`. Guest ids cannot contain ':' so the three can never collide.
"""
import re
from datetime import datetime, timedelta
from typing import Callable, Optional

from fastapi import Depends, Header, HTTPException, Request
from sqlmodel import Session

from ..config import settings
from ..db import FamilyMember, LoginSession, User, get_session
from .security import sha256

SESSION_COOKIE = "educlear_session"
IDLE_DAYS, ABSOLUTE_DAYS = 14, 90
_GUEST = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


def current_user(request: Request, s: Session = Depends(get_session)) -> Optional[User]:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    row = s.get(LoginSession, sha256(token))
    now = datetime.utcnow()
    if not row or row.expires_at <= now:
        return None
    if now - row.last_seen_at > timedelta(hours=1):  # sliding idle window, capped by the absolute lifetime
        row.last_seen_at = now
        row.expires_at = min(row.created_at + timedelta(days=ABSOLUTE_DAYS), now + timedelta(days=IDLE_DAYS))
        s.add(row); s.commit()
    return s.get(User, row.user_id)


def require_user(u: Optional[User] = Depends(current_user)) -> User:
    if not u:
        raise HTTPException(401, "Sign in first.")
    return u


def membership(s: Session, u: User) -> Optional[FamilyMember]:
    return s.get(FamilyMember, u.id)


def _guest(x_client_id: Optional[str]) -> str:
    if not x_client_id or not _GUEST.match(x_client_id):
        raise HTTPException(400, "X-Client-Id header (8-64 letters, digits, - or _) required")
    return x_client_id


def actor_read(u: Optional[User] = Depends(current_user), s: Session = Depends(get_session), x_client_id: Optional[str] = Header(None)) -> str:
    if u:
        m = membership(s, u)
        return f"family:{m.family_id}" if m else f"user:{u.id}"
    return _guest(x_client_id)


def _writer(guest_allowed: Callable[[], bool]):
    def dep(u: Optional[User] = Depends(current_user), s: Session = Depends(get_session), x_client_id: Optional[str] = Header(None)) -> str:
        if u:
            m = membership(s, u)
            if u.role != "parent" or not m:
                raise HTTPException(403, "Only a parent can do this. Ask a parent to sign in and do it.")
            return f"family:{m.family_id}"
        if not guest_allowed():
            raise HTTPException(401, "Sign in as a parent to do this.")
        return _guest(x_client_id)
    return dep


pay_actor = _writer(lambda: settings.guest_checkout)  # payments: guests only while GUEST_CHECKOUT is on (demo)
family_actor = _writer(lambda: True)  # deposits: guests keep their own browser-scoped tracker
