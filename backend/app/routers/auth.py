"""Sign-in by emailed code, sessions, and family linking (PLAN_AUTH.md phases 1 and 2). No passwords anywhere."""
import re
from datetime import datetime, timedelta
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ..auth.deps import IDLE_DAYS, SESSION_COOKIE, current_user, membership, require_user
from ..auth.security import mac, new_code, new_invite_code, new_session_token, same, sha256
from ..config import settings
from ..db import AuthCode, Booking, Consent, Deposit, Family, FamilyMember, Invite, LoginSession, User, get_session
from ..integrations.mailer import Mailer, get_mailer

router = APIRouter(prefix="/api")

CONSENT_TEXT_VERSION = "2026-11-v1"
CODE_MINUTES, MAX_ATTEMPTS = 10, 5
PER_EMAIL_PER_HOUR, PER_IP_PER_HOUR = 5, 20
INVITE_DAYS = 7
_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,200}\.[^@\s]{2,}$")
OTHER = {"parent": "student", "student": "parent"}


def _email(v: str) -> str:
    v = v.strip().lower()
    if not _EMAIL.match(v) or len(v) > 254:
        raise HTTPException(422, "Enter a valid email address.")
    return v


def _mask(email: str) -> str:
    name, _, dom = email.partition("@")
    return f"{name[:1]}***@{dom}"


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


class StartIn(BaseModel):
    email: str = Field(max_length=254)
    role: Literal["student", "parent"]
    over18: bool = False  # students only; self-declared, we do not verify age
    display_name: str = Field("", max_length=60)


class VerifyIn(BaseModel):
    email: str = Field(max_length=254)
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class JoinIn(BaseModel):
    code: str = Field(min_length=8, max_length=8)


def me_payload(s: Session, u: Optional[User]) -> dict:
    base = {"guest_checkout": settings.guest_checkout,
            "sign_in_available": not (settings.env == "production" and not get_mailer().real)}
    if not u:
        return {"user": None, **base}
    m = membership(s, u)
    family = None
    if m:
        members = s.exec(select(FamilyMember).where(FamilyMember.family_id == m.family_id)).all()
        users = {x.id: x for x in s.exec(select(User).where(User.id.in_([x.user_id for x in members]))).all()}  # type: ignore[attr-defined]
        family = {"id": m.family_id, "members": [
            {"id": x.user_id, "role": x.role, "name": users[x.user_id].display_name or _mask(users[x.user_id].email),
             "is_minor": users[x.user_id].is_minor, "you": x.user_id == u.id} for x in members]}
    return {"user": {"id": u.id, "role": u.role, "email": u.email, "display_name": u.display_name, "is_minor": u.is_minor},
            "family": family, **base}


@router.post("/auth/start")
def start(body: StartIn, request: Request, s: Session = Depends(get_session), mailer: Mailer = Depends(get_mailer)):
    if settings.env == "production" and not mailer.real:
        raise HTTPException(503, "Email sign-in is not configured on this server.")
    email, ip = _email(body.email), mac("ip", _client_ip(request))
    since = datetime.utcnow() - timedelta(hours=1)
    if len(s.exec(select(AuthCode).where(AuthCode.email == email, AuthCode.created_at > since)).all()) >= PER_EMAIL_PER_HOUR \
            or len(s.exec(select(AuthCode).where(AuthCode.ip_hash == ip, AuthCode.created_at > since)).all()) >= PER_IP_PER_HOUR:
        raise HTTPException(429, "Too many codes requested. Try again in an hour.")
    code = new_code()
    s.add(AuthCode(email=email, code_hash=mac("code", email, code), role=body.role, over18=body.over18 or body.role == "parent",
                   display_name=body.display_name.strip(), ip_hash=ip, expires_at=datetime.utcnow() + timedelta(minutes=CODE_MINUTES)))
    s.commit()
    mailer.send_code(email, code)
    out = {"ok": True, "message": "If the address is valid, a sign-in code has been sent. It expires in 10 minutes."}
    if settings.auth_show_code and settings.env != "production":
        out["demo_code"] = code  # demo only, refused in production
    return out


@router.post("/auth/verify")
def verify(body: VerifyIn, request: Request, response: Response, s: Session = Depends(get_session)):
    email, now = _email(body.email), datetime.utcnow()
    row = s.exec(select(AuthCode).where(AuthCode.email == email, AuthCode.used_at == None, AuthCode.expires_at > now)  # noqa: E711
                 .order_by(AuthCode.id.desc())).first()  # type: ignore[attr-defined]
    bad = HTTPException(400, "That code is wrong or has expired.")
    if not row or row.attempts >= MAX_ATTEMPTS:
        raise bad
    if not same(row.code_hash, mac("code", email, body.code)):
        row.attempts += 1
        s.add(row); s.commit()
        raise bad
    for other in s.exec(select(AuthCode).where(AuthCode.email == email, AuthCode.used_at == None)).all():  # noqa: E711
        other.used_at = now  # one code, one use; burn any others
        s.add(other)
    u = s.exec(select(User).where(User.email == email)).first()
    if not u:  # role comes from the sign-up request and is fixed from here on
        u = User(email=email, role=row.role, display_name=row.display_name, is_minor=(row.role == "student" and not row.over18))
        s.add(u); s.flush()
        if u.role == "parent":
            f = Family(created_by=u.id); s.add(f); s.flush()
            s.add(FamilyMember(user_id=u.id, family_id=f.id, role="parent"))
    u.last_login_at = now
    s.add(u)
    token = new_session_token()  # a fresh session id on every sign-in (no fixation)
    s.add(LoginSession(id_hash=sha256(token), user_id=u.id, expires_at=now + timedelta(days=IDLE_DAYS)))
    s.commit()
    s.refresh(u)
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", secure=settings.env == "production",
                        max_age=IDLE_DAYS * 86400, path="/")
    response.headers["Cache-Control"] = "no-store"
    return me_payload(s, u)


