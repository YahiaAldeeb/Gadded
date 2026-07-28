"""Optimization: objective correctness, roof/budget constraints, non-largest proof."""

from pathlib import Path

import pandas as pd
import pytest

from gadded.contracts import load_assessment_input, load_assumptions
from gadded.load import estimate_load_baseline
from gadded.optimization import optimize_capacity, project_npv
from gadded.weather import load_cached_weather

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "weather_10ramadan_cached.csv"

pytestmark = pytest.mark.skipif(
    not CACHE.exists(), reason="cached weather CSV not present"
)


def _setup():
    ai = load_assessment_input(ROOT / "data" / "golden_case.json")
    a = load_assumptions(ROOT / "data" / "assumptions.json")
    w = load_cached_weather(CACHE)
    load = estimate_load_baseline(ai, w.frame.index, a.number("reconciliation_tolerance_pct")).series["load_kw"]
    return ai, a, w, load


def test_objective_monotonic_in_savings() -> None:
    ai, a, _, _ = _setup()
    low = project_npv(100_000, 10_000_000, 200_000, a)
    high = project_npv(200_000, 10_000_000, 200_000, a)
    assert high > low


def test_objective_negative_when_capex_dominates() -> None:
    _, a, _, _ = _setup()
    npv = project_npv(1_000, 50_000_000, 100_000, a)
    assert npv < 0


def test_recommendation_is_argmax_npv() -> None:
    ai, a, w, load = _setup()
    res = optimize_capacity(ai, w, load, a)
    best = res.table.loc[res.recommendation.recommendedCapacityKw, "npv_egp"]
    assert best == pytest.approx(res.table["npv_egp"].max())


def test_candidates_respect_roof() -> None:
    ai, a, w, load = _setup()
    res = optimize_capacity(ai, w, load, a)
    # 3000 m2 / 6 m2 per kW = 500 kW physical max
    assert res.recommendation.physicalMaximumKw == pytest.approx(500, rel=1e-6)
    assert max(res.recommendation.evaluatedCapacitiesKw) <= 500 + 1e-6


def test_budget_constraint_binds() -> None:
    ai, a, w, load = _setup()
    ai.finance.budgetCeilingEgp = 100 * a.number("capex_per_kw_egp")  # caps at 100 kW
    res = optimize_capacity(ai, w, load, a)
    assert max(res.recommendation.evaluatedCapacitiesKw) <= 100 + 1e-6
    assert "budget" in res.recommendation.bindingConstraints


def test_not_largest_when_load_is_small() -> None:
    # Shrink load so a large system spills most of its output; optimum must be interior.
    ai, a, w, load = _setup()
    tiny = load * 0.02  # ~39 MWh/yr factory
    res = optimize_capacity(ai, w, tiny, a)
    caps = res.recommendation.evaluatedCapacitiesKw
    assert res.recommendation.recommendedCapacityKw < max(caps)
