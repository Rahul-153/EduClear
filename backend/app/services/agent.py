"""Autonomous financial & admissions agent (FR-11) under the hybrid rule (D-07):
  * every number comes from deterministic engines (tools),
  * the LLM may only (a) choose one tool from a fixed list and (b) re-phrase the finished answer,
  * (b) is rejected unless it contains exactly the numbers of the template answer,
  * creating a payment order is NEVER automatic: the agent proposes, the user confirms (human in the loop)."""
import re
import time
import uuid
from typing import Dict, List, Optional

from ..config import settings
from ..data import colleges
from ..engines.assumptions import Assumptions
from ..engines.emi import funding_plan
from ..engines.roi import payback
from ..llm.client import LLM
from ..services.programs import PROGRAMS, slots
from ..services.recommend import recommend
from . import intake

TOOLS = ["recommend", "affordability", "emi_compare", "payback", "explain_college", "list_slots", "propose_booking", "help"]
ALIASES = {"calicut": "nit-calicut", "nitc": "nit-calicut", "kozhikode": "nit-calicut", "mnit": "mnit-jaipur", "jaipur": "mnit-jaipur",
           "dtu": "dtu-delhi", "delhi tech": "dtu-delhi", "bits": "bits-pilani", "pilani": "bits-pilani", "bhu": "iit-bhu", "varanasi": "iit-bhu",
           "guwahati": "iit-guwahati", "iitg": "iit-guwahati", "hyderabad": "iit-hyderabad", "iith": "iit-hyderabad",
           "कालीकट": "nit-calicut", "जयपुर": "mnit-jaipur", "पिलानी": "bits-pilani", "गुवाहाटी": "iit-guwahati", "हैदराबाद": "iit-hyderabad"}
PENDING: Dict[str, dict] = {}  # action_id -> {owner, program_id, slot, exp}
NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _find_colleges(text: str) -> List[str]:
    low = text.lower()
    found = [cid for k, cid in ALIASES.items() if k in low]
    for cid, c in colleges().items():
        if c.shortName.lower() in low and cid not in found:
            found.append(cid)
    return list(dict.fromkeys(found))


def _money_lakhs(text: str, words: str) -> Optional[int]:
    t = text.translate(intake.DEV).lower()
    unit = r"(lakhs?|lacs?|लाख|crores?|करोड़)"
    m = re.search(rf"(?:{words})\D{{0,20}}?(\d+(?:\.\d+)?)\s*{unit}", t) or re.search(rf"(\d+(?:\.\d+)?)\s*{unit}\s*(?:of\s*)?(?:{words})", t)
    if not m:
        return None
    n, u = m.group(1), m.group(2)
    return round(float(n) * (10_000_000 if u.startswith(("cr", "कर")) else 100_000))


def route_rules(msg: str, prof: dict) -> str:
    t = msg.lower()
    if re.search(r"\b(book|reserve|schedule|sessions?|counsell?ors?|appointments?)\b|बुक|सत्र|काउंसलर", t):
        return "propose_booking" if re.search(r"\b(book|reserve)\b|बुक", t) else "list_slots"
    if re.search(r"\bemi\b|loan|लोन|ईएमआई", t):
        return "emi_compare"
    if re.search(r"afford|saving|budget|can i|खर्च|बचत|बजट|afford", t):
        return "affordability"
    if re.search(r"payback|roi|worth|return|कमाई|वापस", t):
        return "payback"
    if _find_colleges(msg) and re.search(r"tell|about|placement|salary|fees?|cost|how is|कैसा|बारे", t):
        return "explain_college"
    if re.search(r"recommend|suggest|which college|best|options|सुझाव|कौन", t):
        return "recommend"
    return "recommend" if prof.get("percentile") else "help"


TOOL_SYSTEM = ("You route a student's message to exactly one tool. Tools: recommend (suggest colleges), affordability (can the family "
               "afford a college), emi_compare (loan EMI), payback (is it worth the cost), explain_college (facts about one college), "
               "list_slots (counselling times), propose_booking (the user explicitly asks to book a session), help. "
               'Reply JSON: {"tool": "<name>"}. Never invent other tools.')


def choose_tool(msg: str, prof: dict, llm: Optional[LLM]) -> tuple[str, str]:
    """Rules first (instant). The small model is only consulted when the rules find no intent."""
    tool = route_rules(msg, prof)
    if tool != "help" or not llm:
        return tool, "rules"
    got = llm.json(TOOL_SYSTEM, msg, {"type": "object", "properties": {"tool": {"type": "string", "enum": TOOLS}}, "required": ["tool"]})
    if got and got.get("tool") in TOOLS:
        # an LLM may not escalate to booking unless the words are really there
        if got["tool"] != "propose_booking" or re.search(r"\b(book|reserve)\b|बुक", msg.lower()):
            return got["tool"], "llm"
    return "help", "rules"


def _inr(n: int) -> str:
    return f"₹{n:,}"


