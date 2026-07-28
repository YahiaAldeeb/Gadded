"""Monte Carlo risk analysis for the recommended solar investment.

Reuses the deterministic finance functions (``finance.npv``, ``finance.savings_stream``,
``finance.simple_payback``) for every draw — Monte Carlo only supplies the varied inputs,
it never re-implements the cash-flow math. This is uncertainty quantification, not a
black-box risk score: every variable and its distribution is named and versioned.

Sensitivity is computed one-at-a-time: each variable is perturbed by +/-1 standard
deviation while the others are held at their mean, and the resulting swing in NPV ranks
the variable's influence. This is deterministic and independent of the Monte Carlo draws.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from gadded.contracts import AssumptionSet, RiskSimulationSummary, SensitivityDriver
from gadded.finance import npv, savings_stream, simple_payback

RISK_MODEL_VERSION = "monte-carlo-oat-0.1.0"


@dataclass
class RiskInputs:
    """Base-case values the simulation perturbs."""

    capacity_kw: float
    year1_pv_savings_egp: float  # savings attributable to PV output (scales with yield)
    capex_egp: float
    opex_egp: float


def _draw_normal(rng: np.random.Generator, mean: float, rel_std_pct: float, n: int, floor: float = 0.0) -> np.ndarray:
    """Normal draws around `mean`, width `rel_std_pct` percent of `mean`, clipped at `floor`."""
    std = mean * (rel_std_pct / 100.0)
    return np.clip(rng.normal(mean, std, n), floor, None)


def _npv_for_draw(
    year1_savings: float, capex: float, opex: float, esc: float, deg: float, n: int, disc: float
) -> float:
    cfs = savings_stream(year1_savings, opex, n, esc, deg)
    return npv(cfs, capex, disc)


def _payback_for_draw(
    year1_savings: float, capex: float, opex: float, esc: float, deg: float, n: int
) -> float | None:
    cfs = savings_stream(year1_savings, opex, n, esc, deg)
    return simple_payback(cfs, capex)


def run_monte_carlo(
    inputs: RiskInputs,
    assumptions: AssumptionSet,
    target_payback_years: float | None = None,
    seed: int | None = None,
    runs: int | None = None,
) -> RiskSimulationSummary:
    """Simulate NPV and payback distributions under PV yield, capex, opex, and tariff uncertainty."""
    n_years = int(assumptions.number("analysis_period_years"))
    disc = assumptions.number("discount_rate_pct") / 100.0
    deg = assumptions.number("degradation_pct_year") / 100.0
    base_esc = assumptions.number("tariff_escalation_pct") / 100.0

    n_runs = runs if runs is not None else int(assumptions.number("monte_carlo_runs"))
    seed = seed if seed is not None else int(assumptions.number("monte_carlo_seed"))
    rng = np.random.default_rng(seed)

    pv_yield_pct = assumptions.number("irradiance_variability_pct")
    capex_var_pct = assumptions.number("capex_variability_pct")
    opex_var_pct = assumptions.number("opex_variability_pct")
    esc_var_pct = assumptions.number("tariff_escalation_variability_pct")

    if n_runs <= 0:
        raise ValueError("monte_carlo_runs must be positive")

    pv_factor = _draw_normal(rng, 1.0, pv_yield_pct, n_runs, floor=0.0)
    capex_draw = _draw_normal(rng, inputs.capex_egp, capex_var_pct, n_runs, floor=0.0)
    opex_draw = _draw_normal(rng, inputs.opex_egp, opex_var_pct, n_runs, floor=0.0)
    esc_draw = np.clip(
        rng.normal(base_esc, base_esc * (esc_var_pct / 100.0), n_runs), -0.5, 1.0
    )

    year1_savings_draw = inputs.year1_pv_savings_egp * pv_factor

    npvs = np.empty(n_runs)
    paybacks = np.full(n_runs, np.nan)
    for i in range(n_runs):
        npvs[i] = _npv_for_draw(
            year1_savings_draw[i], capex_draw[i], opex_draw[i], esc_draw[i], deg, n_years, disc
        )
        pb = _payback_for_draw(
            year1_savings_draw[i], capex_draw[i], opex_draw[i], esc_draw[i], deg, n_years
        )
        if pb is not None:
            paybacks[i] = pb

    valid_paybacks = paybacks[~np.isnan(paybacks)]
    prob_target = None
    if target_payback_years is not None and len(valid_paybacks) > 0:
        prob_target = float((valid_paybacks <= target_payback_years).mean() * 100.0)

    def pct(arr: np.ndarray, q: float) -> float:
        return float(np.percentile(arr, q))

    payback_p10 = pct(valid_paybacks, 10) if len(valid_paybacks) else None
    payback_p50 = pct(valid_paybacks, 50) if len(valid_paybacks) else None
    payback_p90 = pct(valid_paybacks, 90) if len(valid_paybacks) else None

    drivers = _sensitivity_drivers(inputs, assumptions, base_esc, deg, n_years, disc)

    return RiskSimulationSummary(
        runCount=n_runs,
        seed=seed,
        paybackP10Years=payback_p10,
        paybackP50Years=payback_p50,
        paybackP90Years=payback_p90,
        probabilityTargetPaybackPct=prob_target,
        npvP10Egp=pct(npvs, 10),
        npvP50Egp=pct(npvs, 50),
        npvP90Egp=pct(npvs, 90),
        topSensitivityDrivers=drivers,
    )


def _sensitivity_drivers(
    inputs: RiskInputs,
    assumptions: AssumptionSet,
    base_esc: float,
    deg: float,
    n_years: int,
    disc: float,
) -> list[SensitivityDriver]:
    """One-at-a-time +/-1 std swing in NPV for each uncertain variable."""
    base_npv = _npv_for_draw(
        inputs.year1_pv_savings_egp, inputs.capex_egp, inputs.opex_egp, base_esc, deg, n_years, disc
    )

    def swing(**kwargs) -> float:
        lo = _npv_for_draw(
            kwargs.get("savings", inputs.year1_pv_savings_egp),
            kwargs.get("capex", inputs.capex_egp),
            kwargs.get("opex", inputs.opex_egp),
            kwargs.get("esc", base_esc),
            deg,
            n_years,
            disc,
        )
        return abs(lo - base_npv)

    pv_std = inputs.year1_pv_savings_egp * (assumptions.number("irradiance_variability_pct") / 100.0)
    capex_std = inputs.capex_egp * (assumptions.number("capex_variability_pct") / 100.0)
    opex_std = inputs.opex_egp * (assumptions.number("opex_variability_pct") / 100.0)
    esc_std = base_esc * (assumptions.number("tariff_escalation_variability_pct") / 100.0)

    raw = {
        "pv_yield": swing(savings=inputs.year1_pv_savings_egp + pv_std),
        "capex": swing(capex=inputs.capex_egp + capex_std),
        "opex": swing(opex=inputs.opex_egp + opex_std),
        "tariff_escalation": swing(esc=base_esc + esc_std),
    }
    total = sum(raw.values()) or 1.0
    ranked = sorted(raw.items(), key=lambda kv: kv[1], reverse=True)
    return [SensitivityDriver(variable=k, influence=v / total) for k, v in ranked]
