"""Feature store document entity."""

from app.db.entity import DocumentEntity


class FeatureStoreEntry(DocumentEntity):
    """One feature row per customer per feature name."""
