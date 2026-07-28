"""Load baseline: reconciliation, shape, and alignment checks on the golden case."""

from pathlib import Path

import pytest

from gadded.contracts import load_assessment_input, load_assumptions
from gadded.load import estimate_load_baseline
from gadded.weather import load_cached_weather

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "weather_10ramadan_cached.csv"

pytestmark = pytest.mark.skipif(
    not CACHE.exists(), reason="cached weather CSV not present"
)


def _run():
    ai = load_assessment_input(ROOT / "data" / "golden_case.json")
    a = load_assumptions(ROOT / "data" / "assumptions.json")
    index = load_cached_weather(CACHE).frame.index
    tol = a.number("reconciliation_tolerance_pct")
    return ai, estimate_load_baseline(ai, index, tol)


def test_monthly_reconciles_exactly() -> None:
    ai, lp = _run()
    submitted = ai.factory.monthlyConsumptionKwh
    for m in range(1, 13):
        assert lp.monthly_kwh[m] == pytest.approx(submitted[m - 1], rel=1e-6)
    assert lp.result.reconciliationErrorPct < 0.01


def test_annual_equals_sum_of_submitted() -> None:
    ai, lp = _run()
    assert lp.result.annualConsumptionKwh == pytest.approx(
        sum(ai.factory.monthlyConsumptionKwh), rel=1e-6
    )


def test_non_negative_and_aligned_to_index() -> None:
    ai, lp = _run()
    load = lp.series["load_kw"]
    assert (load >= 0).all()
    assert len(load) in (8760, 8784)
    # food processing keeps a standby base load overnight
    assert (lp.series.between_time("02:00", "03:00")["load_kw"] > 0).all()


def test_daytime_exceeds_night_for_day_shift() -> None:
    _, lp = _run()
    day = lp.series.between_time("10:00", "14:00")["load_kw"].mean()
    night = lp.series.between_time("00:00", "04:00")["load_kw"].mean()
    assert day > night
