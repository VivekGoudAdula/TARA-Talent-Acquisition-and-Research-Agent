"""Model artifact persistence for Repayment Capacity Prediction."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib

from app.utils.logging_config import get_logger

logger = get_logger(__name__)

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_PATH = MODELS_DIR / "best_repayment_model.pkl"
METRICS_PATH = MODELS_DIR / "metrics.json"
FEATURE_IMPORTANCE_PATH = MODELS_DIR / "feature_importance.json"


class RepaymentModelRegistry:
    """Loads and saves repayment capacity model artifacts."""

    def __init__(
        self,
        models_dir: Path | None = None,
        model_path: Path | None = None,
        metrics_path: Path | None = None,
        feature_importance_path: Path | None = None,
    ) -> None:
        self._models_dir = models_dir or MODELS_DIR
        self._model_path = model_path or (self._models_dir / "best_repayment_model.pkl")
        self._metrics_path = metrics_path or (self._models_dir / "metrics.json")
        self._feature_importance_path = (
            feature_importance_path or (self._models_dir / "feature_importance.json")
        )

    @property
    def model_path(self) -> Path:
        return self._model_path

    @property
    def metrics_path(self) -> Path:
        return self._metrics_path

    @property
    def feature_importance_path(self) -> Path:
        return self._feature_importance_path

    def ensure_dir(self) -> None:
        self._models_dir.mkdir(parents=True, exist_ok=True)

    def model_exists(self) -> bool:
        return self._model_path.exists()

    def save_model(self, pipeline: Any, metadata: dict[str, Any], label_encoder: Any = None) -> str:
        self.ensure_dir()
        artifact = {
            "pipeline": pipeline,
            "label_encoder": label_encoder,
            "metadata": metadata,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        joblib.dump(artifact, self._model_path)
        logger.info("Saved repayment model to %s", self._model_path)
        return str(self._model_path)

    def load_model(self) -> dict[str, Any]:
        if not self.model_exists():
            raise FileNotFoundError(f"Repayment model not found at {self._model_path}")
        artifact = joblib.load(self._model_path)
        logger.info("Loaded repayment model from %s", self._model_path)
        return artifact

    def save_metrics(self, metrics: dict[str, Any]) -> str:
        self.ensure_dir()
        with self._metrics_path.open("w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)
        logger.info("Saved repayment metrics to %s", self._metrics_path)
        return str(self._metrics_path)

    def load_metrics(self) -> dict[str, Any] | None:
        if not self._metrics_path.exists():
            return None
        with self._metrics_path.open(encoding="utf-8") as f:
            return json.load(f)

    def save_feature_importance(self, importance: dict[str, float]) -> str:
        self.ensure_dir()
        with self._feature_importance_path.open("w", encoding="utf-8") as f:
            json.dump(importance, f, indent=2)
        logger.info("Saved feature importance to %s", self._feature_importance_path)
        return str(self._feature_importance_path)

    def load_feature_importance(self) -> dict[str, float] | None:
        if not self._feature_importance_path.exists():
            return None
        with self._feature_importance_path.open(encoding="utf-8") as f:
            return json.load(f)
