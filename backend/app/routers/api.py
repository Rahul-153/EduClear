from typing import Dict, Optional

from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlmodel import Session, select
from pydantic import BaseModel, Field

from ..data import colleges, get_college
from ..engines import alignment as align
from ..engines.assumptions import Assumptions
from ..engines.emi import funding_plan
from ..engines.roi import payback, trajectory
from ..services.recommend import SUPPORTED_STREAMS, card, recommend
from ..engines.fit import fit
from ..engines import refund as refund_engine
from ..db import Deposit, get_session
from ..services import admissions
from ..engines.choice import analyse as analyse_choices

router = APIRouter(prefix="/api")


class RecommendIn(BaseModel):
    stream: str = "Computer Science"
    percentile: Optional[float] = Field(None, ge=0, le=100)
    budget_lakhs: float = Field(18, gt=0)
    region: str = "All"
    home_state: Optional[str] = None
    jee_advanced_rank: Optional[int] = Field(None, ge=1)
    bitsat_score: Optional[int] = Field(None, ge=0, le=390)
    assumptions: Assumptions = Assumptions()


class RoiIn(BaseModel):
    college_id: str
    assumptions: Assumptions = Assumptions()


class FinanceIn(BaseModel):
    college_id: str
    family_savings: int = Field(ge=0)
    annual_contribution: int = Field(0, ge=0)
    assumptions: Assumptions = Assumptions()


class ChoiceIn(BaseModel):
    college_ids: list[str] = Field(min_length=1, max_length=50)
    percentile: Optional[float] = Field(None, ge=0, le=100)
    home_state: Optional[str] = None
    jee_advanced_rank: Optional[int] = Field(None, ge=1)
    assumptions: Assumptions = Assumptions()


class AlignIn(BaseModel):
    student: Dict[str, int]
    parent: Dict[str, int]


def _college(cid: str):
    try:
        return get_college(cid)
    except KeyError as e:
        raise HTTPException(404, str(e))


@router.get("/health")
def health():
    return {"status": "ok", "colleges": len(colleges())}


@router.get("/assumptions")
def assumptions():
    return {"defaults": Assumptions().model_dump(), "supported_streams": SUPPORTED_STREAMS,
            "note": "Model assumptions, not audited data. Editable by the user."}


@router.get("/colleges")
def list_colleges():
    a = Assumptions()
    return [card(c, a, {"tier": None, "reason": "No profile supplied"}) for c in sorted(colleges().values(), key=lambda c: c.nirfRank)]


@router.get("/colleges/{cid}")
def college(cid: str):
    return _college(cid).model_dump()


@router.get("/colleges/{cid}/sources")
def sources(cid: str):
    s = _college(cid).sources
    return {"id": cid, "nirf_year": s.nirfYear, "retrieved_at": s.retrievedAt, "verification": s.verificationStatus,
            "provenance": {k: v.model_dump() for k, v in s.provenance.items()}, "snapshots_sha256": s.snapshots}


@router.post("/recommend")
def recommend_ep(body: RecommendIn):
    user = dict(percentile=body.percentile, home_state=body.home_state,
                jee_advanced_rank=body.jee_advanced_rank, bitsat_score=body.bitsat_score)
    return recommend(body.stream, body.budget_lakhs, body.region, body.assumptions, **user)


@router.post("/roi")
def roi(body: RoiIn):
    c = _college(body.college_id)
    return {"payback": payback(c.fees.totalFourYearCostINR, c.placement.medianBaseSalary, body.assumptions),
            "trajectory": trajectory(c.placement.medianBaseSalary, body.assumptions)}


@router.post("/finance/plan")
def finance(body: FinanceIn):
    c = _college(body.college_id)
    return funding_plan(c.fees.totalFourYearCostINR, body.family_savings, body.annual_contribution, body.assumptions)


@router.post("/alignment")
def alignment_ep(body: AlignIn):
    try:
        return align.score(body.student, body.parent)
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.post("/choice-order")
def choice_order(body: ChoiceIn):
    for cid in body.college_ids:
        _college(cid)
    return analyse_choices(body.college_ids, body.assumptions, percentile=body.percentile,
                           home_state=body.home_state, jee_advanced_rank=body.jee_advanced_rank)


@router.get("/admissions/timeline")
def admissions_timeline():
    return admissions.timeline()


