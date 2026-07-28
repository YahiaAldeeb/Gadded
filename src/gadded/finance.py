"""Deterministic cash and financing analysis for the recommended system.

Produces the reported ``FinancialScenario`` objects. Cash flows are in nominal EGP:
savings escalate with the tariff, generation declines with degradation, O&M is flat.
The discount rate is treated as nominal. Taxes, general inflation adjustment, inverter
replacement, and residual value are excluded (and labeled as such on each scenario).

All discounting matches ``optimization.project_npv`` so the cash NPV of the recommended
capacity reconciles with the sizing objective.
"""

from __future__ import annotations

import numpy as np
import numpy_financial as npf

from gadded.contracts import AssumptionSet, FinancialScenario

FINANCE_VERSION = "deterministic-0.1.0"


# --------------------------------------------------------------------------- #
# Core cash-flow helpers (pure, independently tested)
# --------------------------------------------------------------------------- #


def savings_stream(year1_savings: float, annual_opex: float, n: int, esc: float, deg: float) -> list[float]:
    """Net annual cash flow (savings minus O&M) for years 1..n."""
    out = []
    for t in range(1, n + 1):
        savings_t = year1_savings * ((1 + esc) ** (t - 1)) * ((1 - deg) ** (t - 1))
        out.append(savings_t - annual_opex)
    return out


def npv(cash_flows: list[float], upfront: float, disc: float) -> float:
    """NPV of a stream that starts with -upfront at t=0."""
    total = -upfront
    for t, cf in enumerate(cash_flows, start=1):
        total += cf / ((1 + disc) ** t)
    return total


def irr_pct(upfront: float, cash_flows: list[float]) -> float | None:
    """Internal rate of return in percent, or None if undefined."""
    series = [-upfront, *cash_flows]
    try:
        r = npf.irr(series)
    except (ValueError, FloatingPointError):
        return None
    if r is None or np.isnan(r):
        return None
    return float(r * 100.0)


def simple_payback(cash_flows: list[float], target: float) -> float | None:
    """Years to recover `target` from undiscounted cash flows, with fractional interpolation."""
    cum = 0.0
    for t, cf in enumerate(cash_flows, start=1):
        prev = cum
        cum += cf
        if cum >= target:
            if cf <= 0:
                return float(t)
            return (t - 1) + (target - prev) / cf
    return None


def discounted_payback(cash_flows: list[float], target: float, disc: float) -> float | None:
    """Years to recover `target` from discounted cash flows."""
    cum = 0.0
    for t, cf in enumerate(cash_flows, start=1):
        dcf = cf / ((1 + disc) ** t)
        prev = cum
        cum += dcf
        if cum >= target:
            if dcf <= 0:
                return float(t)
            return (t - 1) + (target - prev) / dcf
    return None


def monthly_loan_payment(principal: float, annual_rate_pct: float, term_years: int) -> float:
    """Fixed monthly amortizing payment (positive EGP)."""
    if principal <= 0:
        return 0.0
    r_m = annual_rate_pct / 100.0 / 12.0
    n_m = term_years * 12
    if r_m == 0:
        return principal / n_m
    return float(-npf.pmt(r_m, n_m, principal))


# --------------------------------------------------------------------------- #
# Scenario builders
# --------------------------------------------------------------------------- #


def _shared_assumptions(a: AssumptionSet) -> dict[str, float | str]:
    return {
        "capex_per_kw_egp": a.number("capex_per_kw_egp"),
        "opex_per_kw_year_egp": a.number("opex_per_kw_year_egp"),
        "discount_rate_pct": a.number("discount_rate_pct"),
        "analysis_period_years": a.number("analysis_period_years"),
        "tariff_escalation_pct": a.number("tariff_escalation_pct"),
        "degradation_pct_year": a.number("degradation_pct_year"),
        "cashflow_basis": "nominal",
        "includes": "opex, tariff_escalation, panel_degradation",
        "excludes": "tax, general_inflation_adjustment, inverter_replacement, residual_value",
    }


