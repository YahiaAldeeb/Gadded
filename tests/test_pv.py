"""PV model sanity checks on the cached golden site."""

from pathlib import Path

import pytest

from gadded.contracts import load_assumptions
from gadded.pv import generate_pv
from gadded.weather import load_cached_weather

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "weather_10ramadan_cached.csv"

pytestmark = pytest.mark.skipif(
    not CACHE.exists(), reason="cached weather CSV not present"
)


def _run(capacity_kw: float):
    weather = load_cached_weather(CACHE)
    assumptions = load_assumptions(ROOT / "data" / "assumptions.json")
    return generate_pv(weather, capacity_kw, assumptions)


def test_non_negative_and_night_zero() -> None:
    gen = _run(500)
    pv = gen.series["pv_kw"]
    assert (pv >= 0).all()
    assert (gen.series.between_time("00:00", "03:00")["pv_kw"] == 0).all()


def test_specific_yield_in_egypt_range() -> None:
    gen = _run(500)
    specific_yield = gen.result.annualGenerationKwh / 500
    assert 1400 <= specific_yield <= 2100, specific_yield
    assert gen.result.warnings == []


def test_monthly_reconciles_to_annual() -> None:
    gen = _run(500)
    assert abs(gen.monthly_kwh.sum() - gen.result.annualGenerationKwh) < 1.0


def test_generation_scales_with_capacity() -> None:
    small = _run(100).result.annualGenerationKwh
    big = _run(400).result.annualGenerationKwh
    assert big == pytest.approx(4 * small, rel=1e-6)
