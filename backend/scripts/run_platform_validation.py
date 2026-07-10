"""CLI entry point for enterprise platform validation."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db_env import load_db_env

load_db_env()

from app.platform_validation.validation_service import PlatformValidationService
from app.utils.database import new_session


def main() -> None:
    db = new_session()
    try:
        service = PlatformValidationService(db, report_dir=PROJECT_ROOT)
        report = service.run_full_validation(write_reports=True)
        print(f"Overall Health: {report.overall_health}")
        print(f"Reports: {report.report_paths}")
        for category in report.categories:
            print(f"  [{category.status}] {category.category}: pass={category.passed} fail={category.failed}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
