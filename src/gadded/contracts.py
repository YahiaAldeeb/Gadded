"""Canonical Pydantic shapes for the Gadded PoC.

This module is the single source of truth for every shape that crosses a module
boundary (see context/data-contracts.md). No other module may define a competing
shape for assessment input, hourly energy series, findings, financial scenarios,
vendor evidence, or the final result.

All monetary values are EGP. All energy is kWh, all power kW. Timestamps carry an
explicit timezone (Africa/Cairo for display).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# --------------------------------------------------------------------------- #
# Assessment input
# --------------------------------------------------------------------------- #

ProjectType = Literal["industrial_rooftop"]
ConnectionModel = Literal["self_consumption", "net_metering"]
Sector = Literal["food_processing", "textiles"]
ShiftPattern = Literal["day_shift", "two_shifts", "continuous"]
OwnershipStatus = Literal["owned", "rented_authorized", "rented_unknown", "unknown"]
FinancePreference = Literal["cash", "finance", "compare"]


class Location(BaseModel):
    latitude: float
    longitude: float
    address: str | None = None
    governorate: str | None = None
    industrialZone: str | None = None

    @field_validator("latitude")
    @classmethod
    def _lat_range(cls, v: float) -> float:
        if not -90 <= v <= 90:
            raise ValueError("latitude must be between -90 and 90")
        return v

    @field_validator("longitude")
    @classmethod
    def _lon_range(cls, v: float) -> float:
        if not -180 <= v <= 180:
            raise ValueError("longitude must be between -180 and 180")
        return v


class Factory(BaseModel):
    sector: Sector
    monthlyConsumptionKwh: list[float]
    workingDaysPerWeek: int = Field(ge=1, le=7)
    shiftPattern: ShiftPattern
    shiftStartHour: int | None = Field(default=None, ge=0, le=23)
    shiftEndHour: int | None = Field(default=None, ge=0, le=24)
    intervalDataArtifactId: str | None = None

    @field_validator("monthlyConsumptionKwh")
    @classmethod
    def _monthly_valid(cls, v: list[float]) -> list[float]:
        if len(v) not in (1, 12):
            raise ValueError("monthlyConsumptionKwh must contain 1 or 12 values")
        if any(x <= 0 for x in v):
            raise ValueError("monthlyConsumptionKwh values must be positive")
        return v


class Site(BaseModel):
    availableRoofAreaM2: float = Field(gt=0)
    ownershipStatus: OwnershipStatus
    roofType: str | None = None
    targetCapacityKw: float | None = Field(default=None, gt=0)
    connectionVoltage: str | None = None


class Finance(BaseModel):
    budgetCeilingEgp: float | None = Field(default=None, gt=0)
    preference: FinancePreference
    targetPaybackYears: float | None = Field(default=None, gt=0)


class Timeline(BaseModel):
    targetCommissioningDate: str | None = None


class AssessmentInput(BaseModel):
    projectId: str
    projectName: str
    projectType: ProjectType
    connectionModel: ConnectionModel
    location: Location
    factory: Factory
    site: Site
    finance: Finance
    timeline: Timeline

    @model_validator(mode="after")
    def _custom_shift_hours(self) -> "AssessmentInput":
        f = self.factory
        if f.shiftPattern != "continuous" and (
            f.shiftStartHour is None or f.shiftEndHour is None
        ):
            # Not fatal for two_shifts/day_shift defaults, but flag intent early.
            pass
        return self


# --------------------------------------------------------------------------- #
# Hourly energy series
# --------------------------------------------------------------------------- #


class HourlyEnergyPoint(BaseModel):
    timestamp: str
    loadKw: float = Field(ge=0)
    pvKw: float = Field(ge=0)
    selfConsumedKwh: float = Field(ge=0)
    importedKwh: float = Field(ge=0)
    exportedKwh: float = Field(ge=0)
    retailValueEgp: float = Field(ge=0)
    exportValueEgp: float = Field(ge=0)


# --------------------------------------------------------------------------- #
# Module results
# --------------------------------------------------------------------------- #

Confidence = Literal["high", "medium", "low"]


class LoadPredictionResult(BaseModel):
    seriesArtifactId: str
    annualConsumptionKwh: float
    archetypeId: str
    modelVersion: str
    confidence: Confidence
    reconciliationErrorPct: float
    warnings: list[str] = Field(default_factory=list)


class PvGenerationResult(BaseModel):
    capacityKw: float
    annualGenerationKwh: float
    weatherDatasetId: str
    modelVersion: str
    tiltDegrees: float
    azimuthDegrees: float
    systemLossPct: float
    seriesArtifactId: str
    warnings: list[str] = Field(default_factory=list)


class GisFinding(BaseModel):
    code: str
    category: Literal[
        "protected_area",
        "industrial_zone",
        "land_use",
        "grid_distance",
        "substation_distance",
        "road_distance",
        "coverage",
    ]
    severity: Literal["info", "warning", "critical", "unknown"]
    title: str
    value: float | str | bool | None = None
    unit: str | None = None
    layerId: str
    sourceName: str
    sourceDate: str | None = None
    checkedAt: str
    methodology: str
    limitations: list[str] = Field(default_factory=list)


class RegulatoryCitation(BaseModel):
    documentId: str
    authority: str
    documentTitle: str
    publicationDate: str | None = None
    effectiveDate: str | None = None
    section: str | None = None
    page: int | None = None
    sourceUrl: str | None = None
    excerpt: str


class EstimatedDuration(BaseModel):
    minimum: int
    maximum: int
    basis: Literal["published", "rule_based", "unknown"]


class RegulatoryFinding(BaseModel):
    code: str
    conclusion: Literal[
        "applicable", "not_applicable", "requires_review", "insufficient_information"
    ]
    severity: Literal["info", "warning", "critical"]
    title: str
    explanation: str
    authority: str | None = None
    requiredDocuments: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    estimatedDurationDays: EstimatedDuration | None = None
    citations: list[RegulatoryCitation] = Field(default_factory=list)
    ruleIds: list[str] = Field(default_factory=list)
    confidence: Confidence
    verificationRequired: bool

    @model_validator(mode="after")
    def _cited_unless_insufficient(self) -> "RegulatoryFinding":
        if self.conclusion != "insufficient_information" and not (
            self.citations or self.ruleIds
        ):
            raise ValueError(
                "regulatory finding needs a citation or rule id "
                "unless conclusion is insufficient_information"
            )
        return self


class TechnicalRecommendation(BaseModel):
    recommendedCapacityKw: float
    physicalMaximumKw: float
    evaluatedCapacitiesKw: list[float]
    annualGenerationKwh: float
    annualLoadKwh: float
    selfConsumptionRatio: float = Field(ge=0, le=1)
    selfSufficiencyRatio: float = Field(ge=0, le=1)
    annualImportedKwh: float
    annualExportedKwh: float
    roofAreaRequiredM2: float
    bindingConstraints: list[str] = Field(default_factory=list)
    objectiveName: Literal["npv", "discounted_savings", "target_payback"]


class FinancialScenario(BaseModel):
    scenario: Literal["cash", "finance"]
    currency: Literal["EGP"] = "EGP"
    capexEgp: float
    annualOpexEgp: float
    yearOneSavingsEgp: float
    npvEgp: float
    irrPct: float | None = None
    simplePaybackYears: float | None = None
    discountedPaybackYears: float | None = None
    monthlyLoanPaymentEgp: float | None = None
    assumptions: dict[str, float | str] = Field(default_factory=dict)


class SensitivityDriver(BaseModel):
    variable: str
    influence: float


class RiskSimulationSummary(BaseModel):
    runCount: int
    seed: int
    paybackP10Years: float | None = None
    paybackP50Years: float | None = None
    paybackP90Years: float | None = None
    probabilityTargetPaybackPct: float | None = None
    npvP10Egp: float
    npvP50Egp: float
    npvP90Egp: float
    topSensitivityDrivers: list[SensitivityDriver] = Field(default_factory=list)


class VendorEvidence(BaseModel):
    title: str
    url: str
    publisher: str | None = None
    retrievedAt: str
    supportingText: str


class VendorCandidate(BaseModel):
    name: str
    websiteUrl: str
    contactEmail: str | None = None
    contactPhone: str | None = None
    headquartersOrServiceArea: str | None = None
    supportedProjectEvidence: str
    fitExplanation: str
    services: list[str] = Field(default_factory=list)
    evidence: list[VendorEvidence]
    verificationStatus: Literal["source_supported", "needs_manual_verification"]

    @field_validator("evidence")
    @classmethod
    def _at_least_one_source(cls, v: list[VendorEvidence]) -> list[VendorEvidence]:
        if not v:
            raise ValueError("vendor candidate requires at least one evidence item")
        return v


class FinancingEvidence(BaseModel):
    title: str
    url: str
    publisher: str | None = None
    retrievedAt: str
    supportingText: str


class FinancingOption(BaseModel):
    bankName: str
    productName: str
    financingRatePct: float
    termYears: int
    downPaymentPct: float
    feesPct: float = 0.0
    maxFinancingEgp: float | None = None
    notes: str | None = None
    evidence: list[FinancingEvidence]
    verificationStatus: Literal["source_supported", "needs_manual_verification"]

    @field_validator("evidence")
    @classmethod
    def _at_least_one_source(cls, v: list[FinancingEvidence]) -> list[FinancingEvidence]:
        if not v:
            raise ValueError("financing option requires at least one evidence item")
        return v


class ResultVersions(BaseModel):
    code: str
    assumptionSet: str
    loadModel: str
    pvModel: str
    regulatoryPrompt: str
    vendorPrompt: str


class AssessmentResult(BaseModel):
    runId: str
    assessmentId: str
    status: Literal[
        "likely_feasible",
        "feasible_with_conditions",
        "high_risk",
        "potentially_ineligible",
        "insufficient_information",
    ]
    technical: TechnicalRecommendation
    financial: list[FinancialScenario]
    risk: RiskSimulationSummary
    gisFindings: list[GisFinding] = Field(default_factory=list)
    regulatoryFindings: list[RegulatoryFinding] = Field(default_factory=list)
    vendors: list[VendorCandidate] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    generatedArtifactIds: list[str] = Field(default_factory=list)
    versions: ResultVersions


class ApiError(BaseModel):
    code: str
    message: str
    fieldErrors: dict[str, list[str]] | None = None
    retryable: bool = False
    runId: str | None = None


# --------------------------------------------------------------------------- #
# Assumptions
# --------------------------------------------------------------------------- #

AssumptionClassification = Literal[
    "OFFICIAL", "MARKET_RANGE", "LITERATURE_PROXY", "SYNTHETIC", "DEMO"
]


class AssumptionValue(BaseModel):
    value: float | str
    unit: str | None = None
    classification: AssumptionClassification
    source: str | None = None
    notes: str | None = None


class AssumptionSetMeta(BaseModel):
    id: str
    name: str
    version: str
    status: Literal["DRAFT", "ACTIVE", "RETIRED"]
    effectiveDate: str


class AssumptionSet(BaseModel):
    assumptionSet: AssumptionSetMeta
    values: dict[str, AssumptionValue]

    def number(self, key: str) -> float:
        """Return a numeric assumption by key, raising if missing or non-numeric."""
        av = self.values[key]
        if not isinstance(av.value, (int, float)):
            raise TypeError(f"assumption '{key}' is not numeric")
        return float(av.value)


# --------------------------------------------------------------------------- #
# Loaders
# --------------------------------------------------------------------------- #


def load_assessment_input(path: str | Path) -> AssessmentInput:
    """Load and validate an assessment input JSON file."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return AssessmentInput.model_validate(data)


def load_assumptions(path: str | Path) -> AssumptionSet:
    """Load and validate a versioned assumption set JSON file."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return AssumptionSet.model_validate(data)
