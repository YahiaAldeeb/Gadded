"""Load-profile ML: clustering + classifier, evaluated against the deterministic baseline.

This is the actual machine learning in the load module (``load.py``'s archetype baseline
is not ML — it is a fixed lookup). Pipeline:

1. Generate a synthetic population of "facilities" (parametric variants of the six
   sector|shift archetypes in ``data/load_archetypes/archetypes.json``, with jittered
   parameters and hourly noise) It does not represent measured factories.
2. Cluster the facilities' normalized weekly (168-hour) load shapes with KMeans. The
   number of clusters is chosen by silhouette score sweep, not by intuition.
3. Train a classifier that maps simple user-facing inputs (sector, shift pattern,
   working days, shift hours) to a cluster, evaluated on facilities held out at the
   facility level (not random hourly rows) and compared against a simple majority-lookup
   baseline.
4. At inference time, low classifier confidence falls back to the deterministic
   archetype baseline (``load.estimate_load_baseline``), never a low-quality ML guess.

Because the synthetic generator is itself built from six known parametric groups,
recovering ~6 clusters validates the *technique* (clustering + classification), not a
discovery of real hidden structure in measured factories.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    adjusted_rand_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
    silhouette_score,
)
from sklearn.model_selection import train_test_split

from gadded.contracts import AssessmentInput, Confidence, LoadPredictionResult
from gadded.load import (
    LoadProfile,
    default_shift_hours,
    estimate_load_baseline,
    load_archetype_spec,
    reconcile_to_monthly,
    tile_week_shape_to_index,
    week_shape_from_params,
)

LOAD_ML_MODEL_VERSION = "load-cluster-classifier-0.1.0"
_ARTIFACT_DIR = Path(__file__).resolve().parents[2] / "data" / "load_archetypes"
FEATURE_NAMES = [
    "Sector Food Processing",
    "Sector Textiles",
    "Shift Day Shift",
    "Shift Two Shifts",
    "Shift Continuous",
    "Working Days/Week",
    "Shift Start Hour",
    "Shift End Hour",
]

@dataclass
class SyntheticFacility:
    facility_id: str
    sector: str
    shift_pattern: str
    working_days_per_week: int
    shift_start_hour: int
    shift_end_hour: int
    combo_label: (
        str  # ground-truth sector|shift, evaluation only, never a model feature
    )
    week_shape: np.ndarray  # normalized 168-length


@dataclass
class LoadMlBundle:
    """Everything inference needs. Serializable with joblib; metrics are plain floats."""

    classifier: RandomForestClassifier
    cluster_shapes: dict[int, np.ndarray]  # cluster id -> mean normalized 168-shape
    version: str
    metrics: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# 1. Synthetic facility population
# --------------------------------------------------------------------------- #


def generate_synthetic_facilities(
    seed: int = 42, n_per_combo: int = 40
) -> list[SyntheticFacility]:
    """Build a labeled synthetic facility population from the archetype spec.

    Explicitly SYNTHETIC: parametric jitter + noise around six known archetype
    combinations, not measured interval data.
    """
    spec = load_archetype_spec()
    weekend_days = set(spec["defaults"]["weekend_days"])
    rng = np.random.default_rng(seed)

    facilities: list[SyntheticFacility] = []
    for combo, arch in spec["archetypes"].items():
        sector, shift = combo.split("|")
        base = float(arch["base_fraction"])
        weekend_factor = float(arch["weekend_base_factor"])
        default_start, default_end = default_shift_hours(spec, shift)

        for i in range(n_per_combo):
            jittered_base = float(np.clip(base * (1 + rng.normal(0, 0.15)), 0.02, 0.95))
            jittered_weekend = float(
                np.clip(weekend_factor * (1 + rng.normal(0, 0.10)), 0.3, 1.2)
            )
            start = int(np.clip(default_start + rng.integers(-1, 2), 0, 22))
            end = int(np.clip(default_end + rng.integers(-1, 2), start + 1, 24))
            working_days = int(
                np.clip(7 - len(weekend_days) + rng.integers(-1, 2), 4, 7)
            )

            shape = week_shape_from_params(
                jittered_base, jittered_weekend, weekend_days, working_days, start, end
            )
            noisy = np.clip(shape + rng.normal(0, 0.03, size=168), 0.0, None)
            normalized = noisy / noisy.sum()

            facilities.append(
                SyntheticFacility(
                    facility_id=f"{combo}-{i:03d}",
                    sector=sector,
                    shift_pattern=shift,
                    working_days_per_week=working_days,
                    shift_start_hour=start,
                    shift_end_hour=end,
                    combo_label=combo,
                    week_shape=normalized, # 7 * 24 = (168,)
                )
            )
    return facilities


# --------------------------------------------------------------------------- #
# Feature encoding (shared by training and inference)
# --------------------------------------------------------------------------- #


def encode_features(
    sector: str,
    shift_pattern: str,
    working_days_per_week: int,
    shift_start_hour: int,
    shift_end_hour: int,
) -> list[float]:
    """Simple explicit one-hot + numeric encoding — no fitted encoder object to version."""
    return [
        1.0 if sector == "food_processing" else 0.0,
        1.0 if sector == "textiles" else 0.0,
        1.0 if shift_pattern == "day_shift" else 0.0,
        1.0 if shift_pattern == "two_shifts" else 0.0,
        1.0 if shift_pattern == "continuous" else 0.0,
        float(working_days_per_week),
        float(shift_start_hour),
        float(shift_end_hour),
    ]


def _facility_features(f: SyntheticFacility) -> list[float]:
    return encode_features(
        f.sector,
        f.shift_pattern,
        f.working_days_per_week,
        f.shift_start_hour,
        f.shift_end_hour,
    )


# --------------------------------------------------------------------------- #
# 2 + 3. Clustering, classifier, evaluation vs baseline
# --------------------------------------------------------------------------- #


def _choose_k(shapes: np.ndarray, seed: int, k_range: range = range(2, 9)) -> int:
    """Pick cluster count by silhouette score, not intuition."""
    best_k, best_score = k_range.start, -1.0
    for k in k_range:
        labels = KMeans(n_clusters=k, random_state=seed, n_init=10).fit_predict(shapes)
        score = silhouette_score(shapes, labels)
        if score > best_score:
            best_k, best_score = k, score
    return best_k


def train_load_ml_model(
    seed: int = 42, n_per_combo: int = 15, test_size: float = 0.25
) -> LoadMlBundle:
    """Full reproducible training script: generate -> split -> cluster -> classify -> evaluate."""
    # Unsupervised learning (clustering) -> KMeans, Supervised learning (classification) -> RandomForestClassifier
    facilities = generate_synthetic_facilities(seed=seed, n_per_combo=n_per_combo)

    # train -> 180, test -> 60
    train, test = train_test_split(
        facilities,
        test_size=test_size,
        random_state=seed,
        stratify=[f.combo_label for f in facilities],
    )

    # [0.1, 0.4, 0.2, 0.3] sum = 1
    train_shapes = np.array([f.week_shape for f in train])
    test_shapes = np.array([f.week_shape for f in test])

    k = _choose_k(train_shapes, seed) # k = 6 no_of_clusters
    kmeans = KMeans(n_clusters=k, random_state=seed, n_init=10).fit(train_shapes)
    train_labels = kmeans.labels_ # belong to [0, 1, 2, 3, 4, 5] for k=6
    test_labels = kmeans.predict(
        test_shapes
    )  # test facilities assigned via train-fit geometry

    # Cluster ID: facilities average week_shape mapped to mean normalized 168-shape (used for inference).
    cluster_shapes = {
        int(c): train_shapes[train_labels == c].mean(axis=0) for c in range(k)
    }

    train_X = np.array([_facility_features(f) for f in train])
    test_X = np.array([_facility_features(f) for f in test])

    classifier = RandomForestClassifier(n_estimators=200, random_state=seed)
    # Train the classifier to map assumptions (after encoding) 
    # e.g., sector, shift pattern, working days, etc... to a cluster ID
    classifier.fit(train_X, train_labels)
    pred_labels = classifier.predict(test_X)
    # How well can the classifier reproduce the cluster assignments that KMeans made using only facility metadata?
    classifier_accuracy = float(accuracy_score(test_labels, pred_labels))

    precision, recall, f1, _ = precision_recall_fscore_support(test_labels, pred_labels, average="macro", zero_division=0)

    conf_matrix = confusion_matrix(test_labels, pred_labels).tolist()

    report = classification_report(test_labels, pred_labels, zero_division=0)

    feature_importance = dict(
        sorted(zip(FEATURE_NAMES, classifier.feature_importances_, strict=True), key=lambda x: x[1], reverse=True)
    )

    # Baseline: majority train-cluster per (sector, shift) combo — a lookup, not a model.
    cluster_by_combo: defaultdict[str, list[int]] = defaultdict(list)

    for facility, cluster in zip(train, train_labels, strict=True):
        cluster_by_combo[facility.combo_label].append(cluster)

    combo_majority = {combo: int(np.bincount(clusters).argmax()) for combo, clusters in cluster_by_combo.items()}

    baseline_pred = [combo_majority.get(f.combo_label, -1) for f in test]
    baseline_accuracy = float(accuracy_score(test_labels, baseline_pred))

    # Did KMeans naturally rediscover the original archetypes?
    ari = float(adjusted_rand_score([f.combo_label for f in test], test_labels))
    sil = float(silhouette_score(train_shapes, train_labels))
    print(
    f"""\
