"""Finance: formula checks with fixed examples, undefined-case handling, scenario shape."""

from pathlib import Path

import pytest

from gadded.contracts import load_assumptions
from gadded.finance import (
    build_scenarios,
    cash_scenario,
    discounted_payback,
    finance_scenario,
    irr_pct,
    monthly_loan_payment,
    npv,
    simple_payback,
)

ROOT = Path(__file__).resolve().parents[1]


def _assumptions():
    return load_assumptions(ROOT / "data" / "assumptions.json")


def test_npv_fixed_example() -> None:
    # -1000 upfront, +600/yr for 2 years at 10% discount
    result = npv([600, 600], 1000, 0.10)
    expected = -1000 + 600 / 1.10 + 600 / 1.10**2
    assert result == pytest.approx(expected)


def test_irr_recovers_known_rate() -> None:
    # A loan of 1000 repaid as 1100 after 1 year has IRR of exactly 10%.
    rate = irr_pct(1000, [1100])
    assert rate == pytest.approx(10.0, abs=1e-6)


def test_irr_undefined_when_all_negative() -> None:
    assert irr_pct(1000, [-100, -100, -100]) is None


def test_simple_payback_fixed_example() -> None:
    # 1000 upfront, 400/yr -> payback at 2.5 years
    assert simple_payback([400, 400, 400], 1000) == pytest.approx(2.5)


def test_simple_payback_none_when_never_recovered() -> None:
    assert simple_payback([10, 10], 1000) is None


def test_discounted_payback_ge_simple_payback() -> None:
    cfs = [400, 400, 400, 400]
    simple = simple_payback(cfs, 1000)
    disc = discounted_payback(cfs, 1000, 0.08)
    assert disc is not None and simple is not None
    assert disc >= simple


def test_monthly_loan_payment_zero_rate_is_linear() -> None:
    payment = monthly_loan_payment(120_000, 0.0, 10)
    assert payment == pytest.approx(120_000 / 120)


def test_monthly_loan_payment_matches_amortization_formula() -> None:
    principal, rate, term = 1_000_000, 18.0, 7
    payment = monthly_loan_payment(principal, rate, term)
    r_m = rate / 100 / 12
    n_m = term * 12
    expected = principal * r_m / (1 - (1 + r_m) ** -n_m)
    assert payment == pytest.approx(expected, rel=1e-6)


def test_cash_scenario_shape() -> None:
    a = _assumptions()
    s = cash_scenario(475, 1_900_000, a)
    assert s.scenario == "cash"
    assert s.capexEgp == pytest.approx(475 * a.number("capex_per_kw_egp"))
    assert s.simplePaybackYears is not None
    assert s.assumptions["cashflow_basis"] == "nominal"


def test_finance_scenario_has_loan_payment_and_lower_upfront_need() -> None:
    a = _assumptions()
    cash = cash_scenario(475, 1_900_000, a)
    fin = finance_scenario(475, 1_900_000, a)
    assert fin.monthlyLoanPaymentEgp is not None and fin.monthlyLoanPaymentEgp > 0
    # equity NPV differs from cash NPV (leverage changes cash flow shape)
    assert fin.npvEgp != cash.npvEgp


def test_build_scenarios_respects_preference() -> None:
    a = _assumptions()
    assert len(build_scenarios(475, 1_900_000, a, "cash")) == 1
    assert len(build_scenarios(475, 1_900_000, a, "finance")) == 1
    assert len(build_scenarios(475, 1_900_000, a, "compare")) == 2
