"""Export ML training datasets to CSV and Parquet."""

from pathlib import Path

import pandas as pd

from app.utils.logging_config import get_logger

logger = get_logger(__name__)

DATASETS_DIR = Path(__file__).resolve().parent.parent / "datasets"
CSV_FILENAME = "training_dataset.csv"
PARQUET_FILENAME = "training_dataset.parquet"


class DatasetExporter:
    """Writes standardized datasets to enterprise export paths."""

    def __init__(self, output_dir: Path | None = None) -> None:
        self._output_dir = output_dir or DATASETS_DIR

    @property
    def csv_path(self) -> Path:
        return self._output_dir / CSV_FILENAME

    @property
    def parquet_path(self) -> Path:
        return self._output_dir / PARQUET_FILENAME

    def export(self, df: pd.DataFrame) -> dict[str, str]:
        self._output_dir.mkdir(parents=True, exist_ok=True)

        csv_path = self.csv_path
        parquet_path = self.parquet_path

        export_df = df.copy()
        if "created_at" in export_df.columns:
            export_df["created_at"] = pd.to_datetime(export_df["created_at"])

        export_df.to_csv(csv_path, index=False)
        export_df.to_parquet(parquet_path, index=False, engine="pyarrow")

        logger.info(
            "Exported training dataset csv=%s parquet=%s rows=%d",
            csv_path,
            parquet_path,
            len(export_df),
        )
        return {
            "csv_path": str(csv_path),
            "parquet_path": str(parquet_path),
            "record_count": str(len(export_df)),
        }