================ Load ML Training Summary ================

Train facilities : {len(train)}
Test facilities  : {len(test)}

Chosen clusters (K)      : {k}

Classifier
----------
Accuracy                 : {classifier_accuracy:.4f}
Precision (macro)        : {precision:.4f}
Recall (macro)           : {recall:.4f}
F1-score (macro)         : {f1:.4f}

Baseline lookup accuracy : {baseline_accuracy:.4f}

Clustering
----------
Silhouette score         : {sil:.4f}
Adjusted Rand Index      : {ari:.4f}

Feature importance
------------------
    """)

    for name, score in sorted(
        feature_importance.items(),
        key=lambda x: x[1],
        reverse=True,
    ):
        print(f"{name:<28} {score:.4f}")

    print("\nConfusion Matrix")
    print(np.array(conf_matrix))

    print("\nClassification Report")
    print(report)

    metrics = {
        "chosen_k": k,
        "train_facility_count": len(train),
        "test_facility_count": len(test),
        "classifier_test_accuracy": classifier_accuracy,
        "classifier_precision_macro": float(precision),
        "classifier_recall_macro": float(recall),
        "classifier_f1_macro": float(f1),
        "baseline_test_accuracy": baseline_accuracy,
        "silhouette_score_train": sil,
        "adjusted_rand_index_vs_combo_label": ari,
        "feature_importance": feature_importance,
        "confusion_matrix": conf_matrix,
        "seed": seed,
        "limitations": (
            "Trained entirely on a synthetic parametric population, not measured Egyptian "
            "factory interval data. Cluster recovery validates the clustering+classification "
            "technique; it is not a discovery of real hidden structure."
        ),
    }
    return LoadMlBundle(
        classifier=classifier,
        cluster_shapes=cluster_shapes,
        version=LOAD_ML_MODEL_VERSION,
        metrics=metrics,
    )


# --------------------------------------------------------------------------- #
# Persistence
# --------------------------------------------------------------------------- #


def save_bundle(
    bundle: LoadMlBundle, path: str | Path = _ARTIFACT_DIR / "load_ml_bundle.joblib"
) -> None:
    joblib.dump(bundle, path)


def load_bundle(
    path: str | Path = _ARTIFACT_DIR / "load_ml_bundle.joblib",
) -> LoadMlBundle:
    return joblib.load(path)


# --------------------------------------------------------------------------- #
# 4. Inference, with fallback to the deterministic baseline
# --------------------------------------------------------------------------- #

_CONFIDENCE_HIGH = 0.70
_CONFIDENCE_MEDIUM = 0.40


def confidence_label(max_proba: float) -> Confidence:
    if max_proba >= _CONFIDENCE_HIGH:
        return "high"
    if max_proba >= _CONFIDENCE_MEDIUM:
        return "medium"
    return "low"


def predict_load_ml(
    ai: AssessmentInput,
    index: pd.DatetimeIndex,
    bundle: LoadMlBundle,
    reconciliation_tolerance_pct: float = 2.0,
) -> LoadProfile:
    """Predict the hourly load series via the trained classifier; fall back on low confidence."""
    features = np.array(
        [
            encode_features(
                ai.factory.sector,
                ai.factory.shiftPattern,
                ai.factory.workingDaysPerWeek,
                ai.factory.shiftStartHour
                or default_shift_hours(load_archetype_spec(), ai.factory.shiftPattern)[
                    0
                ],
                ai.factory.shiftEndHour
                or default_shift_hours(load_archetype_spec(), ai.factory.shiftPattern)[
                    1
                ],
            )
        ]
    )
     # belong to [0, 1, 2, 3, 4, 5] for k=6
    proba = bundle.classifier.predict_proba(features)[0]
    cluster_id = int(bundle.classifier.classes_[np.argmax(proba)]) # Cluster = 0
    max_proba = float(proba.max())
    confidence = confidence_label(max_proba)

    if confidence == "low":
        fallback = estimate_load_baseline(ai, index, reconciliation_tolerance_pct)
        fallback.result.warnings.append(
            f"ML classifier confidence low ({max_proba:.2f}); fell back to deterministic "
            f"archetype baseline. model_version={bundle.version}, fallback_version={fallback.result.modelVersion}"
        )
        fallback.result.modelVersion = (
            f"{bundle.version}+fallback:{fallback.result.modelVersion}"
        )
        return fallback

    cluster_week_shape = bundle.cluster_shapes[cluster_id] # [0.1, 0.4, 0.2, 0.3] sum = 1
    # Tilting
    raw = tile_week_shape_to_index(cluster_week_shape, index)
    # Scaling to match the submitted monthly consumption
    scaled, monthly_kwh, recon_err, warnings = reconcile_to_monthly(
        raw, index, ai.factory.monthlyConsumptionKwh
    )
    annual = float(scaled.sum())

    warnings.append(
        "ML load profile: KMeans clustering + RandomForest classifier trained on a "
        "synthetic facility population (see load_ml.py); not measured interval data."
    )
    if recon_err > reconciliation_tolerance_pct:
        warnings.append(
            f"reconciliation error {recon_err:.2f}% exceeds tolerance {reconciliation_tolerance_pct:.2f}%"
        )

    result = LoadPredictionResult(
        seriesArtifactId=f"load_ml_cluster{cluster_id}_{bundle.version}",
        annualConsumptionKwh=annual,
        archetypeId=f"cluster-{cluster_id}@{bundle.version}",
        modelVersion=bundle.version,
        confidence=confidence,
        reconciliationErrorPct=recon_err,
        warnings=warnings,
    )
    return LoadProfile(series=scaled.to_frame(), result=result, monthly_kwh=monthly_kwh)
