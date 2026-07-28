"""Matching: energy balance, ratios, valuation, and alignment guards."""

from pathlib import Path

import pandas as pd
import pytest

from gadded.contracts import load_assessment_input, load_assumptions
from gadded.load import estimate_load_baseline
from gadded.matching import match_load_and_pv, to_hourly_point
from gadded.pv import generate_pv
from gadded.weather import load_cached_weather

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "weather_10ramadan_cached.csv"

pytestmark = pytest.mark.skipif(
    not CACHE.exists(), reason="cached weather CSV not present"
)


def _run(capacity_kw: float = 500, connection="self_consumption"):
    ai = load_assessment_input(ROOT / "data" / "golden_case.json")
    a = load_assumptions(ROOT / "data" / "assumptions.json")
    w = load_cached_weather(CACHE)
    pv = generate_pv(w, capacity_kw, a).series["pv_kw"]
    load = estimate_load_baseline(ai, w.frame.index, a.number("reconciliation_tolerance_pct")).series["load_kw"]
    return a, match_load_and_pv(load, pv, a, connection)


def test_energy_balance() -> None:
    _, r = _run()
    h = r.hourly
    # self + import == load ; self + export == pv, every hour
    assert ((h["self_kwh"] + h["import_kwh"] - h["load_kw"]).abs() < 1e-9).all()
    assert ((h["self_kwh"] + h["export_kwh"] - h["pv_kw"]).abs() < 1e-9).all()


def test_ratios_bounded_and_consistent() -> None:
    _, r = _run()
    assert 0 <= r.self_consumption_ratio <= 1
    assert 0 <= r.self_sufficiency_ratio <= 1
    assert r.annual_self_kwh <= r.annual_pv_kwh + 1e-6
    assert r.annual_self_kwh <= r.annual_load_kwh + 1e-6


def test_self_consumption_has_zero_export_value() -> None:
    _, r = _run(connection="self_consumption")
    assert r.annual_export_value_egp == 0.0
    assert r.annual_export_kwh >= 0.0


def test_net_metering_credits_export() -> None:
    _, r = _run(connection="net_metering")
    if r.annual_export_kwh > 0:
        assert r.annual_export_value_egp > 0


def test_hourly_point_contract() -> None:
    _, r = _run()
    row = r.hourly.iloc[12]
    pt = to_hourly_point(row, r.hourly.index[12])
    assert pt.loadKw >= 0 and pt.pvKw >= 0


def test_misaligned_series_rejected() -> None:
    a, r = _run()
    load = r.hourly["load_kw"]
    shifted = r.hourly["pv_kw"].iloc[:-5]  # different length
    with pytest.raises(ValueError):
        match_load_and_pv(load, shifted, a, "self_consumption")


def test_naive_index_rejected() -> None:
    a, r = _run()
    load = r.hourly["load_kw"].copy()
    pv = r.hourly["pv_kw"].copy()
    load.index = load.index.tz_localize(None)
    pv.index = pv.index.tz_localize(None)
    with pytest.raises(ValueError):
        match_load_and_pv(load, pv, a, "self_consumption")
