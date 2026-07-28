"""Weather adapter: the cached golden-site series loads offline and validates."""

from pathlib import Path

import pytest

from gadded.weather import load_cached_weather, validate_hourly

CACHE = Path(__file__).resolve().parents[1] / "data" / "weather_10ramadan_cached.csv"

pytestmark = pytest.mark.skipif(
    not CACHE.exists(), reason="cached weather CSV not present"
)


def test_cached_weather_loads_and_validates() -> None:
    ds = load_cached_weather(CACHE)
    assert len(ds.frame) in (8760, 8784)
    assert str(ds.frame.index.tz) == "Africa/Cairo"
    assert {"ghi_wm2", "temp_air_c"}.issubset(ds.frame.columns)
    assert validate_hourly(ds, expected_rows=len(ds.frame)) == []


def test_no_negative_irradiance_and_night_is_zero() -> None:
    ds = load_cached_weather(CACHE)
    ghi = ds.frame["ghi_wm2"]
    assert (ghi >= 0).all()
    # local midnight should be dark
    midnight = ds.frame.between_time("00:00", "00:00")["ghi_wm2"]
    assert (midnight == 0).all()
