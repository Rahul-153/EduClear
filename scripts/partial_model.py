"""Partly verified institute record (D-49, PLAN_VIEWS_AND_DATA.md B4).

Holds only what has been verified. Today that is the NIRF 2025 UG 4-year placement row for the batch graduating 2023-24
(D-09, D-20) plus identity. Fees, total cost, headline package and accreditation are listed in `notVerified` and are not
part of the record, so the app can never show a number for them.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict


class PartialPlacement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    batch: str  # graduating year, "2023-24"
    graduated: int  # students graduating in minimum stipulated time
    higherStudies: int
    eligible: int  # graduated minus higher studies (D-09)
    placed: int
    placementRatePct: float  # placed / eligible x 100, two decimals
    medianSalaryInr: int  # per annum, as printed by NIRF


class PartialSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str
    nirfYear: int
    retrievedAt: str  # ISO date of the saved file
    snapshot: str  # file under data/sources/<id>/
    sha256: str
    locator: str


class PartialCollege(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    josaaName: str  # official JoSAA institute name, joins the cutoff table
    name: str
    shortName: str
    type: str
    nirfRank: Optional[int] = None  # None when NIRF lists only a rank band
    dataLevel: Literal["partly_verified"] = "partly_verified"
    placement: PartialPlacement
    verifiedFields: List[str]
    notVerified: List[str]
    source: PartialSource


def gate_errors(r: PartialCollege) -> List[str]:
    """Integrity gates for the placement row; an empty list means it passes."""
    p, errs = r.placement, []
    if not 0 <= p.higherStudies <= p.graduated:
        errs.append("higher studies must be between 0 and graduated")
    if p.eligible != p.graduated - p.higherStudies:
        errs.append("eligible must equal graduated minus higher studies (D-09)")
    if p.eligible <= 0:
        errs.append("eligible must be positive")
    if not 0 <= p.placed <= p.eligible:
        errs.append("placed must be between 0 and eligible")
    if p.eligible > 0 and abs(p.placementRatePct - round(p.placed / p.eligible * 100, 2)) > 0.005:
        errs.append("placement rate does not match placed / eligible")
    if p.medianSalaryInr <= 0:
        errs.append("median salary must be positive")
    if len(r.source.sha256) != 64:
        errs.append("source sha256 must be 64 hex characters")
    return errs
