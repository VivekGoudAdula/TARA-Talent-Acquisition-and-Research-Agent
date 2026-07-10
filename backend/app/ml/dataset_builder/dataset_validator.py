"""Validation and cleaning for ML training datasets."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd

from app.ml.dataset_builder.dataset_generator import DatasetRow, PROFILE_EXTERNAL, PROFILE_INTERNAL
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

VALID_PROFILE_TYPES = {PROFILE_INTERNAL, PROFILE_EXTERNAL}
VALID_TARGETS = {"Very High", "High", "Medium", "Low"}

NUMERIC_COLUMNS = [
    "age",
    "income",
    "credit_score",
    "financial_health_score",
    "repayment_behaviour_score",
    "digital_engagement_score",
    "financial_capacity_score",
    "lead_score",
    "lead_quality_score",
    "lead_authenticity_score",
    "income_confidence_score",
    "relationship_score",
    "savings_ratio",
    "emi_burden",
    "cash_flow_score",
    "digital_adoption_score",
    "customer_value_score",
]

CATEGORICAL_COLUMNS = [
    "profile_type",
    "occupation",
    "employment_type",
    "city",
    "target_repayment_capacity",
]


@dataclass(frozen=True)
class ValidationReport:
    """Summary of dataset validation and cleaning."""

    records_in: int
    records_out: int
    duplicates_removed: int
    invalid_profile_types: int
    invalid_targets_corrected: int
    numeric_columns: int
    categorical_columns: int


class DatasetValidator:
    """Validates, deduplicates, and normalizes training records for ML readiness."""

    def validate_and_clean(self, rows: list[DatasetRow]) -> tuple[list[DatasetRow], ValidationReport]:
        if not rows:
            return [], ValidationReport(
                records_in=0,
                records_out=0,
                duplicates_removed=0,
                invalid_profile_types=0,
                invalid_targets_corrected=0,
                numeric_columns=len(NUMERIC_COLUMNS),
                categorical_columns=len(CATEGORICAL_COLUMNS),
            )

        df = self._rows_to_dataframe(rows)
        records_in = len(df)

        duplicates_removed = self._remove_duplicates(df)
        invalid_profile_types = self._fix_profile_types(df)
        invalid_targets_corrected = self._fix_targets(df)
        self._normalize_numeric_columns(df)
        self._normalize_categorical_columns(df)
        self._clip_score_columns(df)

        cleaned = self._dataframe_to_rows(df)
        report = ValidationReport(
            records_in=records_in,
            records_out=len(cleaned),
            duplicates_removed=duplicates_removed,
            invalid_profile_types=invalid_profile_types,
            invalid_targets_corrected=invalid_targets_corrected,
            numeric_columns=len(NUMERIC_COLUMNS),
            categorical_columns=len(CATEGORICAL_COLUMNS),
        )
        logger.info(
            "Dataset validation complete in=%d out=%d duplicates_removed=%d",
            report.records_in,
            report.records_out,
            report.duplicates_removed,
        )
        return cleaned, report

    def rows_to_dataframe(self, rows: list[DatasetRow]) -> pd.DataFrame:
        return self._rows_to_dataframe(rows)

    def compute_missing_counts(self, df: pd.DataFrame) -> dict[str, int]:
        missing: dict[str, int] = {}
        for col in df.columns:
            missing[col] = int(df[col].isna().sum())
        return missing

    def compute_target_distribution(self, df: pd.DataFrame) -> dict[str, int]:
        if "target_repayment_capacity" not in df.columns or df.empty:
            return {}
        counts = df["target_repayment_capacity"].value_counts()
        return {str(k): int(v) for k, v in counts.items()}

    def _rows_to_dataframe(self, rows: list[DatasetRow]) -> pd.DataFrame:
        records: list[dict[str, Any]] = []
        for row in rows:
            records.append(
                {
                    "record_id": str(row.record_id),
                    "profile_type": row.profile_type,
                    "profile_id": str(row.profile_id),
                    "age": row.age,
                    "income": self._to_float(row.income),
                    "credit_score": row.credit_score,
                    "financial_health_score": self._to_float(row.financial_health_score),
                    "repayment_behaviour_score": self._to_float(row.repayment_behaviour_score),
                    "digital_engagement_score": self._to_float(row.digital_engagement_score),
                    "financial_capacity_score": self._to_float(row.financial_capacity_score),
                    "lead_score": self._to_float(row.lead_score),
                    "lead_quality_score": self._to_float(row.lead_quality_score),
                    "lead_authenticity_score": self._to_float(row.lead_authenticity_score),
                    "income_confidence_score": self._to_float(row.income_confidence_score),
                    "relationship_score": self._to_float(row.relationship_score),
                    "savings_ratio": self._to_float(row.savings_ratio),
                    "emi_burden": self._to_float(row.emi_burden),
                    "cash_flow_score": self._to_float(row.cash_flow_score),
                    "digital_adoption_score": self._to_float(row.digital_adoption_score),
                    "customer_value_score": self._to_float(row.customer_value_score),
                    "occupation": row.occupation,
                    "employment_type": row.employment_type,
                    "city": row.city,
                    "target_repayment_capacity": row.target_repayment_capacity,
                    "created_at": row.created_at,
                }
            )
        return pd.DataFrame(records)

    def _dataframe_to_rows(self, df: pd.DataFrame) -> list[DatasetRow]:
        from uuid import UUID

        rows: list[DatasetRow] = []
        for record in df.to_dict(orient="records"):
            rows.append(
                DatasetRow(
                    record_id=UUID(str(record["record_id"])),
                    profile_type=str(record["profile_type"]),
                    profile_id=UUID(str(record["profile_id"])),
                    age=self._to_int(record.get("age")),
                    income=self._to_decimal(record.get("income")),
                    credit_score=self._to_int(record.get("credit_score")),
                    financial_health_score=self._to_decimal(record.get("financial_health_score")),
                    repayment_behaviour_score=self._to_decimal(
                        record.get("repayment_behaviour_score")
                    ),
                    digital_engagement_score=self._to_decimal(record.get("digital_engagement_score")),
                    financial_capacity_score=self._to_decimal(record.get("financial_capacity_score")),
                    lead_score=self._to_decimal(record.get("lead_score")),
                    lead_quality_score=self._to_decimal(record.get("lead_quality_score")),
                    lead_authenticity_score=self._to_decimal(record.get("lead_authenticity_score")),
                    income_confidence_score=self._to_decimal(record.get("income_confidence_score")),
                    relationship_score=self._to_decimal(record.get("relationship_score")),
                    savings_ratio=self._to_decimal(record.get("savings_ratio")),
                    emi_burden=self._to_decimal(record.get("emi_burden")),
                    cash_flow_score=self._to_decimal(record.get("cash_flow_score")),
                    digital_adoption_score=self._to_decimal(record.get("digital_adoption_score")),
                    customer_value_score=self._to_decimal(record.get("customer_value_score")),
                    occupation=self._to_str(record.get("occupation")),
                    employment_type=self._to_str(record.get("employment_type")),
                    city=self._to_str(record.get("city")),
                    target_repayment_capacity=str(record["target_repayment_capacity"]),
                    created_at=record["created_at"],
                )
            )
        return rows

    def _remove_duplicates(self, df: pd.DataFrame) -> int:
        before = len(df)
        df.drop_duplicates(subset=["profile_type", "profile_id"], keep="last", inplace=True)
        df.reset_index(drop=True, inplace=True)
        return before - len(df)

    def _fix_profile_types(self, df: pd.DataFrame) -> int:
        invalid_mask = ~df["profile_type"].isin(VALID_PROFILE_TYPES)
        count = int(invalid_mask.sum())
        if count:
            df.loc[invalid_mask, "profile_type"] = PROFILE_INTERNAL
        return count

    def _fix_targets(self, df: pd.DataFrame) -> int:
        invalid_mask = ~df["target_repayment_capacity"].isin(VALID_TARGETS)
        count = int(invalid_mask.sum())
        if count:
            df.loc[invalid_mask, "target_repayment_capacity"] = "Low"
        return count

    def _normalize_numeric_columns(self, df: pd.DataFrame) -> None:
        for col in NUMERIC_COLUMNS:
            if col not in df.columns:
                continue
            df[col] = pd.to_numeric(df[col], errors="coerce")

    def _normalize_categorical_columns(self, df: pd.DataFrame) -> None:
        for col in CATEGORICAL_COLUMNS:
            if col not in df.columns:
                continue
            df[col] = df[col].apply(
                lambda v: str(v).strip() if pd.notna(v) and str(v).strip() else np.nan
            )

    def _clip_score_columns(self, df: pd.DataFrame) -> None:
        score_cols = [
            c
            for c in NUMERIC_COLUMNS
            if c not in ("age", "income", "credit_score", "savings_ratio", "emi_burden")
        ]
        for col in score_cols:
            if col in df.columns:
                df[col] = df[col].clip(lower=0, upper=100)

    @staticmethod
    def _to_float(value: Decimal | float | int | None) -> float | None:
        if value is None:
            return None
        return float(value)

    @staticmethod
    def _to_decimal(value: Any) -> Decimal | None:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return None
        return Decimal(str(value))

    @staticmethod
    def _to_int(value: Any) -> int | None:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return None
        return int(value)

    @staticmethod
    def _to_str(value: Any) -> str | None:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return None
        text = str(value).strip()
        return text or None
