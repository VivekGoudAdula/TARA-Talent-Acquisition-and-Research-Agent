"""Database access — MongoDB (primary)."""

from app.db.mongo import MongoDatabase, ensure_indexes, get_db, get_database, new_session

__all__ = ["MongoDatabase", "ensure_indexes", "get_db", "get_database", "new_session"]
