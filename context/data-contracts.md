# Data Contracts

## Purpose

This file defines the minimum shared shapes required for an end-to-end assessment. For the notebook-first PoC the **canonical implementation is Pydantic** in `src/gadded/contracts.py`; every module produces and consumes these shapes. The TypeScript interfaces below are kept as a readable specification of each shape — translate them to Pydantic models, no TS build is required.

## Assessment Input

```ts
interface AssessmentInput {
  projectId: string;
  projectName: string;
  projectType: "industrial_rooftop";
  connectionModel: "self_consumption" | "net_metering";
  location: {
    latitude: number;
    longitude: number;
    address?: string;
    governorate?: string;
    industrialZone?: string;
  };
  factory: {
    sector: "food_processing" | "textiles";
    monthlyConsumptionKwh: number[];
    workingDaysPerWeek: number;
    shiftPattern: "day_shift" | "two_shifts" | "continuous";
    shiftStartHour?: number;
    shiftEndHour?: number;
    intervalDataArtifactId?: string;
  };
  site: {
    availableRoofAreaM2: number;
    ownershipStatus: "owned" | "rented_authorized" | "rented_unknown" | "unknown";
    roofType?: string;
    targetCapacityKw?: number;
    connectionVoltage?: string;
  };
  finance: {
    budgetCeilingEgp?: number;
    preference: "cash" | "finance" | "compare";
    targetPaybackYears?: number;
  };
  timeline: {
    targetCommissioningDate?: string;
  };
}
```

## Input Validation Rules

- Latitude must be between -90 and 90.
- Longitude must be between -180 and 180.
- Monthly consumption must contain either one representative value or twelve positive values.
- Available roof area must be positive.
- Shift hours are required for custom shift patterns.
- Target capacity cannot exceed the roof-derived physical maximum without a warning.
- Connection model must be supported in the selected geography.
- Missing ownership authorization blocks a "likely feasible" result.

## Hourly Energy Series

The canonical analytical time series contains 8,760 rows for a standard year or 8,784 for a leap year.

```ts
interface HourlyEnergyPoint {
  timestamp: string;
  loadKw: number;
  pvKw: number;
  selfConsumedKwh: number;
  importedKwh: number;
  exportedKwh: number;
  retailValueEgp: number;
  exportValueEgp: number;
}
```

Required invariants:

- Values cannot be negative.
- `selfConsumedKwh = min(load energy, PV energy)` for the same interval.
- `importedKwh = max(load energy - PV energy, 0)`.
- `exportedKwh = max(PV energy - load energy, 0)`.
- Predicted load totals must reconcile to the submitted monthly totals within the documented tolerance.
- Timestamps must carry an explicit timezone.

## Load Prediction Result

```ts
interface LoadPredictionResult {
  seriesArtifactId: string;
  annualConsumptionKwh: number;
  archetypeId: string;
  modelVersion: string;
  confidence: "high" | "medium" | "low";
  reconciliationErrorPct: number;
  warnings: string[];
}
```

## PV Generation Result

```ts
interface PvGenerationResult {
  capacityKw: number;
  annualGenerationKwh: number;
  weatherDatasetId: string;
  modelVersion: string;
  tiltDegrees: number;
  azimuthDegrees: number;
  systemLossPct: number;
  seriesArtifactId: string;
  warnings: string[];
}
```

## GIS Finding

```ts
interface GisFinding {
  code: string;
  category:
    | "protected_area"
    | "industrial_zone"
    | "land_use"
    | "grid_distance"
    | "substation_distance"
    | "road_distance"
    | "coverage";
  severity: "info" | "warning" | "critical" | "unknown";
  title: string;
  value?: number | string | boolean;
  unit?: string;
  layerId: string;
  sourceName: string;
  sourceDate?: string;
  checkedAt: string;
  methodology: string;
  limitations: string[];
}
```

## Regulatory Citation

