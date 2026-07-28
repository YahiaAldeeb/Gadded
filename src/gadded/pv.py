"""Deterministic hourly PV generation using pvlib (physics, not machine learning).

Given a weather series and a system capacity, produce an hourly AC power series and
reconciled annual / monthly energy. Defaults (tilt, azimuth, loss) come from the active
assumption set — nothing is hardcoded.

Method: transpose GHI/DNI/DHI to plane-of-array (Hay-Davies), estimate cell temperature
(Faiman), run the PVWatts DC model, then apply the system-loss derate (which folds in
inverter, wiring, soiling, and mismatch losses).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
import pvlib

from gadded.contracts import AssumptionSet, PvGenerationResult
from gadded.weather import WeatherDataset

PV_MODEL_VERSION = "pvlib-pvwatts-0.1.0"
_GAMMA_PDC = -0.0037  # 1/degC, glass-glass crystalline-Si temperature coefficient


@dataclass
class PvGeneration:
    """Hourly PV output plus the typed result summary."""

    series: pd.DataFrame  # column: pv_kw, indexed by timestamp (Africa/Cairo)
    result: PvGenerationResult
    monthly_kwh: pd.Series = field(default_factory=pd.Series)


def generate_pv(
    weather: WeatherDataset,
    capacity_kw: float,
    assumptions: AssumptionSet,
) -> PvGeneration:
    """Model hourly AC generation for one system size at the weather site."""
    if capacity_kw <= 0:
        raise ValueError("capacity_kw must be positive")

    tilt = assumptions.number("pv_tilt_degrees")
    azimuth = assumptions.number("pv_azimuth_degrees")
    loss_pct = assumptions.number("pv_system_loss_pct")

    df = weather.frame
    times = df.index
    loc = pvlib.location.Location(
        weather.latitude, weather.longitude, tz=str(times.tz)
    )
    solpos = loc.get_solarposition(times)
    dni_extra = pvlib.irradiance.get_extra_radiation(times)

    poa = pvlib.irradiance.get_total_irradiance(
        surface_tilt=tilt,
        surface_azimuth=azimuth,
        solar_zenith=solpos["apparent_zenith"],
        solar_azimuth=solpos["azimuth"],
        dni=df["dni_wm2"],
        ghi=df["ghi_wm2"],
        dhi=df["dhi_wm2"],
        dni_extra=dni_extra,
        model="haydavies",
    )
    poa_global = poa["poa_global"].clip(lower=0).fillna(0.0)

    wind = df["wind_ms"] if "wind_ms" in df else pd.Series(1.0, index=times)
    temp_cell = pvlib.temperature.faiman(poa_global, df["temp_air_c"], wind)

    pdc0_w = capacity_kw * 1000.0
    dc_w = pvlib.pvsystem.pvwatts_dc(
        effective_irradiance=poa_global,
        temp_cell=temp_cell,
        pdc0=pdc0_w,
        gamma_pdc=_GAMMA_PDC,
    ).clip(lower=0)

    ac_w = dc_w * (1.0 - loss_pct / 100.0)
    pv_kw = (ac_w / 1000.0).clip(lower=0).fillna(0.0)
    pv_kw.name = "pv_kw"

    series = pv_kw.to_frame()
    # Hourly series -> energy per hour is numerically equal to average kW over the hour.
    annual_kwh = float(pv_kw.sum())
    monthly_kwh = pv_kw.groupby(pv_kw.index.month).sum()
    monthly_kwh.index.name = "month"

    warnings: list[str] = []
    specific_yield = annual_kwh / capacity_kw if capacity_kw else 0.0
    if not 1200 <= specific_yield <= 2200:
        warnings.append(
            f"specific yield {specific_yield:.0f} kWh/kWp outside expected Egypt range 1200-2200"
        )

    result = PvGenerationResult(
        capacityKw=capacity_kw,
        annualGenerationKwh=annual_kwh,
        weatherDatasetId=weather.dataset_id,
        modelVersion=PV_MODEL_VERSION,
        tiltDegrees=tilt,
        azimuthDegrees=azimuth,
        systemLossPct=loss_pct,
        seriesArtifactId=f"pv_{capacity_kw:.0f}kw_{weather.dataset_id}",
        warnings=warnings,
    )
    return PvGeneration(series=series, result=result, monthly_kwh=monthly_kwh)
