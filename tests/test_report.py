"""Report: end-to-end assembly from real modules + HTML rendering checks."""

from pathlib import Path

import pytest

from gadded.contracts import ResultVersions, load_assessment_input, load_assumptions
from gadded.feasibility import resolve_feasibility
from gadded.finance import build_scenarios
from gadded.gis import load_zones, screen_site
from gadded.load import estimate_load_baseline
from gadded.optimization import optimize_capacity
from gadded.regulatory import build_context, evaluate_rules, load_excerpts, load_rules
from gadded.report import DISCLAIMER, assemble_result, render_html
from gadded.risk import RiskInputs, run_monte_carlo
from gadded.weather import load_cached_weather

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "weather_10ramadan_cached.csv"

pytestmark = pytest.mark.skipif(
    not CACHE.exists(), reason="cached weather CSV not present"
)


def _build_golden_result():
    ai = load_assessment_input(ROOT / "data" / "golden_case.json")
    a = load_assumptions(ROOT / "data" / "assumptions.json")
    w = load_cached_weather(CACHE)
    tol = a.number("reconciliation_tolerance_pct")
    load_profile = estimate_load_baseline(ai, w.frame.index, tol)
    opt = optimize_capacity(ai, w, load_profile.series["load_kw"], a)
    cap = opt.recommendation.recommendedCapacityKw
    row = opt.table.loc[cap]

    scenarios = build_scenarios(cap, row["year1_savings_egp"], a, ai.finance.preference)

    risk_inputs = RiskInputs(
        capacity_kw=cap,
        year1_pv_savings_egp=row["year1_savings_egp"],
        capex_egp=row["capex_egp"],
        opex_egp=cap * a.number("opex_per_kw_year_egp"),
    )
    risk = run_monte_carlo(
        risk_inputs, a, target_payback_years=ai.finance.targetPaybackYears,
        seed=int(a.number("monte_carlo_seed")), runs=500,
    )

    zones = load_zones(ROOT / "data" / "zones.geojson")
    gis_findings = screen_site(ai.location.latitude, ai.location.longitude, zones)

    corpus = load_excerpts(ROOT / "data" / "regulations" / "excerpts.json")
    rules = load_rules(ROOT / "data" / "regulations" / "rules.json")
    ctx = build_context(ai.connectionModel, ai.site.ownershipStatus, {f.code for f in gis_findings}, cap)
    reg_findings = evaluate_rules(ctx, rules, corpus)

    # Feed only run-specific anomalies into the status decision, not the standing
    # "synthetic baseline" disclosure that every baseline run carries (that stays
    # visible in result.warnings for transparency; see feasibility.py docstring).
    material_warnings = [
        w for w in load_profile.result.warnings
        if "exceeds tolerance" in w or "empty archetype shape" in w
    ]
    feas = resolve_feasibility(reg_findings, gis_findings, ai.site.ownershipStatus, material_warnings)

    versions = ResultVersions(
        code="gadded-poc-0.1.0",
        assumptionSet=a.assumptionSet.id,
        loadModel=load_profile.result.modelVersion,
        pvModel="pvlib-pvwatts-0.1.0",
        regulatoryPrompt="reg-explain-0.1.0",
        vendorPrompt="vendor-discovery-0.1.0",
    )

    result = assemble_result(
        run_id="run-test-001",
        assessment_id=ai.projectId,
        status=feas.status,
        technical=opt.recommendation,
        financial=scenarios,
        risk=risk,
        gis_findings=gis_findings,
        regulatory_findings=reg_findings,
        vendors=[],
        warnings=load_profile.result.warnings,
        versions=versions,
    )
    return ai, result


def test_assemble_result_validates() -> None:
    ai, result = _build_golden_result()
    assert result.status == "likely_feasible"
    assert result.technical.recommendedCapacityKw > 0
    assert len(result.financial) == 2  # golden case preference is "compare"


def test_render_html_contains_key_content() -> None:
    ai, result = _build_golden_result()
    html = render_html(result, ai.projectName, "2026-07-28T12:00:00Z")
    assert ai.projectName in html
    assert "Likely feasible" in html
    assert DISCLAIMER in html
    assert result.versions.assumptionSet in html
    assert "No vendor candidates" in html  # empty vendor list handled gracefully


def test_render_html_is_deterministic() -> None:
    ai, result = _build_golden_result()
    html1 = render_html(result, ai.projectName, "2026-07-28T12:00:00Z")
    html2 = render_html(result, ai.projectName, "2026-07-28T12:00:00Z")
    assert html1 == html2


def test_render_html_includes_citation_text() -> None:
    ai, result = _build_golden_result()
    html = render_html(result, ai.projectName, "2026-07-28T12:00:00Z")
    assert "DNERA" in html  # citation authority name surfaced