def cash_scenario(
    capacity_kw: float, year1_savings: float, assumptions: AssumptionSet
) -> FinancialScenario:
    """All-equity purchase."""
    n = int(assumptions.number("analysis_period_years"))
    disc = assumptions.number("discount_rate_pct") / 100.0
    esc = assumptions.number("tariff_escalation_pct") / 100.0
    deg = assumptions.number("degradation_pct_year") / 100.0
    capex = capacity_kw * assumptions.number("capex_per_kw_egp")
    opex = capacity_kw * assumptions.number("opex_per_kw_year_egp")

    cfs = savings_stream(year1_savings, opex, n, esc, deg)
    return FinancialScenario(
        scenario="cash",
        capexEgp=capex,
        annualOpexEgp=opex,
        yearOneSavingsEgp=year1_savings - opex,
        npvEgp=npv(cfs, capex, disc),
        irrPct=irr_pct(capex, cfs),
        simplePaybackYears=simple_payback(cfs, capex),
        discountedPaybackYears=discounted_payback(cfs, capex, disc),
        assumptions=_shared_assumptions(assumptions),
    )


def finance_scenario(
    capacity_kw: float, year1_savings: float, assumptions: AssumptionSet
) -> FinancialScenario:
    """Debt-financed purchase: down payment + amortizing loan."""
    n = int(assumptions.number("analysis_period_years"))
    disc = assumptions.number("discount_rate_pct") / 100.0
    esc = assumptions.number("tariff_escalation_pct") / 100.0
    deg = assumptions.number("degradation_pct_year") / 100.0
    capex = capacity_kw * assumptions.number("capex_per_kw_egp")
    opex = capacity_kw * assumptions.number("opex_per_kw_year_egp")

    down_pct = assumptions.number("down_payment_pct") / 100.0
    fees_pct = assumptions.number("financing_fees_pct") / 100.0
    rate = assumptions.number("financing_rate_pct")
    term = int(assumptions.number("financing_term_years"))

    down_payment = capex * down_pct
    upfront_fees = capex * fees_pct
    principal = capex - down_payment
    monthly = monthly_loan_payment(principal, rate, term)
    annual_debt = monthly * 12.0

    gross = savings_stream(year1_savings, opex, n, esc, deg)  # savings - opex
    equity_cfs = [cf - (annual_debt if t <= term else 0.0) for t, cf in enumerate(gross, start=1)]
    upfront_equity = down_payment + upfront_fees

    return FinancialScenario(
        scenario="finance",
        capexEgp=capex,
        annualOpexEgp=opex,
        yearOneSavingsEgp=year1_savings - opex,
        npvEgp=npv(equity_cfs, upfront_equity, disc),
        irrPct=irr_pct(upfront_equity, equity_cfs),
        simplePaybackYears=simple_payback(equity_cfs, upfront_equity),
        discountedPaybackYears=discounted_payback(equity_cfs, upfront_equity, disc),
        monthlyLoanPaymentEgp=monthly,
        assumptions={
            **_shared_assumptions(assumptions),
            "financing_rate_pct": rate,
            "financing_term_years": term,
            "down_payment_pct": assumptions.number("down_payment_pct"),
            "financing_fees_pct": assumptions.number("financing_fees_pct"),
        },
    )


def build_scenarios(
    capacity_kw: float, year1_savings: float, assumptions: AssumptionSet, preference: str
) -> list[FinancialScenario]:
    """Return the scenarios requested by the finance preference (cash, finance, or compare)."""
    if preference == "cash":
        return [cash_scenario(capacity_kw, year1_savings, assumptions)]
    if preference == "finance":
        return [finance_scenario(capacity_kw, year1_savings, assumptions)]
    return [
        cash_scenario(capacity_kw, year1_savings, assumptions),
        finance_scenario(capacity_kw, year1_savings, assumptions),
    ]
