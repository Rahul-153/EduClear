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
from ..engines.choice import analyse as analyse_choices
from ..engines.emi import funding_plan
from ..engines.refund import usable_tiers
from ..engines.roi import payback
from ..llm.client import LLM
from ..services.programs import PROGRAMS, slots
from ..services.recommend import card, recommend
from . import admissions, claims, glossary, intake, rounds

TOOLS = ["recommend", "affordability", "emi_compare", "payback", "explain_college", "list_slots", "propose_booking", "help"]
# Only aliases that point to exactly one college (T-15.04). Bare cities shared by several colleges live in AMBIGUOUS.
ALIASES = {"calicut": "nit-calicut", "nitc": "nit-calicut", "kozhikode": "nit-calicut", "mnit": "mnit-jaipur", "jaipur": "mnit-jaipur",
           "dtu": "dtu-delhi", "delhi tech": "dtu-delhi", "bits": "bits-pilani", "pilani": "bits-pilani", "bhu": "iit-bhu", "varanasi": "iit-bhu",
           "guwahati": "iit-guwahati", "iitg": "iit-guwahati", "iith": "iit-hyderabad",
           "कालीकट": "nit-calicut", "जयपुर": "mnit-jaipur", "पिलानी": "bits-pilani", "गुवाहाटी": "iit-guwahati"}
AMBIGUOUS = {"hyderabad": ["iit-hyderabad", "iiit-hyderabad"], "हैदराबाद": ["iit-hyderabad", "iiit-hyderabad"]}
PENDING: Dict[str, dict] = {}  # action_id -> {owner, program_id, slot, exp}
NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _spans(text: str, needles: Dict[str, str]) -> List[str]:
    """Longest needle first; a matched span is blanked so 'IIIT Hyderabad' cannot also match 'IIT Hyderabad'."""
    low, found = text.lower(), []
    for k in sorted(needles, key=len, reverse=True):
        rx = re.compile(rf"(?<![\w]){re.escape(k)}(?![\w])")
        if rx.search(low):
            found.append(needles[k])
            low = rx.sub(" " * len(k), low)
    return list(dict.fromkeys(found))


def _find_colleges(text: str) -> List[str]:
    needles = dict(ALIASES)
    for cid, c in colleges().items():
        needles.setdefault(c.shortName.lower(), cid)
        needles.setdefault(c.name.lower(), cid)
    found = _spans(text, needles)
    # keep document order of first appearance
    low = text.lower()
    return sorted(found, key=lambda cid: min((low.find(k) for k, v in needles.items() if v == cid and k in low), default=0))


def _ambiguous(text: str) -> List[str]:
    """A bare city shared by several colleges, only when no specific college was named."""
    if _find_colleges(text):
        return []
    low = text.lower()
    return next((v for k, v in AMBIGUOUS.items() if k in low), [])


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
    if re.search(r"\bmean(s|ing)?\b|\bdefine\b|definition|क्या (है|होता है)|मतलब|अर्थ", t) and glossary.best(msg):
        return "explain_term"
    if re.search(r"\b(float|freeze|slide)\b|फ़्लोट|फ्लोट|फ़्रीज़|फ्रीज|स्लाइड", t) or (
            re.search(r"(round|राउंड)\s*\d", t) and re.search(r"\b(got|allotted|allocated)\b|मिल", t)):
        return "round_advice"  # what to do after a JoSAA round (T-16.08)
    if re.search(r"refund|withdraw|cancel (my )?seat|रिफंड|वापसी", t):
        return "refund"
    if re.search(r"choice order|choice list|preference (list|order)|choice filling|वरीयता|चॉइस", t):
        return "check_choice_order"
    if re.search(r"brochure|advert|they claim|claims? (that|to)|100% placement|ब्रोशर|दावा", t):
        return "check_claim"
    if re.search(r"\bemi\b|loan|लोन|ईएमआई", t):
        return "emi_compare"
    if re.search(r"afford|saving|budget|can i|खर्च|बचत|बजट|afford", t):
        return "affordability"
    if re.search(r"payback|roi|worth|return|कमाई|वापस", t):
        return "payback"
    if (_find_colleges(msg) or _ambiguous(msg)) and re.search(r"tell|about|placement|salary|fees?|cost|how is|कैसा|बारे", t):
        return "explain_college"
    if re.search(r"\b(compare|vs|versus|better)\b|तुलना", t) and len(_find_colleges(msg)) >= 2:
        return "compare"
    if re.search(r"deadline|last date|when (is|are|does|do)|\bround\b|अंतिम तिथि|कब", t):
        return "deadlines"
    if re.search(r"recommend|suggest|which college|best|options|सुझाव|कौन", t):
        return "recommend"
    return "help"  # off-topic questions must not get college suggestions (T-15.01)


