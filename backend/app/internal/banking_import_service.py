"""Orchestrates internal banking Excel import into MongoDB."""

from pathlib import Path

from app.config import get_settings
from app.internal.banking_excel_importer import BankingExcelImporter, BankingImportBundle
from app.repositories.banking_import_repository import BankingImportRepository
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class BankingImportService:
    """Loads internal customer Excel workbooks into core banking collections."""

    def __init__(
        self,
        repository: BankingImportRepository,
        importer: BankingExcelImporter | None = None,
    ) -> None:
        self._repo = repository
        self._importer = importer or BankingExcelImporter()

    def import_from_excel(
        self,
        *,
        customer_master_path: Path | None = None,
        transaction_history_path: Path | None = None,
        loan_history_path: Path | None = None,
        digital_activity_path: Path | None = None,
        replace_existing: bool = True,
    ) -> dict[str, int | str]:
        settings = get_settings()
        paths = {
            "customer_master": customer_master_path or settings.customer_master_excel_path,
            "transaction_history": transaction_history_path or settings.transaction_history_excel_path,
            "loan_history": loan_history_path or settings.loan_history_excel_path,
            "digital_activity": digital_activity_path or settings.digital_activity_excel_path,
        }
        for label, path in paths.items():
            if not path.exists():
                raise FileNotFoundError(f"{label} Excel not found: {path}")

        bundle = self._importer.import_all(
            customer_master_path=paths["customer_master"],
            transaction_history_path=paths["transaction_history"],
            loan_history_path=paths["loan_history"],
            digital_activity_path=paths["digital_activity"],
        )
        counts = self._repo.load_bundle(bundle, replace_existing=replace_existing)
        logger.info("Internal banking Excel import complete: %s", counts)
        return {
            "message": "Internal banking data imported from Excel",
            **{k: v for k, v in counts.items()},
            **{f"{k}_path": str(v) for k, v in paths.items()},
        }
