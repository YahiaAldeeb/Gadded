"""Feasibility: deterministic waterfall precedence, one branch at a time."""

from pathlib import Path

from gadded.contracts import GisFinding, RegulatoryFinding
from gadded.feasibility import resolve_feasibility
from gadded.gis import load_zones, screen_site
from gadded.regulatory import build_context, evaluate_rules, load_excerpts, load_rules

ROOT = Path(__file__).resolve().parents[1]


def _reg(conclusion, severity, code="R"):
    return RegulatoryFinding(
        code=code,
        conclusion=conclusion,
        severity=severity,
        title="t",
        explanation="e",
        ruleIds=[code],
        confidence="high",
        verificationRequired=True,
    )


def _gis(category, severity, code="g"):
    return GisFinding(
        code=code,
        category=category,
        severity=severity,
        title="t",
        layerId="l",
        sourceName="s",
        checkedAt="2026-01-01T00:00:00Z",
        methodology="m",
    )


def test_golden_case_end_to_end_is_feasible_with_conditions() -> None:
    # A real Egyptian industrial project always needs an EEAA environmental-impact
    # assessment (RULE-008); a clean site with confirmed ownership therefore lands on
    # feasible_with_conditions, not likely_feasible - that condition is real, not a bug.
    corpus = load_excerpts(ROOT / "data" / "regulations" / "excerpts.json")
    rules = load_rules(ROOT / "data" / "regulations" / "rules.json")
    zones = load_zones(ROOT / "data" / "zones.geojson")

    gis_findings = screen_site(30.3203, 31.7466, zones)
    ctx = build_context("self_consumption", "owned", {f.code for f in gis_findings}, recommended_capacity_kw=350)
    reg_findings = evaluate_rules(ctx, rules, corpus)

    result = resolve_feasibility(reg_findings, gis_findings, "owned", module_warnings=[])
    assert result.status == "feasible_with_conditions"


def test_insufficient_information_beats_everything() -> None:
    reg = [_reg("insufficient_information", "info", "R1"), _reg("not_applicable", "critical", "R2")]
    result = resolve_feasibility(reg, [], "owned")
    assert result.status == "insufficient_information"


def test_unknown_gis_coverage_triggers_insufficient_information() -> None:
    gis = [_gis("industrial_zone", "unknown", "g1")]
    result = resolve_feasibility([], gis, "owned")
    assert result.status == "insufficient_information"


def test_unknown_ownership_triggers_insufficient_information() -> None:
    result = resolve_feasibility([], [], "unknown")
    assert result.status == "insufficient_information"


def test_not_applicable_gives_potentially_ineligible() -> None:
    reg = [_reg("not_applicable", "critical", "R3")]
    result = resolve_feasibility(reg, [], "owned")
    assert result.status == "potentially_ineligible"


def test_critical_severity_gives_high_risk() -> None:
    reg = [_reg("requires_review", "critical", "R4")]
    result = resolve_feasibility(reg, [], "owned")
    assert result.status == "high_risk"


def test_critical_gis_gives_high_risk() -> None:
    gis = [_gis("protected_area", "critical", "g2")]
    result = resolve_feasibility([], gis, "owned")
    assert result.status == "high_risk"


def test_requires_review_gives_feasible_with_conditions() -> None:
    reg = [_reg("requires_review", "warning", "R5")]
    result = resolve_feasibility(reg, [], "rented_authorized")
    assert result.status == "feasible_with_conditions"


def test_module_warning_gives_feasible_with_conditions() -> None:
    result = resolve_feasibility([], [], "owned", module_warnings=["low confidence load model"])
    assert result.status == "feasible_with_conditions"


def test_clean_inputs_give_likely_feasible() -> None:
    reg = [_reg("applicable", "info", "R6")]
    result = resolve_feasibility(reg, [], "owned")
    assert result.status == "likely_feasible"
    assert result.reasons
