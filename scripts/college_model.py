"""Pydantic model of the EduClear master institution record (DATA_INGESTION_MANUAL §4).

Additive source fields (decision D-04): nirfYear, retrievedAt, headlineCtcUrl, feeCircularUrl,
cutoffUrl, snapshots, provenance.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class Location(BaseModel):
    model_config = ConfigDict(extra="forbid")
    city: str
    state: str
    tier: str  # "Tier 1" | "Tier 2" | "Tier 3"
    region: str  # North | South | East | West | Central


class Cutoffs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    primaryExam: str
    category: str
    minPercentileOrRank: str
    safeCutoffScore: Optional[float] = None  # D-21: only when an official percentile is published


class Fees(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tuitionAnnual: int
    mandatoryInstituteFeesAnnual: int
    hostelAndMessAnnual: int
    estimatedLivingAnnual: int
    totalFourYearCostINR: int


class Placement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    headlineCTC: float  # LPA
    medianBaseSalary: float  # LPA
    batchSize: int
    eligibleStudents: int
    actuallyPlaced: int
    higherStudiesOrFounders: int
    disclosedPlacementRate: float
    placementAuditNote: str


class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str
    locator: str  # table / page / section where the value was read
    snapshot: Optional[str] = None  # file under data/sources/<id>/


class Sources(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nirfDisclosureUrl: str
    feeCircularDate: str
    verificationStatus: str
    # additive (D-04)
    nirfYear: Optional[int] = None
    retrievedAt: Optional[str] = None  # ISO date
    headlineCtcUrl: Optional[str] = None
    feeCircularUrl: Optional[str] = None
    cutoffUrl: Optional[str] = None
    snapshots: Dict[str, str] = Field(default_factory=dict)  # filename -> sha256
    provenance: Dict[str, Provenance] = Field(default_factory=dict)  # field path -> evidence


class College(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    shortName: str
    stream: str
    type: str
    location: Location
    nirfRank: int
    accreditation: str
    flagshipPrograms: List[str]
    cutoffs: Cutoffs
    fees: Fees
    placement: Placement
    sources: Sources
    commercialRelationship: str
