"""Guided intake (FR-01): English/Hindi free text -> editable profile fields.
Rules run first and are authoritative. The LLM may only fill fields the rules missed, and every value it returns must be
literally supported by the user's text (number appears in the text; names appear in the text) or it is discarded."""
import re
from typing import Dict, Optional

from ..llm.client import LLM

DEV = str.maketrans("०१२३४५६७८९", "0123456789")
STATES = {
    "andhra pradesh": "Andhra Pradesh", "assam": "Assam", "bihar": "Bihar", "chhattisgarh": "Chhattisgarh", "delhi": "Delhi", "goa": "Goa",
    "gujarat": "Gujarat", "haryana": "Haryana", "himachal pradesh": "Himachal Pradesh", "jharkhand": "Jharkhand", "karnataka": "Karnataka",
    "kerala": "Kerala", "madhya pradesh": "Madhya Pradesh", "maharashtra": "Maharashtra", "odisha": "Odisha", "punjab": "Punjab",
    "rajasthan": "Rajasthan", "tamil nadu": "Tamil Nadu", "telangana": "Telangana", "uttar pradesh": "Uttar Pradesh",
    "uttarakhand": "Uttarakhand", "west bengal": "West Bengal",
    "राजस्थान": "Rajasthan", "दिल्ली": "Delhi", "उत्तर प्रदेश": "Uttar Pradesh", "असम": "Assam", "तेलंगाना": "Telangana", "केरल": "Kerala",
    "महाराष्ट्र": "Maharashtra", "तमिलनाडु": "Tamil Nadu", "कर्नाटक": "Karnataka", "गुजरात": "Gujarat", "बिहार": "Bihar", "पंजाब": "Punjab",
    "हरियाणा": "Haryana", "पश्चिम बंगाल": "West Bengal",
}
REGIONS = [("All", r"all india|pan india|anywhere|पूरे भारत|पूरा भारत|कहीं भी"), ("North", r"\bnorth\b|उत्तर भारत|उत्तर में|उत्तर"),
           ("South", r"\bsouth\b|दक्षिण"), ("East", r"\beast\b|पूर्व"), ("West", r"\bwest\b|पश्चिम")]
STREAMS = [("Computer Science", r"computer|\bcse\b|\bcs\b|कंप्यूटर|कम्प्यूटर|सीएस"),
           ("Electronics & Communication", r"electronics|\bece\b|इलेक्ट्रॉनिक्स"),
           ("Electrical", r"electrical|\bee\b|इलेक्ट्रिकल"), ("Mechanical", r"mechanical|\bmech\b|मैकेनिकल|मेकैनिकल"),
           ("Civil", r"civil|सिविल"), ("MBA", r"\bmba\b|management|एमबीए")]
SCHEMA = {"type": "object", "properties": {"percentile": {"type": ["number", "null"]}, "budget_lakhs": {"type": ["number", "null"]},
          "region": {"type": ["string", "null"]}, "stream": {"type": ["string", "null"]}, "home_state": {"type": ["string", "null"]}},
          "required": ["percentile", "budget_lakhs", "region", "stream", "home_state"]}
SYSTEM = ("Extract fields from an Indian student's message (English or Hindi). Use null for anything not stated. "
          "percentile: JEE Main percentile 0-100. budget_lakhs: total 4-year budget in lakhs of rupees (1 crore = 100). "
          "region: one of All, North, South, East, West. stream: one of Computer Science, Electronics & Communication, Electrical, Mechanical, Civil, MBA. home_state: an Indian state. "
          "Do not guess; copy numbers exactly as written.")


def _num(s: str) -> float:
    return float(s)


