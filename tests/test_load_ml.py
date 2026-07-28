"""Load ML: synthetic population sanity, clustering/classifier evaluation, fallback safety."""

from pathlib import Path

import numpy as np
import pytest

from gadded.contracts import load_assessment_input
from gadded.load_ml import (
    LOAD_ML_MODEL_VERSION,
    LoadMlBundle,
    confidence_label,
    generate_synthetic_facilities,
    load_bundle,
    predict_load_ml,
    save_bundle,
    train_load_ml_model,
)
from gadded.weather import load_cached_weather

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "weather_10ramadan_cached.csv"


@pytest.fixture(scope="module")
def bundle() -> LoadMlBundle:
    return train_load_ml_model(seed=42, n_per_combo=15)


def test_synthetic_population_shape() -> None:
    facilities = generate_synthetic_facilities(seed=1, n_per_combo=10)
    assert len(facilities) == 6 * 10  # six archetype combos in archetypes.json
    for f in facilities:
        assert f.week_shape.shape == (168,)
        assert (f.week_shape >= 0).all()
        assert f.week_shape.sum() == pytest.approx(1.0, rel=1e-6)


def test_facility_ids_unique() -> None:
    facilities = generate_synthetic_facilities(seed=1, n_per_combo=10)
    ids = {f.facility_id for f in facilities}
    assert len(ids) == len(facilities)


def test_training_produces_metrics(bundle: LoadMlBundle) -> None:
    m = bundle.metrics
    assert m["chosen_k"] >= 2
    assert 0.0 <= m["classifier_test_accuracy"] <= 1.0
    assert 0.0 <= m["baseline_test_accuracy"] <= 1.0
    assert m["train_facility_count"] + m["test_facility_count"] == 6 * 15
    assert "synthetic" in m["limitations"].lower()


def test_classifier_at_least_close_to_baseline(bundle: LoadMlBundle) -> None:
    # The lookup baseline is strong by construction (sector+shift fully determines the
    # synthetic archetype); the classifier should be competitive with it, not far worse.
    m = bundle.metrics
    assert m["classifier_test_accuracy"] >= m["baseline_test_accuracy"] - 0.15


def test_confidence_label_thresholds() -> None:
    assert confidence_label(0.9) == "high"
    assert confidence_label(0.5) == "medium"
    assert confidence_label(0.1) == "low"
    assert confidence_label(0.70) == "high"
    assert confidence_label(0.40) == "medium"


def test_save_and_load_bundle_roundtrip(bundle: LoadMlBundle, tmp_path) -> None:
    path = tmp_path / "bundle.joblib"
    save_bundle(bundle, path)
    reloaded = load_bundle(path)
    assert reloaded.version == bundle.version
    assert reloaded.metrics["chosen_k"] == bundle.metrics["chosen_k"]


@pytest.mark.skipif(not CACHE.exists(), reason="cached weather CSV not present")
def test_predict_load_ml_reconciles_on_golden_case(bundle: LoadMlBundle) -> None:
    ai = load_assessment_input(ROOT / "data" / "golden_case.json")
    index = load_cached_weather(CACHE).frame.index
    profile = predict_load_ml(ai, index, bundle, reconciliation_tolerance_pct=2.0)

    submitted = ai.factory.monthlyConsumptionKwh
    for m in range(1, 13):
        assert profile.monthly_kwh[m] == pytest.approx(submitted[m - 1], rel=1e-6)
    assert (profile.series["load_kw"] >= 0).all()
    assert profile.result.confidence in ("high", "medium", "low")


class _FakeLowConfidenceClassifier:
    classes_ = np.array([0, 1, 2])

    def predict_proba(self, X):
        return np.array([[0.34, 0.33, 0.33]])


@pytest.mark.skipif(not CACHE.exists(), reason="cached weather CSV not present")
def test_low_confidence_falls_back_to_baseline() -> None:
    ai = load_assessment_input(ROOT / "data" / "golden_case.json")
    index = load_cached_weather(CACHE).frame.index
    fake_bundle = LoadMlBundle(
        classifier=_FakeLowConfidenceClassifier(),
        cluster_shapes={0: np.ones(168) / 168, 1: np.ones(168) / 168, 2: np.ones(168) / 168},
        version=LOAD_ML_MODEL_VERSION,
        metrics={},
    )
    profile = predict_load_ml(ai, index, fake_bundle)
    assert profile.result.confidence == "low"
    assert "fallback:archetype-baseline" in profile.result.modelVersion
    assert any("fell back" in w for w in profile.result.warnings)
    # still reconciles even on the fallback path
    submitted = ai.factory.monthlyConsumptionKwh
    assert profile.monthly_kwh[1] == pytest.approx(submitted[0], rel=1e-6)