@router.get("/admissions/refund-policy")
def admissions_refund_policy():
    return admissions.refund_policy()


class DepositIn(BaseModel):
    college_id: str
    amount_inr: int = Field(gt=0)
    paid_on: date
    closure_date: date
    note: Optional[str] = Field(None, max_length=200)


def _deposit_view(d: Deposit, today: date):
    pol = admissions.refund_policy()
    now = refund_engine.refund(pol, d.amount_inr, d.closure_date, today)
    ms = refund_engine.milestones(pol, d.closure_date, today)
    nxt = next((m for m in ms if m["days_left"] >= 0), None)
    return {"id": d.id, "college_id": d.college_id, "amount_inr": d.amount_inr, "paid_on": d.paid_on, "closure_date": d.closure_date,
            "note": d.note, "refund_if_withdrawn_today": now, "milestones": ms, "next_cutoff": nxt,
            "alert": bool(nxt and nxt["days_left"] <= 7)}


def _owner(x_client_id: Optional[str]) -> str:
    if not x_client_id or not 8 <= len(x_client_id) <= 64:
        raise HTTPException(400, "X-Client-Id header (8-64 chars) required")
    return x_client_id


@router.post("/deposits")
def add_deposit(body: DepositIn, s: Session = Depends(get_session), x_client_id: Optional[str] = Header(None)):
    _college(body.college_id)
    d = Deposit(owner=_owner(x_client_id), **body.model_dump())
    s.add(d); s.commit(); s.refresh(d)
    return _deposit_view(d, date.today())


@router.get("/deposits")
def list_deposits(s: Session = Depends(get_session), x_client_id: Optional[str] = Header(None)):
    rows = s.exec(select(Deposit).where(Deposit.owner == _owner(x_client_id))).all()
    return [_deposit_view(d, date.today()) for d in rows]


@router.delete("/deposits/{did}")
def delete_deposit(did: int, s: Session = Depends(get_session), x_client_id: Optional[str] = Header(None)):
    d = s.get(Deposit, did)
    if not d or d.owner != _owner(x_client_id):
        raise HTTPException(404, "deposit not found")
    s.delete(d); s.commit()
    return {"deleted": did}


class LetterIn(BaseModel):
    student_name: str = Field(min_length=1, max_length=80)
    guardian_name: Optional[str] = Field(None, max_length=80)
    college_name: str = Field(min_length=1, max_length=120)
    amount_inr: int = Field(gt=0)
    paid_on: date
    closure_date: date
    notice_date: date


@router.post("/refund-letter")
def refund_letter(body: LetterIn):
    pol = admissions.refund_policy()
    r = refund_engine.refund(pol, body.amount_inr, body.closure_date, body.notice_date)
    n = pol["notice"]
    who = f"{body.student_name}" + (f", through {body.guardian_name} (parent/guardian)" if body.guardian_name else "")
    fee_line = (f" I understand that the institution may deduct a processing fee of at most Rs {r['max_processing_fee_inr']:,} "
                f"(5% of fees paid, capped at Rs 5,000) under the UGC notification.") if r["max_processing_fee_inr"] else ""
    text = (f"Date: {body.notice_date:%d %B %Y}\n\nTo,\nThe Registrar / Admissions Office\n{body.college_name}\n\n"
            f"Subject: Withdrawal of admission and request for refund of fees\n\nSir/Madam,\n\n"
            f"I, {who}, hereby withdraw my admission to {body.college_name}. I paid Rs {body.amount_inr:,} on {body.paid_on:%d %B %Y}. "
            f"The institution's last date of admission is {body.closure_date:%d %B %Y}, and this written notice is submitted on "
            f"{body.notice_date:%d %B %Y}.\n\nUnder the UGC fee-refund provisions ({n['number_or_date']}), a withdrawal in this window "
            f"entitles me to a {r['refund_percent']}% refund (\"{r['window']}\"), i.e. Rs {r['gross_refund_inr']:,}.{fee_line} "
            f"The notification requires the refund to be made within {pol['return_within_days']} days of receiving this written application.\n\n"
            f"Kindly refund the amount to the original payment source and confirm receipt of this application, and return my original documents.\n\n"
            f"Yours faithfully,\n{body.student_name}")
    return {"letter": text, "calculation": r, "policy_reference": n["title"], "disclaimer": "Template for convenience, not legal advice. Check your institution's own rules and the latest UGC notice."}