```ts
interface RegulatoryCitation {
  documentId: string;
  authority: string;
  documentTitle: string;
  publicationDate?: string;
  effectiveDate?: string;
  section?: string;
  page?: number;
  sourceUrl?: string;
  excerpt: string;
}
```

## Regulatory Finding

```ts
interface RegulatoryFinding {
  code: string;
  conclusion:
    | "applicable"
    | "not_applicable"
    | "requires_review"
    | "insufficient_information";
  severity: "info" | "warning" | "critical";
  title: string;
  explanation: string;
  authority?: string;
  requiredDocuments: string[];
  dependencies: string[];
  estimatedDurationDays?: {
    minimum: number;
    maximum: number;
    basis: "published" | "rule_based" | "unknown";
  };
  citations: RegulatoryCitation[];
  ruleIds: string[];
  confidence: "high" | "medium" | "low";
  verificationRequired: boolean;
}
```

## Technical Recommendation

```ts
interface TechnicalRecommendation {
  recommendedCapacityKw: number;
  physicalMaximumKw: number;
  evaluatedCapacitiesKw: number[];
  annualGenerationKwh: number;
  annualLoadKwh: number;
  selfConsumptionRatio: number;
  selfSufficiencyRatio: number;
  annualImportedKwh: number;
  annualExportedKwh: number;
  roofAreaRequiredM2: number;
  bindingConstraints: string[];
  objectiveName: "npv" | "discounted_savings" | "target_payback";
}
```

## Financial Scenario

```ts
interface FinancialScenario {
  scenario: "cash" | "finance";
  currency: "EGP";
  capexEgp: number;
  annualOpexEgp: number;
  yearOneSavingsEgp: number;
  npvEgp: number;
  irrPct?: number;
  simplePaybackYears?: number;
  discountedPaybackYears?: number;
  monthlyLoanPaymentEgp?: number;
  assumptions: Record<string, number | string>;
}
```

## Risk Summary

```ts
interface RiskSimulationSummary {
  runCount: number;
  seed: number;
  paybackP10Years?: number;
  paybackP50Years?: number;
  paybackP90Years?: number;
  probabilityTargetPaybackPct?: number;
  npvP10Egp: number;
  npvP50Egp: number;
  npvP90Egp: number;
  topSensitivityDrivers: Array<{
    variable: string;
    influence: number;
  }>;
}
```

## Vendor Candidate

```ts
interface VendorCandidate {
  name: string;
  websiteUrl: string;
  contactEmail?: string;
  contactPhone?: string;
  headquartersOrServiceArea?: string;
  supportedProjectEvidence: string;
  fitExplanation: string;
  services: string[];
  evidence: Array<{
    title: string;
    url: string;
    publisher?: string;
    retrievedAt: string;
    supportingText: string;
  }>;
  verificationStatus: "source_supported" | "needs_manual_verification";
}
```

Rules:

- `name`, `websiteUrl`, and at least one evidence item are required.
- Contact details must be omitted when not supported.
- No quality score is allowed in the proof of concept.
- No claim such as "licensed," "certified," or "best" is allowed without direct supporting evidence.

## Final Assessment Result

```ts
interface AssessmentResult {
  runId: string;
  assessmentId: string;
  status:
    | "likely_feasible"
    | "feasible_with_conditions"
    | "high_risk"
    | "potentially_ineligible"
    | "insufficient_information";
  technical: TechnicalRecommendation;
  financial: FinancialScenario[];
  risk: RiskSimulationSummary;
  gisFindings: GisFinding[];
  regulatoryFindings: RegulatoryFinding[];
  vendors: VendorCandidate[];
  warnings: string[];
  generatedArtifactIds: string[];
  versions: {
    code: string;
    assumptionSet: string;
    loadModel: string;
    pvModel: string;
    regulatoryPrompt: string;
    vendorPrompt: string;
  };
}
```

## Error Shape

```ts
interface ApiError {
  code: string;
  message: string;
  fieldErrors?: Record<string, string[]>;
  retryable: boolean;
  runId?: string;
}
```
