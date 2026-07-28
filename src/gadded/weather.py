"""Hourly weather / irradiance adapter.

Primary source: NASA POWER Hourly API (free, no key). The exact response used by the
demo is cached to CSV so the pipeline is reproducible and makes no live call at run time.

Canonical output: a timezone-aware hourly DataFrame in Africa/Cairo local time with
explicit unit-bearing columns:

    ghi_wm2   global horizontal irradiance   (W/m^2)
    dni_wm2   direct normal irradiance       (W/m^2)
    dhi_wm2   diffuse horizontal irradiance  (W/m^2)
    temp_air_c  ambient air temperature      (deg C)
    wind_ms   wind speed at 10 m             (m/s)

The index is named ``timestamp`` and is localized to Africa/Cairo.
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import requests

CAIRO_TZ = "Africa/Cairo"
POWER_URL = "https://power.larc.nasa.gov/api/temporal/hourly/point"

# NASA POWER parameter -> canonical column (units already SI in POWER)
_PARAM_MAP = {
    "ALLSKY_SFC_SW_DWN": "ghi_wm2",   # W/m^2
    "ALLSKY_SFC_SW_DNI": "dni_wm2",   # W/m^2
    "ALLSKY_SFC_SW_DIFF": "dhi_wm2",  # W/m^2
    "T2M": "temp_air_c",              # deg C
    "WS10M": "wind_ms",               # m/s
}
_FILL = -999.0  # NASA POWER missing-value sentinel


@dataclass
class WeatherDataset:
    """Canonical hourly weather series plus provenance."""

    frame: pd.DataFrame
    dataset_id: str
    source_name: str
    latitude: float
    longitude: float
    retrieved_at: str
    source_timezone: str
    warnings: list[str] = field(default_factory=list)


def _to_canonical(raw: dict, latitude: float, longitude: float, retrieved_at: str) -> WeatherDataset:
    """Convert a NASA POWER JSON payload to the canonical dataset."""
    params = raw["properties"]["parameter"]
    present = {k: v for k, v in _PARAM_MAP.items() if k in params}
    if "ALLSKY_SFC_SW_DWN" not in present or "T2M" not in present:
        raise ValueError("NASA POWER response missing required GHI or temperature")

    cols = {}
    for power_key, canon in present.items():
        s = pd.Series(params[power_key], dtype="float64")
        cols[canon] = s
    df = pd.DataFrame(cols)

    # POWER hourly keys look like 'YYYYMMDDHH' in UTC.
    idx_utc = pd.to_datetime(df.index, format="%Y%m%d%H", utc=True)
    df.index = idx_utc
    df.index.name = "timestamp"

    warnings: list[str] = []
    missing = (df == _FILL).sum().sum()
    if missing:
        warnings.append(f"{int(missing)} missing values interpolated")
    df = df.replace(_FILL, pd.NA).astype("float64")
    df = df.interpolate(limit_direction="both")

    # Derive DHI if not supplied: DHI = GHI - DNI*cos(zenith) is non-trivial without
    # solar position; leave absent and let the PV model reconstruct if needed.
    df = df.tz_convert(CAIRO_TZ)

    dataset_id = f"nasa_power_{latitude:.4f}_{longitude:.4f}_{retrieved_at[:10]}"
    return WeatherDataset(
        frame=df,
        dataset_id=dataset_id,
        source_name="NASA POWER Hourly",
        latitude=latitude,
        longitude=longitude,
        retrieved_at=retrieved_at,
        source_timezone="UTC",
        warnings=warnings,
    )


def fetch_nasa_power(
    latitude: float,
    longitude: float,
    start: str,
    end: str,
    timeout: float = 60.0,
) -> WeatherDataset:
    """Fetch an hourly series from NASA POWER. `start`/`end` are YYYYMMDD strings.

    Makes a live network call. Use `cache_weather` to persist the result and
    `load_cached_weather` to read it back offline.
    """
    resp = requests.get(
        POWER_URL,
        params={
            "parameters": ",".join(_PARAM_MAP.keys()),
            "community": "RE",
            "longitude": longitude,
            "latitude": latitude,
            "start": start,
            "end": end,
            "format": "JSON",
            "time-standard": "UTC",
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    retrieved_at = pd.Timestamp.now(tz="UTC").isoformat()
    return _to_canonical(resp.json(), latitude, longitude, retrieved_at)


def cache_weather(ds: WeatherDataset, csv_path: str | Path) -> None:
    """Persist a WeatherDataset to CSV + sidecar JSON metadata."""
    csv_path = Path(csv_path)
    ds.frame.to_csv(csv_path)
    meta = {
        "dataset_id": ds.dataset_id,
        "source_name": ds.source_name,
        "latitude": ds.latitude,
        "longitude": ds.longitude,
        "retrieved_at": ds.retrieved_at,
        "source_timezone": ds.source_timezone,
        "display_timezone": CAIRO_TZ,
        "warnings": ds.warnings,
    }
    csv_path.with_suffix(".meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )


def load_cached_weather(csv_path: str | Path) -> WeatherDataset:
    """Read a cached WeatherDataset back from CSV + sidecar metadata. No network."""
    csv_path = Path(csv_path)
    df = pd.read_csv(csv_path, index_col="timestamp")
    # Parse explicitly: pandas 3.0 does not coerce tz-aware ISO strings via parse_dates.
    idx = pd.to_datetime(df.index, utc=True)
    df.index = idx.tz_convert(CAIRO_TZ)
    df.index.name = "timestamp"
    df = df.astype("float64")
    meta_path = csv_path.with_suffix(".meta.json")
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    return WeatherDataset(
        frame=df,
        dataset_id=meta.get("dataset_id", csv_path.stem),
        source_name=meta.get("source_name", "cached"),
        latitude=meta.get("latitude", float("nan")),
        longitude=meta.get("longitude", float("nan")),
        retrieved_at=meta.get("retrieved_at", ""),
        source_timezone=meta.get("source_timezone", "UTC"),
        warnings=meta.get("warnings", []),
    )


def validate_hourly(ds: WeatherDataset, expected_rows: int | None = None) -> list[str]:
    """Return a list of validation problems (empty means valid)."""
    problems: list[str] = []
    df = ds.frame
    if df.index.tz is None:
        problems.append("index is not timezone-aware")
    if not df.index.is_monotonic_increasing:
        problems.append("index is not sorted ascending")
    if df.index.has_duplicates:
        problems.append("index has duplicate timestamps")
    if "ghi_wm2" in df and (df["ghi_wm2"] < 0).any():
        problems.append("negative GHI present")
    if expected_rows is not None and len(df) != expected_rows:
        problems.append(f"expected {expected_rows} rows, got {len(df)}")
    return problems
