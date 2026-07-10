"""Inference for Lead Conversion Prediction."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.ml.conversion.training import FEATURE_COLUMNS, ConversionModelRegistry
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class ConversionPredictor:
    """Loads a trained conversion model and predicts conversion probability."""

    def __init__(self, registry: ConversionModelRegistry | None = None) -> None:
        self._registry = registry or ConversionModelRegistry()
        self._artifact: dict[str, Any] | None = None

    def load(self) -> None:
        self._artifact = self._registry.load_model()

    def predict(self, features: dict[str, Any]) -> dict[str, Any]:
        if self._artifact is None:
            self.load()

        assert self._artifact is not None
        pipeline = self._artifact["pipeline"]
        metadata = self._artifact.get("metadata", {})

        row = {col: features.get(col) for col in FEATURE_COLUMNS}
        df = pd.DataFrame([row])
        raw = float(pipeline.predict(df)[0])
        probability = round(float(np.clip(raw, 0.0, 100.0)), 2)

        return {
            "conversion_probability": probability,
            "model_used": metadata.get("best_model", "unknown"),
        }
