"""Inference for Repayment Capacity Prediction."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.ml.repayment.evaluation import TARGET_ORDER
from app.ml.repayment.registry import RepaymentModelRegistry
from app.ml.repayment.training import FEATURE_COLUMNS
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class RepaymentPredictor:
    """Loads a trained repayment model and produces predictions."""

    def __init__(self, registry: RepaymentModelRegistry | None = None) -> None:
        self._registry = registry or RepaymentModelRegistry()
        self._artifact: dict[str, Any] | None = None

    def load(self) -> None:
        self._artifact = self._registry.load_model()

    @property
    def is_loaded(self) -> bool:
        return self._artifact is not None

    def predict(self, features: dict[str, Any]) -> dict[str, Any]:
        if self._artifact is None:
            self.load()

        assert self._artifact is not None
        pipeline = self._artifact["pipeline"]
        label_encoder = self._artifact.get("label_encoder")
        metadata = self._artifact.get("metadata", {})

        row = {col: features.get(col) for col in FEATURE_COLUMNS}
        df = pd.DataFrame([row])

        proba = pipeline.predict_proba(df)[0]
        pred_enc = pipeline.predict(df)[0]

        if label_encoder is not None:
            pred_label = label_encoder.inverse_transform([pred_enc])[0]
            class_labels = list(label_encoder.classes_)
        else:
            pred_label = pred_enc
            class_labels = list(pipeline.classes_)

        probabilities = {str(cls): float(p) for cls, p in zip(class_labels, proba)}
        ordered_probs = {label: probabilities.get(label, 0.0) for label in TARGET_ORDER}

        return {
            "repayment_capacity": str(pred_label),
            "confidence": float(np.max(proba)),
            "probabilities": ordered_probs,
            "model_used": metadata.get("best_model", "unknown"),
        }
