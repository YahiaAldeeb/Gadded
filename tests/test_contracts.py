"""Layer 0 validation: golden case and assumptions load against the contracts."""

from pathlib import Path

import pytest

from gadded.contracts import (
    AssessmentInput,
    AssumptionSet,
    load_assessment_input,
    load_assumptions,
)

DATA = Path(__file__).resolve().parents[1] / "data"


def test_golden_case_validates() -> None:
    ai = load_assessment_input(DATA / "golden_case.json")
    assert isinstance(ai, AssessmentInput)
    assert ai.projectType == "industrial_rooftop"
    assert len(ai.factory.monthlyConsumptionKwh) == 12
    assert ai.site.availableRoofAreaM2 == 3000


def test_assumptions_validate_and_resolve() -> None:
    a = load_assumptions(DATA / "assumptions.json")
    assert isinstance(a, AssumptionSet)
    assert a.assumptionSet.status == "ACTIVE"
    # a few numeric keys the finance/pv/sizing modules will need
    for key in ("capex_per_kw_egp", "discount_rate_pct", "area_per_kw_m2"):
        assert a.number(key) > 0


def test_monthly_consumption_rejects_bad_length() -> None:
    data = load_assessment_input(DATA / "golden_case.json").model_dump()
    data["factory"]["monthlyConsumptionKwh"] = [1, 2, 3]
    with pytest.raises(ValueError):
        AssessmentInput.model_validate(data)


def test_latitude_out_of_range_rejected() -> None:
    data = load_assessment_input(DATA / "golden_case.json").model_dump()
    data["location"]["latitude"] = 200
    with pytest.raises(ValueError):
        AssessmentInput.model_validate(data)
