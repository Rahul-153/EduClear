from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlmodel import Session

from ..db import get_session
from ..engines.assumptions import Assumptions
from ..integrations.paypal import PayPal, get_paypal
from ..llm.client import LLM, get_llm
from ..services import agent as agent_svc
from ..services import claims
from ..services.ratelimit import limit_ai
from ..services import intake
from ..services import payments as svc
from ..auth.deps import pay_actor
from .payments import guard, owner, view

router = APIRouter(prefix="/api")


class IntakeIn(BaseModel):
    text: str = Field(min_length=1, max_length=600)


class ClaimIn(BaseModel):
    text: str = Field(min_length=1, max_length=1500)
    lang: str = "en"


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    profile: dict = {}
    lang: str = "en"
    assumptions: Assumptions = Assumptions()


class ConfirmIn(BaseModel):
    action_id: str


@router.post("/intake", dependencies=[Depends(limit_ai)])
def intake_ep(body: IntakeIn, llm: Optional[LLM] = Depends(get_llm)):
    return intake.parse(body.text, llm)


@router.post("/claims/check", dependencies=[Depends(limit_ai)])
def claims_check(body: ClaimIn, llm: Optional[LLM] = Depends(get_llm)):
    return claims.check(body.text, agent_svc._find_colleges(body.text) or agent_svc._ambiguous(body.text), llm, body.lang)


@router.post("/agent/chat", dependencies=[Depends(limit_ai)])
def chat(body: ChatIn, o: str = Depends(owner), llm: Optional[LLM] = Depends(get_llm)):
    return agent_svc.handle(body.message, body.profile, body.lang, body.assumptions, o, llm)


@router.post("/agent/confirm")
def confirm(body: ConfirmIn, request: Request, o: str = Depends(pay_actor), s: Session = Depends(get_session), pp: PayPal = Depends(get_paypal)):
    p = agent_svc.take_pending(body.action_id, o)
    if not p:
        raise HTTPException(404, "This action expired or was already used. Ask again.")
    b = guard(svc.create_booking, s, pp, o, p["program_id"], p["slot"], mcp_return_url=str(request.base_url))
    via = "paypal-mcp" if (b.note or "").startswith("order created through the PayPal MCP") else "agent"
    return {"booking": view(b, s), "via": via, "note": "Order created in the PayPal sandbox after your confirmation. Approve it in the checkout panel."}
