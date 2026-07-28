"""Deterministic industrial load-profile baseline.

Builds an 8,760-hour load series from a synthetic archetype (base/standby load plus a
production block during shift hours), then scales each calendar month so the series
reconciles exactly to the submitted monthly kWh. This is the explicit baseline the ML
path (``load_ml``) is compared against — it is not machine learning.

The output series shares the caller-supplied timestamp index (the weather index), so it
aligns hour-for-hour with the PV series for downstream matching.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from gadded.contracts import AssessmentInput, LoadPredictionResult

LOAD_MODEL_VERSION = "archetype-baseline-0.1.0"
_ARCHETYPES_PATH = Path(__file__).resolve().parents[2] / "data" / "load_archetypes" / "archetypes.json"


@dataclass
class LoadProfile:
    """Hourly load series plus the typed result summary."""

    series: pd.DataFrame  # column: load_kw, indexed by timestamp
    result: LoadPredictionResult
    monthly_kwh: pd.Series


def load_archetype_spec() -> dict:
    return json.loads(_ARCHETYPES_PATH.read_text(encoding="utf-8"))


def _shift_bounds(spec: dict, shift_pattern: str, ai: AssessmentInput) -> tuple[int, int]:
    if ai.factory.shiftStartHour is not None and ai.factory.shiftEndHour is not None:
        return ai.factory.shiftStartHour, ai.factory.shiftEndHour
    start, end = spec["defaults"]["shift_hours"][shift_pattern]
    return start, end


def daily_production_intensity(hour: int, start: int, end: int) -> float:
    """Production intensity in [0, 1] for an hour, with a 1-hour ramp at each edge."""
    if start <= hour < end:
        return 1.0
    if hour == start - 1 or hour == end:  # ramp shoulders
        return 0.5
    return 0.0


def default_shift_hours(spec: dict, shift_pattern: str) -> tuple[int, int]:
    """The archetype spec's default (start, end) hour for a shift pattern."""
    return tuple(spec["defaults"]["shift_hours"][shift_pattern])


def week_shape_from_params(
    base_fraction: float,
    weekend_factor: float,
    weekend_days: set[int],
    working_days_per_week: int,
    start_hour: int,
    end_hour: int,
) -> np.ndarray:
    """Build a normalized 168-length (7 day x 24 hour, Monday=0) intensity shape.

    Shared by the deterministic baseline's synthetic-facility generator (``load_ml``)
    and by tiling an ML-predicted cluster centroid back onto a real annual index.
    """
    n_rest = 7 - working_days_per_week
    rest_days = set(list(weekend_days)[: max(0, n_rest)])
    shape = np.empty(168, dtype="float64")
    for dow in range(7):
        is_rest = dow in rest_days
        for hour in range(24):
            pos = dow * 24 + hour
            if is_rest:
                shape[pos] = base_fraction * weekend_factor
            else:
                prod = daily_production_intensity(hour, start_hour, end_hour)
                shape[pos] = base_fraction + (1.0 - base_fraction) * prod
    return shape


def tile_week_shape_to_index(week_shape_168: np.ndarray, index: pd.DatetimeIndex) -> pd.Series:
    """Tile a 168-length weekly shape across a full annual index by (weekday, hour)."""
    positions = index.dayofweek.to_numpy() * 24 + index.hour.to_numpy()
    vals = week_shape_168[positions]
    return pd.Series(vals, index=index, name="load_kw")


def reconcile_to_monthly(
    raw: pd.Series, index: pd.DatetimeIndex, monthly_targets: list[float]
) -> tuple[pd.Series, pd.Series, float, list[str]]:
    """Scale each calendar month of `raw` so it sums exactly to `monthly_targets`.

    Shared by the deterministic baseline and the ML path so both reconcile identically.
    Returns (scaled_series, monthly_kwh_by_month, max_reconciliation_error_pct, warnings).
    """
    raw_vals = raw.to_numpy(copy=True)
    scaled_vals = raw_vals.copy()
    months = np.asarray(index.month)
    warnings: list[str] = []
    errors_pct: list[float] = []

    for m in range(1, 13):
        mask = months == m
        if not mask.any():
            continue
        raw_month_sum = raw_vals[mask].sum()
        target = monthly_targets[m - 1] if len(monthly_targets) == 12 else monthly_targets[0]
        if raw_month_sum <= 0:
            warnings.append(f"month {m}: empty shape, cannot reconcile")
            continue
        factor = target / raw_month_sum
        scaled_vals[mask] = raw_vals[mask] * factor
        achieved = scaled_vals[mask].sum()
        errors_pct.append(abs(achieved - target) / target * 100.0)

    scaled = pd.Series(scaled_vals, index=index, name=raw.name or "load_kw")
    monthly_kwh = scaled.groupby(scaled.index.month).sum()
    monthly_kwh.index.name = "month"
    recon_err = max(errors_pct) if errors_pct else 0.0
    return scaled, monthly_kwh, recon_err, warnings


def estimate_load_baseline(
    ai: AssessmentInput,
    index: pd.DatetimeIndex,
    reconciliation_tolerance_pct: float = 2.0,
) -> LoadProfile:
    """Estimate an hourly load series reconciled to the submitted monthly consumption."""
    spec = load_archetype_spec()
    sector = ai.factory.sector
    shift = ai.factory.shiftPattern
    key = f"{sector}|{shift}"
    arch = spec["archetypes"].get(key) or spec["archetypes"][f"{sector}|continuous"]

    base = float(arch["base_fraction"])
    weekend_factor = float(arch["weekend_base_factor"])
    weekend_days = set(spec["defaults"]["weekend_days"])
    working_days_per_week = ai.factory.workingDaysPerWeek
    # Rest days: take the configured weekend days, as many as the week is short.
    n_rest = 7 - working_days_per_week
    rest_days = set(list(weekend_days)[:max(0, n_rest)])

    start, end = _shift_bounds(spec, shift, ai)

    # Build the unscaled intensity shape in [0, 1].
    hours = index.hour.to_numpy()
    weekdays = index.dayofweek.to_numpy()  # Monday=0 .. Sunday=6
    intensity = np.empty(len(index), dtype="float64")
    for i in range(len(index)):
        is_rest = weekdays[i] in rest_days
        if is_rest:
            intensity[i] = base * weekend_factor
        else:
            prod = daily_production_intensity(int(hours[i]), start, end)
            intensity[i] = base + (1.0 - base) * prod

    raw = pd.Series(intensity, index=index, name="load_kw")

    monthly = ai.factory.monthlyConsumptionKwh
    scaled, monthly_kwh, recon_err, warnings = reconcile_to_monthly(raw, index, monthly)
    annual = float(scaled.sum())

    warnings.append(
        "Synthetic archetype baseline (not measured factory data); intra-day shape is representative."
    )
    if recon_err > reconciliation_tolerance_pct:
        warnings.append(
            f"reconciliation error {recon_err:.2f}% exceeds tolerance {reconciliation_tolerance_pct:.2f}%"
        )

    result = LoadPredictionResult(
        seriesArtifactId=f"load_{key}_{LOAD_MODEL_VERSION}",
        annualConsumptionKwh=annual,
        archetypeId=f"{key}@{spec['manifest']['version']}",
        modelVersion=LOAD_MODEL_VERSION,
        confidence="low",  # baseline is synthetic; ML path may raise this
        reconciliationErrorPct=recon_err,
        warnings=warnings,
    )
    return LoadProfile(series=scaled.to_frame(), result=result, monthly_kwh=monthly_kwh)
