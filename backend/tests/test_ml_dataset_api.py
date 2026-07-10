"""Integration tests for ML Dataset Builder API."""

import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.ml.dataset_builder.dataset_exporter import DATASETS_DIR
from db_env import load_db_env

load_db_env()


class MLDatasetAPITests(unittest.TestCase):
    def test_ml_dataset_build_preview_stats(self) -> None:
        with TestClient(app) as client:
            build = client.post("/api/ml/dataset/build")
            self.assertEqual(build.status_code, 200, build.text)
            body = build.json()
            self.assertIn("records_persisted", body)
            self.assertGreater(body["records_persisted"], 0)
            self.assertIn("csv_path", body)
            self.assertIn("parquet_path", body)
            self.assertIn("target_distribution", body)
            self.assertTrue(Path(body["csv_path"]).exists())
            self.assertTrue(Path(body["parquet_path"]).exists())

            preview = client.get("/api/ml/dataset?limit=10")
            self.assertEqual(preview.status_code, 200, preview.text)
            preview_body = preview.json()
            self.assertGreater(preview_body["total_records"], 0)
            self.assertLessEqual(len(preview_body["records"]), 10)
            record = preview_body["records"][0]
            self.assertIn("profile_type", record)
            self.assertIn("target_repayment_capacity", record)
            self.assertIn(record["target_repayment_capacity"], {"Very High", "High", "Medium", "Low"})

            stats = client.get("/api/ml/dataset/stats")
            self.assertEqual(stats.status_code, 200, stats.text)
            stats_body = stats.json()
            self.assertGreater(stats_body["total_records"], 0)
            self.assertGreater(stats_body["feature_count"], 0)
            self.assertIn("missing_values", stats_body)
            self.assertIn("target_distribution", stats_body)
            self.assertIn("export_paths", stats_body)
            self.assertEqual(
                stats_body["export_paths"]["csv"],
                str(DATASETS_DIR / "training_dataset.csv"),
            )


if __name__ == "__main__":
    unittest.main()
