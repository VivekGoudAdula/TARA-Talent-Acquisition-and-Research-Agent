"""Evaluation metrics for Repayment Capacity Prediction."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
)

from app.ml.dataset_builder.dataset_generator import (
    TARGET_HIGH,
    TARGET_LOW,
    TARGET_MEDIUM,
    TARGET_VERY_HIGH,
)

TARGET_ORDER = [TARGET_LOW, TARGET_MEDIUM, TARGET_HIGH, TARGET_VERY_HIGH]


def evaluate_multiclass(
    y_true: list[str] | np.ndarray,
    y_pred: list[str] | np.ndarray,
    y_proba: np.ndarray,
    labels: list[str] | None = None,
) -> dict[str, Any]:
    """Compute classification metrics for repayment capacity classes."""
    labels = labels or TARGET_ORDER
    label_to_idx = {label: i for i, label in enumerate(labels)}

    y_true_idx = np.array([label_to_idx[y] for y in y_true])
    y_pred_idx = np.array([label_to_idx[y] for y in y_pred])

    precision, recall, f1, support = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=labels,
        average=None,
        zero_division=0,
    )

    per_class = {
        label: {
            "precision": float(precision[i]),
            "recall": float(recall[i]),
            "f1": float(f1[i]),
            "support": int(support[i]),
        }
        for i, label in enumerate(labels)
    }

    metrics: dict[str, Any] = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_macro": float(np.mean(precision)),
        "recall_macro": float(np.mean(recall)),
        "f1_macro": float(np.mean(f1)),
        "per_class": per_class,
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
        "labels": labels,
    }

    if y_proba is not None and len(y_proba) > 0:
        try:
            metrics["roc_auc_ovr"] = float(
                roc_auc_score(
                    y_true_idx,
                    y_proba,
                    multi_class="ovr",
                    labels=list(range(len(labels))),
                )
            )
        except ValueError:
            metrics["roc_auc_ovr"] = None

    return metrics


def extract_feature_importance(
    pipeline: Any,
    feature_names: list[str],
) -> dict[str, float]:
    """Extract feature importances from a fitted sklearn pipeline."""
    classifier = pipeline.named_steps.get("classifier")
    selector = pipeline.named_steps.get("selector")

    if classifier is None or not hasattr(classifier, "feature_importances_"):
        return {}

    importances = classifier.feature_importances_
    if selector is not None and hasattr(selector, "get_support"):
        support = selector.get_support()
        selected_names = [name for name, keep in zip(feature_names, support) if keep]
    else:
        selected_names = feature_names

    if len(selected_names) != len(importances):
        selected_names = feature_names[: len(importances)]

    pairs = sorted(
        zip(selected_names, importances),
        key=lambda x: x[1],
        reverse=True,
    )
    return {name: float(score) for name, score in pairs}
