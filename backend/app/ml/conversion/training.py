"""Training pipeline and artifact registry for Lead Conversion Prediction."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_selection import SelectFromModel
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor

from app.utils.logging_config import get_logger

logger = get_logger(__name__)

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_PATH = MODELS_DIR / "best_conversion_model.pkl"
METRICS_PATH = MODELS_DIR / "conversion_metrics.json"
FEATURE_IMPORTANCE_PATH = MODELS_DIR / "conversion_feature_importance.json"

TARGET_COL = "conversion_probability"
FEATURE_NUMERIC = [
    "estimated_income",
    "credit_score",
    "lead_quality_score",
    "behaviour_score",
    "digital_engagement_score",
    "consent",
    "previous_campaign_response",
    "communication_readiness",
]
FEATURE_CATEGORICAL = [
    "lead_source",
    "campaign",
    "referral_source",
    "occupation",
    "employer",
]
FEATURE_COLUMNS = FEATURE_NUMERIC + FEATURE_CATEGORICAL

CV_FOLDS = 5
TEST_SIZE = 0.2
RANDOM_STATE = 42


class ConversionModelRegistry:
    """Loads and saves lead conversion model artifacts."""

    def __init__(
        self,
        models_dir: Path | None = None,
        model_path: Path | None = None,
        metrics_path: Path | None = None,
        feature_importance_path: Path | None = None,
    ) -> None:
        self._models_dir = models_dir or MODELS_DIR
        self._model_path = model_path or MODEL_PATH
        self._metrics_path = metrics_path or METRICS_PATH
        self._feature_importance_path = feature_importance_path or FEATURE_IMPORTANCE_PATH

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

    def save_model(self, pipeline: Any, metadata: dict[str, Any]) -> str:
        self.ensure_dir()
        artifact = {
            "pipeline": pipeline,
            "metadata": metadata,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        joblib.dump(artifact, self._model_path)
        logger.info("Saved conversion model to %s", self._model_path)
        return str(self._model_path)

    def load_model(self) -> dict[str, Any]:
        if not self.model_exists():
            raise FileNotFoundError(f"Conversion model not found at {self._model_path}")
        return joblib.load(self._model_path)

    def save_metrics(self, metrics: dict[str, Any]) -> str:
        self.ensure_dir()
        with self._metrics_path.open("w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)
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
        return str(self._feature_importance_path)

    def load_feature_importance(self) -> dict[str, float] | None:
        if not self._feature_importance_path.exists():
            return None
        with self._feature_importance_path.open(encoding="utf-8") as f:
            return json.load(f)


@dataclass(frozen=True)
class TrainingResult:
    best_model_name: str
    pipeline: Pipeline
    cv_scores: dict[str, float]
    test_metrics: dict[str, Any]
    feature_importance: dict[str, float]
    train_size: int
    test_size: int
    records_used: int
    feature_columns: list[str]


def categorize_lead_source(referral_source: str | None) -> str:
    if not referral_source or not str(referral_source).strip():
        return "Unknown"
    source = str(referral_source).lower()
    if any(k in source for k in ("referral", "branch", "employee", "partner")):
        return "Referral"
    if any(k in source for k in ("website", "digital", "online", "app", "social")):
        return "Digital"
    if source in ("direct", "walk-in", "walk in"):
        return "Direct"
    if any(k in source for k in ("cold", "purchased", "tele")):
        return "Cold Outreach"
    return "Other"


def label_conversion_probability(row: dict[str, Any]) -> float:
    """
    Deterministic conversion labels (temporary until real outreach outcomes).

    Weighted combination of lead quality signals, consent, and engagement.
    """
    score = 0.0

    lq = row.get("lead_quality_score")
    if lq is not None:
        score += float(lq) * 0.28

    behaviour = row.get("behaviour_score")
    if behaviour is not None:
        score += float(behaviour) * 0.18

    digital = row.get("digital_engagement_score")
    if digital is not None:
        score += float(digital) * 0.12

    comm = row.get("communication_readiness")
    if comm is not None:
        score += float(comm) * 0.15

    prev = row.get("previous_campaign_response")
    if prev is not None:
        score += float(prev) * 0.12

    credit = row.get("credit_score")
    if credit is not None:
        score += min(15.0, max(0.0, (int(credit) - 550) / 10.0))

    income = row.get("estimated_income")
    if income is not None and float(income) > 0:
        score += min(10.0, float(income) / 500000.0 * 10.0)

    if row.get("consent"):
        score += 8.0
    else:
        score *= 0.55

    lead_source = row.get("lead_source", "Unknown")
    if lead_source == "Referral":
        score += 6.0
    elif lead_source == "Digital":
        score += 4.0
    elif lead_source == "Cold Outreach":
        score -= 5.0

    return round(min(100.0, max(0.0, score)), 2)


def evaluate_regression(
    y_true: np.ndarray | list[float],
    y_pred: np.ndarray | list[float],
) -> dict[str, float]:
    y_true_arr = np.array(y_true, dtype=float)
    y_pred_arr = np.clip(np.array(y_pred, dtype=float), 0.0, 100.0)
    return {
        "mae": float(mean_absolute_error(y_true_arr, y_pred_arr)),
        "rmse": float(np.sqrt(mean_squared_error(y_true_arr, y_pred_arr))),
        "r2": float(r2_score(y_true_arr, y_pred_arr)),
    }


def extract_feature_importance(pipeline: Pipeline, feature_names: list[str]) -> dict[str, float]:
    regressor = pipeline.named_steps.get("regressor")
    selector = pipeline.named_steps.get("selector")
    if regressor is None or not hasattr(regressor, "feature_importances_"):
        return {}

    importances = regressor.feature_importances_
    if selector is not None and hasattr(selector, "get_support"):
        support = selector.get_support()
        selected_names = [n for n, keep in zip(feature_names, support) if keep]
    else:
        selected_names = feature_names

    if len(selected_names) != len(importances):
        selected_names = feature_names[: len(importances)]

    pairs = sorted(zip(selected_names, importances), key=lambda x: x[1], reverse=True)
    return {name: float(score) for name, score in pairs}


class ConversionTrainer:
    """Trains and compares Random Forest, XGBoost, and LightGBM regressors."""

    def __init__(self, random_state: int = RANDOM_STATE) -> None:
        self._random_state = random_state

    def train(self, df: pd.DataFrame) -> TrainingResult:
        df = self._prepare_dataframe(df)
        if df.empty:
            raise ValueError("Conversion training dataset is empty")

        X = df[FEATURE_COLUMNS]
        y = df[TARGET_COL]

        valid = y.notna()
        X = X[valid]
        y = y[valid]

        if len(y) < CV_FOLDS * 2:
            raise ValueError(
                f"Insufficient lead records for training (need {CV_FOLDS * 2}, got {len(y)})"
            )

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=TEST_SIZE, random_state=self._random_state
        )

        candidates = self._build_candidates()
        cv = KFold(n_splits=CV_FOLDS, shuffle=True, random_state=self._random_state)

        cv_scores: dict[str, float] = {}
        fitted: dict[str, Pipeline] = {}

        for name, estimator in candidates.items():
            pipeline = self._build_pipeline(estimator)
            scores = cross_val_score(
                pipeline,
                X_train,
                y_train,
                cv=cv,
                scoring="neg_mean_absolute_error",
                n_jobs=-1,
            )
            cv_scores[name] = float(-np.mean(scores))
            pipeline.fit(X_train, y_train)
            fitted[name] = pipeline
            logger.info("CV MAE %s=%.4f", name, cv_scores[name])

        best_model_name = min(cv_scores, key=cv_scores.get)
        best_pipeline = fitted[best_model_name]

        y_pred = np.clip(best_pipeline.predict(X_test), 0.0, 100.0)
        test_metrics = evaluate_regression(y_test, y_pred)
        test_metrics["best_model"] = best_model_name
        test_metrics["cv_mae"] = cv_scores

        feature_names = self._get_feature_names(best_pipeline)
        importance = extract_feature_importance(best_pipeline, feature_names)

        return TrainingResult(
            best_model_name=best_model_name,
            pipeline=best_pipeline,
            cv_scores=cv_scores,
            test_metrics=test_metrics,
            feature_importance=importance,
            train_size=len(X_train),
            test_size=len(X_test),
            records_used=len(df),
            feature_columns=FEATURE_COLUMNS,
        )

    def _prepare_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        prepared = df.copy()
        for col in FEATURE_NUMERIC:
            if col in prepared.columns:
                prepared[col] = pd.to_numeric(prepared[col], errors="coerce")
        for col in FEATURE_CATEGORICAL:
            if col in prepared.columns:
                prepared[col] = prepared[col].apply(
                    lambda v: str(v).strip() if pd.notna(v) and str(v).strip() else np.nan
                )
        if TARGET_COL in prepared.columns:
            prepared[TARGET_COL] = pd.to_numeric(prepared[TARGET_COL], errors="coerce")
        return prepared

    def _build_preprocessor(self) -> ColumnTransformer:
        numeric_transformer = Pipeline(steps=[("imputer", SimpleImputer(strategy="median"))])
        categorical_transformer = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
            ]
        )
        return ColumnTransformer(
            transformers=[
                ("num", numeric_transformer, FEATURE_NUMERIC),
                ("cat", categorical_transformer, FEATURE_CATEGORICAL),
            ]
        )

    def _build_pipeline(self, regressor: Any) -> Pipeline:
        selector = SelectFromModel(
            RandomForestRegressor(n_estimators=100, random_state=self._random_state, n_jobs=-1),
            threshold="median",
        )
        return Pipeline(
            steps=[
                ("preprocess", self._build_preprocessor()),
                ("selector", selector),
                ("regressor", regressor),
            ]
        )

    def _build_candidates(self) -> dict[str, Any]:
        return {
            "random_forest": RandomForestRegressor(
                n_estimators=200,
                random_state=self._random_state,
                n_jobs=-1,
            ),
            "xgboost": XGBRegressor(
                objective="reg:squarederror",
                random_state=self._random_state,
                n_jobs=-1,
            ),
            "lightgbm": LGBMRegressor(
                random_state=self._random_state,
                verbose=-1,
                n_jobs=-1,
            ),
        }

    def _get_feature_names(self, pipeline: Pipeline) -> list[str]:
        preprocessor = pipeline.named_steps["preprocess"]
        try:
            return list(preprocessor.get_feature_names_out())
        except Exception:
            return FEATURE_COLUMNS