@router.post("/auth/logout")
def logout(request: Request, response: Response, s: Session = Depends(get_session)):
    token = request.cookies.get(SESSION_COOKIE)
    if token and (row := s.get(LoginSession, sha256(token))):
        s.delete(row); s.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/auth/me")
def me(response: Response, u: Optional[User] = Depends(current_user), s: Session = Depends(get_session)):
    response.headers["Cache-Control"] = "no-store"
    return me_payload(s, u)


# ---- family ----
def _need_family(s: Session, u: User) -> FamilyMember:
    m = membership(s, u)
    if not m:
        raise HTTPException(409, "You are not in a family yet.")
    return m


@router.post("/family")
def create_family(u: User = Depends(require_user), s: Session = Depends(get_session)):
    if membership(s, u):
        raise HTTPException(409, "You are already in a family.")
    if u.is_minor:
        raise HTTPException(403, "A student under 18 joins a family by invitation from a parent.")
    f = Family(created_by=u.id); s.add(f); s.flush()
    s.add(FamilyMember(user_id=u.id, family_id=f.id, role=u.role))
    s.commit()
    return me_payload(s, u)


@router.post("/family/invite")
def invite(u: User = Depends(require_user), s: Session = Depends(get_session)):
    m = _need_family(s, u)
    if u.is_minor:
        raise HTTPException(403, "A student under 18 cannot invite; ask a parent.")
    want = OTHER[u.role]
    if s.exec(select(FamilyMember).where(FamilyMember.family_id == m.family_id, FamilyMember.role == want)).first():
        raise HTTPException(409, f"This family already has a {want}.")
    for old in s.exec(select(Invite).where(Invite.family_id == m.family_id, Invite.role_to_join == want, Invite.used_at == None)).all():  # noqa: E711
        s.delete(old)  # a new invite replaces the old one
    code = new_invite_code()
    exp = datetime.utcnow() + timedelta(days=INVITE_DAYS)
    s.add(Invite(family_id=m.family_id, role_to_join=want, created_by=u.id, code_hash=mac("invite", code), expires_at=exp))
    s.commit()
    return {"code": code, "role_to_join": want, "expires_at": exp}  # shown once; only its hash is stored


@router.post("/family/join")
def join(body: JoinIn, u: User = Depends(require_user), s: Session = Depends(get_session)):
    code = body.code.strip().upper()
    inv = s.exec(select(Invite).where(Invite.code_hash == mac("invite", code))).first()
    bad = HTTPException(400, "That invite is invalid or has expired.")
    if not inv or inv.used_at or inv.expires_at <= datetime.utcnow() or inv.role_to_join != u.role:
        raise bad
    if s.exec(select(FamilyMember).where(FamilyMember.family_id == inv.family_id, FamilyMember.role == u.role)).first():
        raise bad
    own = membership(s, u)
    if own:  # a parent gets an empty family at sign-in; it may be dropped, a family with people or records may not
        others = s.exec(select(FamilyMember).where(FamilyMember.family_id == own.family_id, FamilyMember.user_id != u.id)).all()
        owner = f"family:{own.family_id}"
        has_records = s.exec(select(Booking).where(Booking.owner == owner)).first() or s.exec(select(Deposit).where(Deposit.owner == owner)).first()
        if own.family_id == inv.family_id or others or has_records:
            raise HTTPException(409, "Leave your current family first.")
        s.delete(own); s.flush()
        for old in s.exec(select(Invite).where(Invite.family_id == own.family_id)).all():
            s.delete(old)
        s.delete(s.get(Family, own.family_id)); s.flush()
    s.add(FamilyMember(user_id=u.id, family_id=inv.family_id, role=u.role))
    inv.used_by, inv.used_at = u.id, datetime.utcnow()
    s.add(inv)
    if u.is_minor:  # the parent who created the invite gave consent by creating it; recorded when the student accepts
        s.add(Consent(student_user_id=u.id, parent_user_id=inv.created_by, text_version=CONSENT_TEXT_VERSION))
    s.commit()
    return me_payload(s, u)


@router.delete("/family/members/{user_id}")
def remove_member(user_id: int, u: User = Depends(require_user), s: Session = Depends(get_session)):
    m = _need_family(s, u)
    target = s.get(FamilyMember, user_id)
    if not target or target.family_id != m.family_id:
        raise HTTPException(404, "Member not found.")
    if user_id != u.id and not (u.role == "parent" and target.role == "student"):
        raise HTTPException(403, "Only a parent can remove a student, and anyone can leave.")
    if user_id == u.id and u.role == "parent" and s.exec(select(FamilyMember).where(FamilyMember.family_id == m.family_id, FamilyMember.role == "student")).first():
        raise HTTPException(409, "Remove the student first: only a parent can pay for or release this family's bookings.")
    s.delete(target); s.flush()
    if not s.exec(select(FamilyMember).where(FamilyMember.family_id == m.family_id)).first():
        for old in s.exec(select(Invite).where(Invite.family_id == m.family_id)).all():
            s.delete(old)
        # bookings and deposits stay with the family id: payment records are not deleted by leaving
        s.delete(s.get(Family, m.family_id))
    s.commit()
    return me_payload(s, u)
