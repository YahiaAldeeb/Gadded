"""Constrained PV system sizing.

Generates candidate capacities from roof area (and any budget ceiling), evaluates each
by project NPV, and returns the capacity that maximizes NPV subject to constraints. The
recommendation is never chosen as "the largest" by default — the objective decides, and
the full candidate table is returned so the choice is explainable.

Efficiency: PV output is linear in capacity, so the hourly PV shape is modeled once per
kW (via ``pv.generate_pv`` at 1 kW) and scaled per candidate. Self-consumption is the
nonlinear part, so load/PV matching is recomputed for each candidate.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from gadded.contracts import AssessmentInput, AssumptionSet, TechnicalRecommendation
from gadded.matching import MatchResult, match_load_and_pv
from gadded.pv import generate_pv
from gadded.weather import WeatherDataset

OPTIMIZER_VERSION = "npv-grid-search-0.1.0"


@dataclass
class OptimizationResult:
    recommendation: TechnicalRecommendation
    table: pd.DataFrame  # per-candidate: capacity_kw, npv_egp, self_consumption_ratio, ...
    best_match: MatchResult


def project_npv(
    year1_savings_egp: float,
    capex_egp: float,
    annual_opex_egp: float,
    assumptions: AssumptionSet,
) -> float:
    """Discounted-cash-flow NPV of a project (real terms, deterministic).

    Savings grow with tariff escalation and shrink with panel degradation; O&M is held
    flat. This is the sizing *objective*; ``finance`` produces the full reported scenarios.
    """
    n = int(assumptions.number("analysis_period_years"))
    disc = assumptions.number("discount_rate_pct") / 100.0
    esc = assumptions.number("tariff_escalation_pct") / 100.0
    deg = assumptions.number("degradation_pct_year") / 100.0

    npv = -capex_egp
    for t in range(1, n + 1):
        savings_t = year1_savings_egp * ((1 + esc) ** (t - 1)) * ((1 - deg) ** (t - 1))
        cash_flow = savings_t - annual_opex_egp
        npv += cash_flow / ((1 + disc) ** t)
    return npv


def _candidate_capacities(
    ai: AssessmentInput, assumptions: AssumptionSet
) -> tuple[list[float], float, list[str]]:
    area_per_kw = assumptions.number("area_per_kw_m2")
    step = assumptions.number("capacity_step_kw")
    capex_per_kw = assumptions.number("capex_per_kw_egp")

    physical_max = ai.site.availableRoofAreaM2 / area_per_kw
    limit = physical_max
    binding: list[str] = []

    if ai.finance.budgetCeilingEgp is not None:
        budget_max = ai.finance.budgetCeilingEgp / capex_per_kw
        if budget_max < limit:
            limit = budget_max
            binding.append("budget")

    caps = list(np.arange(step, limit + 1e-9, step))
    if not caps:
        caps = [min(step, limit)]
    # Allow an explicit target capacity to be compared if it fits.
    if ai.site.targetCapacityKw is not None and ai.site.targetCapacityKw <= physical_max:
        if ai.site.targetCapacityKw not in caps:
            caps.append(float(ai.site.targetCapacityKw))
            caps.sort()
    return [round(c, 3) for c in caps], physical_max, binding


def optimize_capacity(
    ai: AssessmentInput,
    weather: WeatherDataset,
    load_kw: pd.Series,
    assumptions: AssumptionSet,
) -> OptimizationResult:
    """Search candidate capacities and return the NPV-optimal recommendation."""
    caps, physical_max, binding = _candidate_capacities(ai, assumptions)
    area_per_kw = assumptions.number("area_per_kw_m2")
    capex_per_kw = assumptions.number("capex_per_kw_egp")
    opex_per_kw = assumptions.number("opex_per_kw_year_egp")

    unit_pv = generate_pv(weather, 1.0, assumptions).series["pv_kw"]  # per-kW hourly shape

    rows = []
    matches: dict[float, MatchResult] = {}
    for cap in caps:
        pv = unit_pv * cap
        pv.name = "pv_kw"
        m = match_load_and_pv(load_kw, pv, assumptions, ai.connectionModel)
        year1_savings = m.annual_retail_value_egp + m.annual_export_value_egp
        capex = cap * capex_per_kw
        opex = cap * opex_per_kw
        npv = project_npv(year1_savings, capex, opex, assumptions)
        matches[cap] = m
        rows.append(
            {
                "capacity_kw": cap,
                "npv_egp": npv,
                "capex_egp": capex,
                "year1_savings_egp": year1_savings,
                "self_consumption_ratio": m.self_consumption_ratio,
                "self_sufficiency_ratio": m.self_sufficiency_ratio,
                "annual_generation_kwh": m.annual_pv_kwh,
                "annual_self_kwh": m.annual_self_kwh,
                "annual_export_kwh": m.annual_export_kwh,
            }
        )

    table = pd.DataFrame(rows).set_index("capacity_kw", drop=False)
    best_cap = float(table["npv_egp"].idxmax())
    best = matches[best_cap]

    binding = list(binding)
    if best_cap >= max(caps) - 1e-9 and "budget" not in binding:
        binding.append("roof_area")
    if not binding:
        binding.append("economic_optimum")

    recommendation = TechnicalRecommendation(
        recommendedCapacityKw=best_cap,
        physicalMaximumKw=round(physical_max, 3),
        evaluatedCapacitiesKw=caps,
        annualGenerationKwh=best.annual_pv_kwh,
        annualLoadKwh=best.annual_load_kwh,
        selfConsumptionRatio=best.self_consumption_ratio,
        selfSufficiencyRatio=best.self_sufficiency_ratio,
        annualImportedKwh=best.annual_import_kwh,
        annualExportedKwh=best.annual_export_kwh,
        roofAreaRequiredM2=round(best_cap * area_per_kw, 2),
        bindingConstraints=binding,
        objectiveName="npv",
    )
    return OptimizationResult(recommendation=recommendation, table=table, best_match=best)
