"""Risk: reproducibility, percentile ordering, probability, and sensitivity ranking."""

from pathlib import Path

import pytest

from gadded.contracts import load_assumptions
from gadded.risk import RiskInputs, run_monte_carlo

ROOT = Path(__file__).resolve().parents[1]


def _inputs() -> RiskInputs:
    return RiskInputs(
        capacity_kw=475,
        year1_pv_savings_egp=1_900_000,
        capex_egp=475 * 32_000,
        opex_egp=475 * 500,
    )


def test_fixed_seed_is_reproducible() -> None:
    a = load_assumptions(ROOT / "data" / "assumptions.json")
    r1 = run_monte_carlo(_inputs(), a, target_payback_years=6, seed=123, runs=500)
    r2 = run_monte_carlo(_inputs(), a, target_payback_years=6, seed=123, runs=500)
    assert r1.npvP50Egp == r2.npvP50Egp
    assert r1.paybackP50Years == r2.paybackP50Years


def test_different_seed_can_differ() -> None:
    a = load_assumptions(ROOT / "data" / "assumptions.json")
    r1 = run_monte_carlo(_inputs(), a, seed=1, runs=500)
    r2 = run_monte_carlo(_inputs(), a, seed=2, runs=500)
    assert r1.npvP50Egp != r2.npvP50Egp


def test_percentiles_ordered() -> None:
    a = load_assumptions(ROOT / "data" / "assumptions.json")
    r = run_monte_carlo(_inputs(), a, target_payback_years=6, seed=42, runs=2000)
    assert r.npvP10Egp <= r.npvP50Egp <= r.npvP90Egp
    assert r.paybackP10Years <= r.paybackP50Years <= r.paybackP90Years


def test_probability_target_in_range() -> None:
    a = load_assumptions(ROOT / "data" / "assumptions.json")
    r = run_monte_carlo(_inputs(), a, target_payback_years=6, seed=42, runs=2000)
    assert 0.0 <= r.probabilityTargetPaybackPct <= 100.0


def test_invalid_run_count_rejected() -> None:
    a = load_assumptions(ROOT / "data" / "assumptions.json")
    with pytest.raises(ValueError):
        run_monte_carlo(_inputs(), a, seed=1, runs=0)


def test_sensitivity_drivers_rank_and_sum_to_one() -> None:
    a = load_assumptions(ROOT / "data" / "assumptions.json")
    r = run_monte_carlo(_inputs(), a, seed=42, runs=500)
    assert len(r.topSensitivityDrivers) == 4
    influences = [d.influence for d in r.topSensitivityDrivers]
    assert influences == sorted(influences, reverse=True)
    assert sum(influences) == pytest.approx(1.0, rel=1e-6)


def test_run_count_and_seed_recorded() -> None:
    a = load_assumptions(ROOT / "data" / "assumptions.json")
    r = run_monte_carlo(_inputs(), a, seed=42, runs=777)
    assert r.runCount == 777
    assert r.seed == 42