def rules(text: str) -> Dict[str, Optional[object]]:
    t = text.translate(DEV)
    low = t.lower()
    out: Dict[str, Optional[object]] = {"percentile": None, "budget_lakhs": None, "region": None, "stream": None, "home_state": None,
                                         "jee_advanced_rank": None, "bitsat_score": None}
    m = re.search(r"(\d{1,3}(?:\.\d+)?)\s*(?:percentile|percentiles|%ile|पर्सेंटाइल|परसेंटाइल|प्रतिशतक)", low) or \
        re.search(r"(?:percentile|पर्सेंटाइल)\D{0,12}(\d{1,3}(?:\.\d+)?)", low)
    if m and 0 < _num(m.group(1)) <= 100:
        out["percentile"] = _num(m.group(1))
    near = re.search(r"(?:budget|बजट|total|कुल)\D{0,25}?(\d+(?:\.\d+)?)\s*(crores?|cr\b|करोड़|करोड|lakhs?|lacs?|लाख)", low)
    anyb = re.search(r"(\d+(?:\.\d+)?)\s*(crores?|cr\b|करोड़|करोड|lakhs?|lacs?|लाख)", low)
    b = near or anyb
    if b:
        v = _num(b.group(1)) * (100 if b.group(2).startswith(("cr", "कर")) else 1)
        if 0 < v <= 500:
            out["budget_lakhs"] = v
    stripped = low
    for name in sorted(STATES, key=len, reverse=True):
        if name in low:
            out["home_state"] = out["home_state"] or STATES[name]
            stripped = stripped.replace(name, " ")
    hits = [region for region, rx in REGIONS if re.search(rx, stripped)]
    if hits:
        out["region"] = hits[0] if len(hits) == 1 else "All"  # several regions named -> do not exclude any
    for stream, rx in STREAMS:
        if re.search(rx, low):
            out["stream"] = stream
            break
    a = re.search(r"(?:advanced|एडवांस्ड|एडवांस)\D{0,25}?(?:rank|air|रैंक)\D{0,6}(\d{1,6})", low) or \
        re.search(r"(?:rank|air|रैंक)\D{0,6}(\d{1,6})\D{0,20}(?:advanced|एडवांस्ड|एडवांस)", low)
    if a:
        out["jee_advanced_rank"] = int(a.group(1))
    s = re.search(r"(?:bitsat|बिटसैट)\D{0,15}(\d{2,3})\b", low)
    if s and int(s.group(1)) <= 390:
        out["bitsat_score"] = int(s.group(1))
    return out


def _named_in(patterns, value, text_low: str) -> bool:
    """The option's own keyword pattern must be found in the user's text (T-15.07)."""
    return any(v == value and re.search(rx, text_low) for v, rx in patterns)


def _supported(field: str, value, text_low: str, text_digits: str) -> bool:
    if value is None:
        return False
    if field in ("percentile", "budget_lakhs"):
        try:
            v = float(value)
        except (TypeError, ValueError):
            return False
        if not 0 < v <= (100 if field == "percentile" else 500):
            return False
        nums = [float(x) for x in re.findall(r"(?<![\d.])\d+(?:\.\d+)?", text_digits)]
        if v in nums:
            return True
        # 'crore' is accepted only when a number written in the text, times 100, is the value
        return field == "budget_lakhs" and bool(re.search(r"crores?|\bcr\b|करोड़|करोड", text_low)) and any(abs(n * 100 - v) < 1e-9 for n in nums)
    if field == "region":
        stripped = text_low
        for name in sorted(STATES, key=len, reverse=True):
            stripped = stripped.replace(name, " ")
        return _named_in(REGIONS, value, stripped)
    if field == "stream":
        return _named_in(STREAMS, value, text_low)
    if field == "home_state":
        return value in set(STATES.values()) and (value.lower() in text_low or any(k in text_low for k, v in STATES.items() if v == value))
    return False


def parse(text: str, llm: Optional[LLM] = None) -> dict:
    text = text.strip()[:600]
    lang = "hi" if re.search(r"[ऀ-ॿ]", text) else "en"
    prof = rules(text)
    src = {k: "rules" for k, v in prof.items() if v is not None}
    used = False
    core = ["percentile", "budget_lakhs", "region"]  # stream defaults to Computer Science, so it never needs a model call
    if llm and text and any(prof[k] is None for k in core):
        got = llm.json(SYSTEM, text, SCHEMA)
        used = got is not None
        low, digits = text.lower(), text.translate(DEV).lower()
        for k in ("percentile", "budget_lakhs", "region", "stream", "home_state"):
            if prof[k] is None and got and _supported(k, got.get(k), low, digits):
                prof[k] = float(got[k]) if k in ("percentile", "budget_lakhs") else got[k]
                src[k] = "llm"
    return {"language": lang, "profile": prof, "sources": src, "missing": [k for k in core if prof[k] is None],
            "llm_used": used, "unsupported_stream": prof["stream"] == "MBA",  # every engineering branch has at least cutoff data (D-59)
            "salary_not_budget": bool(re.search(r"\blpa\b|per annum|\bctc\b", text.lower()))}
