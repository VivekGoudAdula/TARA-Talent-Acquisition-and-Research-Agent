"""Orchestrates Excel import into external_leads."""

from pathlib import Path

from app.config import get_settings
from app.external.excel_importer import ExcelImporter
from app.repositories.external_lead_repository import ExternalLeadRepository
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class ExternalImportService:
    """Imports external CRM leads from Excel into MongoDB."""

    def __init__(
        self,
        lead_repository: ExternalLeadRepository,
        importer: ExcelImporter | None = None,
    ) -> None:
        self._lead_repo = lead_repository
        self._importer = importer or ExcelImporter()

    def import_from_excel(self, file_path: Path | None = None) -> dict[str, int | str]:
        settings = get_settings()
        path = file_path or settings.external_leads_excel_path

        rows = self._importer.read_and_transform(path)
        imported, updated, skipped = self._lead_repo.bulk_upsert(rows)

        logger.info(
            "External import complete: file=%s imported=%d updated=%d skipped=%d",
            path,
            imported,
            updated,
            skipped,
        )

        return {
            "file_path": str(path),
            "leads_imported": imported,
            "leads_updated": updated,
            "leads_skipped": skipped,
        }
