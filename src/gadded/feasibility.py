"""Deterministic overall feasibility status resolver.

The LLM never decides this — it is a fixed, ordered waterfall over the already-computed
regulatory findings, GIS findings, and module warnings. Financial performance (NPV,
payback, risk) is reported separately and does not change this status: a legally and
technically buildable project can still be a poor investment, and that's a financial
judgment for the user, not a "feasibility" judgment about whether it can be built.

Precedence (first match wins; every match records which finding(s) drove it):

1. insufficient_information - a regulatory finding is itself insufficient_information,
   OR a core siting layer (industrial_zone / protected_area) came back unknown coverage,
   OR site ownership is completely unknown (not just "rented, authorization unconfirmed").
2. potentially_ineligible - a regulatory finding concluded not_applicable (the selected
   connection model/capacity is not supported as configured).
3. high_risk - a critical-severity regulatory or GIS finding is present.
4. feasible_with_conditions - a requires_review regulatory finding, a warning-severity
   GIS finding, or any module warning (load/pv/finance/etc.) is present.
5. likely_feasible - none of the above.

``module_warnings`` should carry anomalies specific to this run (e.g. "reconciliation
error exceeded tolerance"), not standing model-limitation disclosures that apply to every
run of the same PoC module (e.g. "synthetic archetype baseline, not measured data"). The
caller filters for that distinction; standing disclosures still belong in the overall
``AssessmentResult.warnings`` for transparency, they just shouldn't downgrade an
otherwise-clean run's status every single time.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from gadded.contracts import GisFinding, RegulatoryFinding

FEASIBILITY_VERSION = "waterfall-0.1.0"

_UNKNOWN_COVERAGE_CATEGORIES = {"industrial_zone", "protected_area"}


@dataclass
class FeasibilityResult:
    status: str
    reasons: list[str] = field(default_factory=list)


def resolve_feasibility(
    regulatory_findings: list[RegulatoryFinding],
    gis_findings: list[GisFinding],
    ownership_status: str,
    module_warnings: list[str] | None = None,
) -> FeasibilityResult:
    """Resolve the overall status from already-computed findings. Deterministic."""
    module_warnings = module_warnings or []
    reasons: list[str] = []

    insufficient = [f for f in regulatory_findings if f.conclusion == "insufficient_information"]
    unknown_coverage = [
        g for g in gis_findings
        if g.severity == "unknown" and g.category in _UNKNOWN_COVERAGE_CATEGORIES
    ]
    if insufficient or unknown_coverage or ownership_status == "unknown":
        for f in insufficient:
            reasons.append(f"regulatory finding {f.code} is insufficient_information")
        for g in unknown_coverage:
            reasons.append(f"GIS layer '{g.category}' has unknown coverage ({g.code})")
        if ownership_status == "unknown":
            reasons.append("site ownership status is unknown")
        return FeasibilityResult(status="insufficient_information", reasons=reasons)

    not_applicable = [f for f in regulatory_findings if f.conclusion == "not_applicable"]
    if not_applicable:
        reasons = [f"regulatory finding {f.code} concluded not_applicable" for f in not_applicable]
        return FeasibilityResult(status="potentially_ineligible", reasons=reasons)

    critical_reg = [f for f in regulatory_findings if f.severity == "critical"]
    critical_gis = [g for g in gis_findings if g.severity == "critical"]
    if critical_reg or critical_gis:
        reasons = [f"regulatory finding {f.code} is critical" for f in critical_reg]
        reasons += [f"GIS finding {g.code} is critical" for g in critical_gis]
        return FeasibilityResult(status="high_risk", reasons=reasons)

    review = [f for f in regulatory_findings if f.conclusion == "requires_review"]
    warning_gis = [g for g in gis_findings if g.severity == "warning"]
    if review or warning_gis or module_warnings:
        reasons = [f"regulatory finding {f.code} requires review" for f in review]
        reasons += [f"GIS finding {g.code} is a warning" for g in warning_gis]
        reasons += [f"module warning: {w}" for w in module_warnings]
        return FeasibilityResult(status="feasible_with_conditions", reasons=reasons)

    return FeasibilityResult(status="likely_feasible", reasons=["no blocking findings or warnings"])
