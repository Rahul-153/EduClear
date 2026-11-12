"""Family discussion brief (T-15.11): talking points from the survey gaps and the colleges now on the shortlist. All numbers come from the
college records and the loan engine; the loan figure assumes the whole four-year cost is financed (no savings are known here)."""
from typing import Dict, List

from ..data import get_college
from ..engines.alignment import DIMENSIONS, PROMPTS
from ..engines.assumptions import Assumptions
from ..engines.emi import funding_plan

HI_PROMPTS = {
    "brand_prestige": "ब्रांड से मीडियन वेतन में कितना फ़र्क पड़ता है, उसे लागत के अंतर से तुलना करें।",
    "branch_passion": "देखें कि पसंदीदा ब्रांच उन कॉलेजों में खुली है या नहीं जो दोनों को पसंद हैं, और उसके नतीजे क्या हैं।",
    "location_safety": "वे क्षेत्र और कैंपस स्थितियाँ तय करें जो सुरक्षित लगें; उनके भीतर कॉलेज चुनें।",
    "budget_strictness": "साथ बैठकर चार साल का पक्का बजट तय करें और उसे लोन की EMI योजना से जाँचें।",
}
HI_NAMES = {"brand_prestige": "ब्रांड प्रतिष्ठा", "branch_passion": "ब्रांच में रुचि", "location_safety": "जगह और सुरक्षा", "budget_strictness": "बजट की सख़्ती"}


def build(gaps: Dict[str, int], college_ids: List[str], a: Assumptions) -> List[dict]:
    """`college_ids` are shortlist colleges, most ambitious first. Only gaps of 2 or more produce a point; at most four."""
    cs = [get_college(i) for i in college_ids]
    out: List[dict] = []
    for k, g in sorted(gaps.items(), key=lambda kv: -kv[1]):
        if g < 2:
            continue
        en, hi = f"{DIMENSIONS[k]} (gap {g}): {PROMPTS[k]}", f"{HI_NAMES[k]} (अंतर {g}): {HI_PROMPTS[k]}"
        if k == "budget_strictness" and cs:
            c = cs[0]
            p = funding_plan(c.fees.totalFourYearCostINR, 0, 0, a)
            en += f" Example: {c.shortName} costs ₹{c.fees.totalFourYearCostINR:,}; financed fully by a {a.loan_years}-year loan the EMI would be about ₹{p['loan']['emi_inr']:,}."
            hi += f" उदाहरण: {c.shortName} की लागत ₹{c.fees.totalFourYearCostINR:,} है; पूरा {a.loan_years} साल के लोन से लें तो EMI लगभग ₹{p['loan']['emi_inr']:,} होगी।"
        elif k == "brand_prestige" and len(cs) >= 2:
            x, y = cs[0], cs[-1]
            d = abs(x.fees.totalFourYearCostINR - y.fees.totalFourYearCostINR)
            en += (f" Example: {x.shortName} median {x.placement.medianBaseSalary} LPA vs {y.shortName} median {y.placement.medianBaseSalary} LPA, "
                   f"a cost difference of ₹{d:,}.")
            hi += (f" उदाहरण: {x.shortName} मीडियन {x.placement.medianBaseSalary} LPA बनाम {y.shortName} मीडियन {y.placement.medianBaseSalary} LPA, "
                   f"लागत का अंतर ₹{d:,}।")
        elif k == "location_safety" and cs:
            regions = sorted({c.location.region for c in cs})
            en += f" Your shortlist is in: {', '.join(regions)}."
            hi += f" आपकी शॉर्टलिस्ट इन क्षेत्रों में है: {', '.join(regions)}।"
        out.append({"dimension": k, "en": en, "hi": hi})
    return out[:4]