TOOL_SYSTEM = ("You route a student's message to exactly one tool. Tools: recommend (suggest colleges), affordability (can the family "
               "afford a college), emi_compare (loan EMI), payback (is it worth the cost), explain_college (facts about one college), "
               "list_slots (counselling times), propose_booking (the user explicitly asks to book a session), deadlines (admission dates), refund (fee refund rules), "
               "check_choice_order (is a JoSAA preference list in a good order), compare (two or more colleges side by side), "
               "check_claim (verify a brochure claim), explain_term (meaning of an admissions or placement term), help. "
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


def run_tool(tool: str, msg: str, profile: dict, a: Assumptions, owner: str, lang: str, llm: Optional[LLM] = None) -> dict:
    hi = lang == "hi"
    ids = _find_colleges(msg)
    cs = colleges()
    if tool == "recommend":
        stream = profile.get("stream") or "Computer Science"
        opts = {k: profile[k] for k in ("seat_type", "gender", "category_rank") if profile.get(k)}
        r = recommend(stream, profile.get("budget_lakhs") or 18, profile.get("region") or "All", a, opts,
                      percentile=profile.get("percentile"), home_state=profile.get("home_state"),
                      jee_advanced_rank=profile.get("jee_advanced_rank"), bitsat_score=profile.get("bitsat_score"))
        if not r.get("supported"):
            return {"tool": tool, "data": r, "reply": f"{stream} के लिए अभी डेटा उपलब्ध नहीं है।" if hi else f"{stream} is not available in our data yet."}
        picks = [(k, v) for k, v in r["deck"].items() if v]
        if not picks:
            rows = ((r.get("cutoff_only") or {}).get("items") or [])[:3]
            if rows:
                lines = [f"{i['institute']} ({i['tier']}): closing rank {i['closing_rank']:,}" for i in rows]
                return {"tool": tool, "data": r, "reply": ("सिर्फ क्लोज़िंग रैंक (लागत और प्लेसमेंट सत्यापित नहीं):\n" if hi else
                        "Closing rank only (cost and placement not verified):\n") + "\n".join(lines)}
            return {"tool": tool, "data": r, "reply": "आपके इनपुट पर अभी कोई कॉलेज मैच नहीं हुआ; बजट या पर्सेंटाइल बदलकर देखें।" if hi else
                    "No college matches those inputs yet. Try a different budget or percentile, or add a JEE Advanced rank or BITSAT score."}
        lines = [f"{v['short_name']} ({v['fit']['tier']}): {_inr(v['four_year_cost_inr'])}, median {v['median_base_lpa']} LPA, payback {v['payback']['payback_months']} months" for _, v in picks]
        return {"tool": tool, "data": r, "reply": ("सुझाव:\n" if hi else "Suggestions:\n") + "\n".join(lines)}
    if tool in ("affordability", "emi_compare", "payback", "explain_college"):
        amb = _ambiguous(msg)
        if amb:
            n = [cs[i].shortName for i in amb]
            return {"tool": tool, "data": {}, "reply": f"कौन सा: {' या '.join(n)}?" if hi else f"Which one: {' or '.join(n)}?"}
        if len(ids) > 1 and tool != "emi_compare":
            n = [cs[i].shortName for i in ids[:3]]
            return {"tool": tool, "data": {}, "reply": f"कौन सा: {' या '.join(n)}?" if hi else f"Which one: {' or '.join(n)}?"}
        if not ids:
            ids = [c for c in (profile.get("last_college"),) if c in cs]
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
    if tool == "deadlines":
        tl = admissions.timeline()
        nxt = [e for e in tl["events"] if e["status"] != "past"][:3]
        if not nxt:
            return {"tool": tool, "data": tl, "reply": "प्रकाशित चक्र की सभी तिथियाँ निकल चुकी हैं; अगला चक्र अभी प्रकाशित नहीं हुआ।" if hi else
                    f"All dates of the latest published cycle (JoSAA {tl['cycle']}) have passed; the next cycle is not published yet."}
        def when(e):
            d = e["days_until_start"]
            return (f"{d} दिन बाद" if hi else f"in {d} days") if d > 0 else ("चल रहा है" if hi else "ongoing")
        lines = [f"{e['label']}: {e['start']}{' to ' + e['end'] if e.get('end') else ''} ({when(e)})" for e in nxt]
        return {"tool": tool, "data": {"events": nxt}, "reply": ("अगली तिथियाँ:\n" if hi else f"Next dates (JoSAA {tl['cycle']} schedule):\n") + "\n".join(lines)}
    if tool == "refund":
        pol = admissions.refund_policy()
        t = msg.translate(intake.DEV).lower()
        lk = _money_lakhs(msg, "fee|fees|deposit|paid|refund|amount|जमा|फीस")
        rs = re.search(r"(?:₹|rs\.?\s*)\s*(\d[\d,]*)", t)
        amount = lk or (int(rs.group(1).replace(",", "")) if rs else None)
        lines = [f"{x['refund_percent']}%: {x['window']}" + (f" -> {_inr(round(amount * x['refund_percent'] / 100))}" if amount else "") for x in usable_tiers(pol)]
        head = "UGC फीस-रिफंड नियम (सूचित अंतिम प्रवेश तिथि के सापेक्ष):\n" if hi else "UGC fee-refund tiers (relative to the formally notified last date of admission):\n"
        return {"tool": tool, "data": {"tiers": usable_tiers(pol), "amount": amount}, "reply": head + "\n".join(lines)}
    if tool == "check_choice_order":
        if len(ids) < 2:
            return {"tool": tool, "data": {}, "reply": "क्रम जाँचने के लिए कम से कम दो कॉलेज के नाम लिखें, उसी क्रम में।" if hi else
                    "Name at least two colleges in the order you plan to list them, and I will check the order."}
        res = analyse_choices(ids, a, percentile=profile.get("percentile"), home_state=profile.get("home_state"),
                              jee_advanced_rank=profile.get("jee_advanced_rank"))
        if res["alerts"]:
            body = "\n".join(x["message"] for x in res["alerts"])
        else:
            body = "कोई क्रम-उलटाव नहीं मिला।" if hi else "No order inversions found for the colleges that could be compared."
        return {"tool": tool, "data": res, "reply": body + ("\n" + "\n".join(res["notes"]) if res["notes"] else "")}
    if tool == "compare":
        if len(ids) < 2:
            return {"tool": tool, "data": {}, "reply": "तुलना के लिए दो कॉलेज के नाम लिखें।" if hi else "Name two colleges to compare."}
        cards = [card(cs[i], a, {"tier": None}) for i in ids[:3]]
        lines = [(f"{x['short_name']}: लागत {_inr(x['four_year_cost_inr'])}, मीडियन {x['median_base_lpa']} LPA, {x['placed']:,}/{x['eligible']:,} प्लेस्ड, पेबैक {x['payback']['payback_months']} महीने" if hi else
                  f"{x['short_name']}: cost {_inr(x['four_year_cost_inr'])}, median {x['median_base_lpa']} LPA, {x['placed']:,} of {x['eligible']:,} placed, payback {x['payback']['payback_months']} months") for x in cards]
        return {"tool": tool, "data": {"cards": cards}, "reply": "\n".join(lines)}
    if tool == "explain_term":
        e = glossary.lookup(msg, llm)
        if not e:
            return {"tool": tool, "data": {}, "reply": "यह शब्द मेरे शब्दकोश में नहीं है।" if hi else "I do not have that term in my glossary."}
        src = e["source"]
        tail = (f"\nस्रोत: {src['label']}" if hi else f"\nSource: {src['label']}") + (f" ({src['url']})" if src.get("url") else "")
        return {"tool": tool, "data": {"id": e["id"]}, "reply": f"{e['term']['hi' if hi else 'en']}: {e['definition']['hi' if hi else 'en']}{tail}"}
    if tool == "round_advice":
        return {"tool": tool, **rounds.copilot(msg, profile, a, hi)}
    if tool == "check_claim":
        res = claims.check(msg, ids, None, lang)
        return {"tool": tool, "data": res, "reply": "\n".join(res["lines"])}
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
    res = run_tool(tool, msg, merged, a, owner, lang, llm)
    named = _find_colleges(msg)
    if len(named) == 1 and tool in ("affordability", "emi_compare", "payback", "explain_college"):
        merged["last_college"] = named[0]  # follow-up questions ("can I afford it") refer to this college (T-15.03)
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