def _program_from(msg: str) -> str:
    t = msg.lower()
    for pid, kws in (("josaa-audit", ("josaa", "choice", "preference")), ("year1-roadmap", ("roadmap", "year 1", "masterclass", "cohort")),
                     ("family-consensus", ("family", "parent", "consensus")), ("branch-vs-college", ("branch", "college dilemma"))):
        if any(k in t for k in kws):
            return pid
    return "branch-vs-college"


def run_tool(tool: str, msg: str, profile: dict, a: Assumptions, owner: str, lang: str) -> dict:
    hi = lang == "hi"
    ids = _find_colleges(msg)
    cs = colleges()
    if tool == "recommend":
        r = recommend("Computer Science", profile.get("budget_lakhs") or 18, profile.get("region") or "All", a,
                      percentile=profile.get("percentile"), home_state=profile.get("home_state"),
                      jee_advanced_rank=profile.get("jee_advanced_rank"), bitsat_score=profile.get("bitsat_score"))
        picks = [(k, v) for k, v in r["deck"].items() if v]
        if not picks:
            return {"tool": tool, "data": r, "reply": "आपके इनपुट पर अभी कोई कॉलेज मैच नहीं हुआ; बजट या पर्सेंटाइल बदलकर देखें।" if hi else
                    "No college matches those inputs yet. Try a different budget or percentile, or add a JEE Advanced rank or BITSAT score."}
        lines = [f"{v['short_name']} ({v['fit']['tier']}): {_inr(v['four_year_cost_inr'])}, median {v['median_base_lpa']} LPA, payback {v['payback']['payback_months']} months" for _, v in picks]
        return {"tool": tool, "data": r, "reply": ("सुझाव:\n" if hi else "Suggestions:\n") + "\n".join(lines)}
    if tool in ("affordability", "emi_compare", "payback", "explain_college"):
        if not ids:
            ids = [c for c in (profile.get("last_college"),) if c] or [cid for cid in cs][:0]
        if not ids:
            return {"tool": tool, "data": {}, "reply": "कृपया कॉलेज का नाम बताएं (जैसे NIT Calicut)।" if hi else "Which college do you mean? For example NIT Calicut or MNIT Jaipur."}
    if tool == "affordability":
        c = cs[ids[0]]
        savings = _money_lakhs(msg, "saving|savings|have|बचत|जमा") or 0
        plan = funding_plan(c.fees.totalFourYearCostINR, savings, 0, a)
        if plan["affordable_without_loan"]:
            txt = f"{c.shortName}: कुल लागत {_inr(c.fees.totalFourYearCostINR)}, आपकी बचत {_inr(savings)} से बिना लोन संभव है।" if hi else \
                  f"{c.shortName}: total cost {_inr(c.fees.totalFourYearCostINR)}; your savings of {_inr(savings)} cover it without a loan."
        else:
            txt = (f"{c.shortName}: कुल लागत {_inr(c.fees.totalFourYearCostINR)}, बचत {_inr(savings)}, कमी {_inr(plan['total_deficit_inr'])}; "
                   f"लोन {a.loan_years} साल पर EMI लगभग {_inr(plan['loan']['emi_inr'])}।") if hi else \
                  (f"{c.shortName}: total cost {_inr(c.fees.totalFourYearCostINR)}, savings {_inr(savings)}, shortfall {_inr(plan['total_deficit_inr'])}. "
                   f"A {a.loan_years}-year loan at {a.loan_rate * 100:.1f}% would mean an EMI of about {_inr(plan['loan']['emi_inr'])}.")
        return {"tool": tool, "data": plan, "reply": txt + ("" if savings else (" (बचत नहीं बताई गई, 0 माना गया।)" if hi else " (No savings were mentioned, so I assumed 0.)"))}
    if tool == "emi_compare":
        savings = _money_lakhs(msg, "saving|savings|have|बचत|जमा") or 0
        rows = []
        for cid in ids[:3]:
            c = cs[cid]
            p = funding_plan(c.fees.totalFourYearCostINR, savings, 0, a)
            rows.append((c.shortName, p["total_deficit_inr"], p["loan"]["emi_inr"]))
        txt = "\n".join((f"{n}: लोन {_inr(d)}, EMI {_inr(e)}" if hi else f"{n}: loan {_inr(d)}, EMI {_inr(e)}") for n, d, e in rows)
        return {"tool": tool, "data": {"rows": rows}, "reply": txt}
    if tool == "payback":
        c = cs[ids[0]]
        p = payback(c.fees.totalFourYearCostINR, c.placement.medianBaseSalary, a)
        txt = (f"{c.shortName}: {_inr(c.fees.totalFourYearCostINR)} की लागत चुकाने में लगभग {p['payback_months']} महीने ({int(a.savings_rate * 100)}% बचत पर); मीडियन {c.placement.medianBaseSalary} LPA।" if hi else
               f"{c.shortName}: about {p['payback_months']} months to repay {_inr(c.fees.totalFourYearCostINR)} using {int(a.savings_rate * 100)}% of in-hand pay on the median of {c.placement.medianBaseSalary} LPA (gross-pay view: {p['payback_months_gross_pay']} months).")
        return {"tool": tool, "data": p, "reply": txt}
    if tool == "explain_college":
        c = cs[ids[0]]
        pl = c.placement
        txt = (f"{c.shortName} (NIRF #{c.nirfRank}): लागत {_inr(c.fees.totalFourYearCostINR)}, मीडियन {pl.medianBaseSalary} LPA, {pl.actuallyPlaced:,}/{pl.eligibleStudents:,} प्लेस्ड, ब्रोशर CTC {pl.headlineCTC} LPA।" if hi else
               f"{c.shortName} (NIRF #{c.nirfRank}): 4-year cost {_inr(c.fees.totalFourYearCostINR)}, median {pl.medianBaseSalary} LPA, {pl.actuallyPlaced:,} of {pl.eligibleStudents:,} eligible students placed, headline CTC {pl.headlineCTC} LPA.")
        return {"tool": tool, "data": {"id": ids[0]}, "reply": txt}
    if tool in ("list_slots", "propose_booking"):
        pid = _program_from(msg)
        prog = PROGRAMS[pid]
        first = slots(prog)[0]
        if tool == "list_slots":
            txt = (f"{prog.title}: {_inr(prog.price_inr)}, अगला स्लॉट {first:%d %b %H:%M} IST। बुक करने के लिए 'book' लिखें।" if hi else
                   f"{prog.title}: {_inr(prog.price_inr)}, next slot {first:%a %d %b, %H:%M} IST. Say 'book' to reserve it.")
            return {"tool": tool, "data": {"program": pid}, "reply": txt}
        action_id = uuid.uuid4().hex
        PENDING[action_id] = {"owner": owner, "program_id": pid, "slot": first, "exp": time.time() + 600}
        txt = (f"मैं {prog.title} के लिए {first:%d %b %H:%M} IST का स्लॉट PayPal sandbox में {_inr(prog.price_inr)} पर बुक कर सकता हूँ। पुष्टि करने पर ही ऑर्डर बनेगा।" if hi else
               f"I can reserve {prog.title} on {first:%a %d %b, %H:%M} IST for {_inr(prog.price_inr)} through PayPal sandbox. No order is created until you confirm.")
        return {"tool": tool, "data": {"program": pid}, "reply": txt,
                "pending_action": {"id": action_id, "type": "create_booking", "program_id": pid, "slot_start": first.isoformat(), "amount_inr": prog.price_inr}}
    return {"tool": "help", "data": {}, "reply": ("मैं कॉलेज सुझाव, खर्च/EMI, पेबैक और काउंसलिंग बुकिंग में मदद कर सकता हूँ।" if hi else
            "I can suggest colleges, check affordability and loan EMI, estimate payback, and book a counselling session. Try: 'Can I afford NIT Calicut with 8 lakh savings?'")}


