"""Hour-by-hour matching of factory load against PV generation.

Uses the canonical interval equations from context/data-contracts.md:

    self_consumed = min(load, pv)
    imported      = max(load - pv, 0)
    exported      = max(pv - load, 0)

Values are hourly kW; over a 1-hour interval the kWh energy is numerically equal.
Retail value is the grid energy avoided by self-consumption. Export value depends on the
connection model: net metering credits exported energy; self-consumption assumes a
zero-export site (surplus earns nothing) unless an export price is explicitly modeled.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from gadded.contracts import AssumptionSet, ConnectionModel, HourlyEnergyPoint


@dataclass
class MatchResult:
    """Hourly energy/value frame plus annual and monthly summaries."""

    hourly: pd.DataFrame  # load_kw, pv_kw, self_kwh, import_kwh, export_kwh, retail_egp, export_egp
    annual_load_kwh: float
    annual_pv_kwh: float
    annual_self_kwh: float
    annual_import_kwh: float
    annual_export_kwh: float
    annual_retail_value_egp: float
    annual_export_value_egp: float
    self_consumption_ratio: float  # self / pv generation
    self_sufficiency_ratio: float  # self / load
    monthly: pd.DataFrame


def _validate_alignment(load_kw: pd.Series, pv_kw: pd.Series) -> None:
    """Reject series that cannot be safely matched."""
    li, pi = load_kw.index, pv_kw.index
    if li.tz is None or pi.tz is None:
        raise ValueError("both series must be timezone-aware")
    if str(li.tz) != str(pi.tz):
        raise ValueError(f"timezone mismatch: {li.tz} vs {pi.tz}")
    if len(li) != len(pi):
        raise ValueError(f"length mismatch: {len(li)} vs {len(pi)}")
    if not li.equals(pi):
        raise ValueError("timestamp indexes are not identical")
    if li.has_duplicates:
        raise ValueError("duplicate timestamps present")
    if not li.is_monotonic_increasing:
        raise ValueError("index not sorted ascending")
    freqs = np.unique(np.diff(li.view("int64")))
    if len(freqs) > 1:
        raise ValueError("irregular sampling frequency")


def match_load_and_pv(
    load_kw: pd.Series,
    pv_kw: pd.Series,
    assumptions: AssumptionSet,
    connection_model: ConnectionModel,
) -> MatchResult:
    """Compute self-consumption, import, export, and their tariff value."""
    _validate_alignment(load_kw, pv_kw)
    if (load_kw < 0).any() or (pv_kw < 0).any():
        raise ValueError("negative load or PV present")

    retail = assumptions.number("tariff_retail_egp_per_kwh")
    export_price = assumptions.number("export_price_egp_per_kwh")
    # Self-consumption sites are modeled as zero-export (no feed-in revenue).
    export_rate = export_price if connection_model == "net_metering" else 0.0

    load = load_kw.to_numpy()
    pv = pv_kw.to_numpy()
    self_kwh = np.minimum(load, pv)
    import_kwh = np.maximum(load - pv, 0.0)
    export_kwh = np.maximum(pv - load, 0.0)
    retail_egp = self_kwh * retail
    export_egp = export_kwh * export_rate

    hourly = pd.DataFrame(
        {
            "load_kw": load,
            "pv_kw": pv,
            "self_kwh": self_kwh,
            "import_kwh": import_kwh,
            "export_kwh": export_kwh,
            "retail_egp": retail_egp,
            "export_egp": export_egp,
        },
        index=load_kw.index,
    )

    annual_load = float(load.sum())
    annual_pv = float(pv.sum())
    annual_self = float(self_kwh.sum())

    months = np.asarray(load_kw.index.month)
    monthly = hourly.groupby(months).sum()
    monthly.index.name = "month"

    return MatchResult(
        hourly=hourly,
        annual_load_kwh=annual_load,
        annual_pv_kwh=annual_pv,
        annual_self_kwh=annual_self,
        annual_import_kwh=float(import_kwh.sum()),
        annual_export_kwh=float(export_kwh.sum()),
        annual_retail_value_egp=float(retail_egp.sum()),
        annual_export_value_egp=float(export_egp.sum()),
        self_consumption_ratio=(annual_self / annual_pv) if annual_pv > 0 else 0.0,
        self_sufficiency_ratio=(annual_self / annual_load) if annual_load > 0 else 0.0,
        monthly=monthly,
    )


def to_hourly_point(row: pd.Series, timestamp: pd.Timestamp) -> HourlyEnergyPoint:
    """Convert one matched row to the canonical HourlyEnergyPoint (for validation/tests)."""
    return HourlyEnergyPoint(
        timestamp=timestamp.isoformat(),
        loadKw=float(row["load_kw"]),
        pvKw=float(row["pv_kw"]),
        selfConsumedKwh=float(row["self_kwh"]),
        importedKwh=float(row["import_kwh"]),
        exportedKwh=float(row["export_kwh"]),
        retailValueEgp=float(row["retail_egp"]),
        exportValueEgp=float(row["export_egp"]),
    )
