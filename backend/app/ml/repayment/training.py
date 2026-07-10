"""Training pipeline for Repayment Capacity Prediction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectFromModel
from sklearn.impute import SimpleImputer
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, OneHotEncoder
from xgboost import XGBClassifier

from app.ml.dataset_builder.dataset_validator import CATEGORICAL_COLUMNS, NUMERIC_COLUMNS
from app.ml.repayment.evaluation import TARGET_ORDER, evaluate_multiclass, extract_feature_importance
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

TARGET_COL = "target_repayment_capacity"
EXCLUDE_COLS = {"record_id", "profile_id", "created_at", TARGET_COL}
FEATURE_NUMERIC = [c for c in NUMERIC_COLUMNS if c not in EXCLUDE_COLS]
FEATURE_CATEGORICAL = [
    c for c in ("profile_type", "occupation", "employment_type", "city") if c in CATEGORICAL_COLUMNS
]
FEATURE_COLUMNS = FEATURE_NUMERIC + FEATURE_CATEGORICAL

CV_FOLDS = 5
TEST_SIZE = 0.2
RANDOM_STATE = 42


@dataclass(frozen=True)
class TrainingResult:
    """Output of repayment capacity model training."""

    best_model_name: str
    pipeline: Pipeline
    label_encoder: LabelEncoder
    cv_scores: dict[str, float]
    test_metrics: dict[str, Any]
    feature_importance: dict[str, float]
    train_size: int
    test_size: int
    records_used: int
    feature_columns: list[str]


class RepaymentTrainer:
    """Trains and compares Random Forest, XGBoost, and LightGBM classifiers."""

    def __init__(self, random_state: int = RANDOM_STATE) -> None:
        self._random_state = random_state

    def train(self, df: pd.DataFrame) -> TrainingResult:
        df = self._prepare_dataframe(df)
        if df.empty:
            raise ValueError("Training dataset is empty")

        X = df[FEATURE_COLUMNS]
        y = df[TARGET_COL]

        missing_targets = y.isna() | ~y.isin(TARGET_ORDER)
        if missing_targets.any():
            X = X[~missing_targets]
            y = y[~missing_targets]

        if len(y) < CV_FOLDS * 2:
            raise ValueError(
                f"Insufficient records for training (need at least {CV_FOLDS * 2}, got {len(y)})"
            )

        stratify_y = y if y.value_counts().min() >= 2 else None
        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=TEST_SIZE,
            random_state=self._random_state,
            stratify=stratify_y,
        )

        label_encoder = LabelEncoder()
        label_encoder.fit(y_train)
        y_train_enc = label_encoder.transform(y_train)
        
        unseen_mask = ~y_test.isin(label_encoder.classes_)
        if unseen_mask.any():
            X_test = X_test[~unseen_mask]
            y_test = y_test[~unseen_mask]
        y_test_enc = label_encoder.transform(y_test)

        candidates = self._build_candidates(len(label_encoder.classes_))
        
        train_class_counts = y_train.value_counts()
        if len(train_class_counts) < 2 or train_class_counts.min() < CV_FOLDS:
            from sklearn.model_selection import KFold
            cv = KFold(n_splits=CV_FOLDS, shuffle=True, random_state=self._random_state)
        else:
            cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=self._random_state)

        cv_scores: dict[str, float] = {}
        fitted_pipelines: dict[str, Pipeline] = {}

        for name, estimator in candidates.items():
            pipeline = self._build_pipeline(estimator)
            scores = cross_val_score(
                pipeline,
                X_train,
                y_train_enc,
                cv=cv,
                scoring="f1_macro",
                n_jobs=-1,
            )
            cv_scores[name] = float(np.mean(scores))
            pipeline.fit(X_train, y_train_enc)
            fitted_pipelines[name] = pipeline
            logger.info("CV f1_macro %s=%.4f (+/- %.4f)", name, cv_scores[name], scores.std())

        best_model_name = max(cv_scores, key=cv_scores.get)
        best_pipeline = fitted_pipelines[best_model_name]

        y_pred_enc = best_pipeline.predict(X_test)
        y_proba = best_pipeline.predict_proba(X_test)
        y_pred = label_encoder.inverse_transform(y_pred_enc)
        y_test_labels = label_encoder.inverse_transform(y_test_enc)
        test_metrics = evaluate_multiclass(y_test_labels.tolist(), y_pred.tolist(), y_proba)
        test_metrics["best_model"] = best_model_name
        test_metrics["cv_f1_macro"] = cv_scores

        feature_names = self._get_feature_names(best_pipeline)
        feature_importance = extract_feature_importance(best_pipeline, feature_names)

        return TrainingResult(
            best_model_name=best_model_name,
            pipeline=best_pipeline,
            label_encoder=label_encoder,
            cv_scores=cv_scores,
            test_metrics=test_metrics,
            feature_importance=feature_importance,
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
        return prepared

    def _build_preprocessor(self) -> ColumnTransformer:
        numeric_transformer = Pipeline(
            steps=[("imputer", SimpleImputer(strategy="median"))]
        )
        categorical_transformer = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="most_frequent")),
                (
                    "encoder",
                    OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                ),
            ]
        )
        return ColumnTransformer(
            transformers=[
                ("num", numeric_transformer, FEATURE_NUMERIC),
                ("cat", categorical_transformer, FEATURE_CATEGORICAL),
            ]
        )

    def _build_pipeline(self, classifier: Any) -> Pipeline:
        selector = SelectFromModel(
            RandomForestClassifier(
                n_estimators=100,
                random_state=self._random_state,
                class_weight="balanced",
                n_jobs=-1,
            ),
            threshold="median",
        )
        return Pipeline(
            steps=[
                ("preprocess", self._build_preprocessor()),
                ("selector", selector),
                ("classifier", classifier),
            ]
        )

    def _build_candidates(self, num_classes: int) -> dict[str, Any]:
        if num_classes > 2:
            xgb = XGBClassifier(
                objective="multi:softprob",
                num_class=num_classes,
                eval_metric="mlogloss",
                random_state=self._random_state,
                n_jobs=-1,
            )
            lgb = LGBMClassifier(
                objective="multiclass",
                num_class=num_classes,
                class_weight="balanced",
                random_state=self._random_state,
                verbose=-1,
                n_jobs=-1,
            )
        else:
            xgb = XGBClassifier(
                objective="binary:logistic",
                eval_metric="logloss",
                random_state=self._random_state,
                n_jobs=-1,
            )
            lgb = LGBMClassifier(
                objective="binary",
                class_weight="balanced",
                random_state=self._random_state,
                verbose=-1,
                n_jobs=-1,
            )
        return {
            "random_forest": RandomForestClassifier(
                n_estimators=200,
                class_weight="balanced",
                random_state=self._random_state,
                n_jobs=-1,
            ),
            "xgboost": xgb,
            "lightgbm": lgb,
        }

    def _get_feature_names(self, pipeline: Pipeline) -> list[str]:
        preprocessor = pipeline.named_steps["preprocess"]
        try:
            return list(preprocessor.get_feature_names_out())
        except Exception:
            return FEATURE_COLUMNS