def _numbers(s: str) -> List[str]:
    return sorted(n.replace(",", "") for n in NUM.findall(s.translate(intake.DEV)))


PHRASE_SYSTEM = ("Rewrite the answer in a warm, concise tone in the same language. Keep every number, rupee amount and college name exactly as given. "
                 "Do not add facts, advice or new numbers.")


def phrase(reply: str, llm: Optional[LLM]) -> tuple[str, bool]:
    if not llm:
        return reply, False
    out = llm.text(PHRASE_SYSTEM, reply)
    if out and len(out) < 900 and _numbers(out) == _numbers(reply):  # guard: same numbers, nothing invented
        return out, True
    return reply, False


def handle(msg: str, profile: dict, lang: str, a: Assumptions, owner: str, llm: Optional[LLM]) -> dict:
    msg = msg.strip()[:500]
    lang = "hi" if re.search(r"[ऀ-ॿ]", msg) else lang
    parsed = intake.parse(msg, llm)
    merged = {**profile, **{k: v for k, v in parsed["profile"].items() if v is not None}}
    tool, how = choose_tool(msg, merged, llm)
    res = run_tool(tool, msg, merged, a, owner, lang)
    reply, rephrased = (phrase(res["reply"], llm) if settings.llm_phrasing and not res.get("pending_action") else (res["reply"], False))
    return {**res, "reply": reply, "tool_chosen_by": how, "rephrased_by_llm": rephrased, "llm": llm.name if llm else None,
            "profile": merged, "language": lang,
            "note": "Numbers come from verified data and deterministic calculators; the language model only picks a tool and rephrases."}


def take_pending(action_id: str, owner: str) -> Optional[dict]:
    p = PENDING.get(action_id)
    if not p or p["owner"] != owner:
        return None  # a wrong visitor must not consume someone else's pending action
    PENDING.pop(action_id, None)
    return p if p["exp"] >= time.time() else None
