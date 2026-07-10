"""Base document entity — attribute-style objects compatible with existing services."""

from __future__ import annotations

from typing import Any

from app.db.codec import decode_document, encode_document


class DocumentEntity:
    """Dict-backed entity with attribute access (replaces SQLAlchemy instances)."""

    def __init__(self, **kwargs: Any) -> None:
        self.__dict__.update(kwargs)

    @classmethod
    def from_doc(cls, doc: dict[str, Any] | None) -> DocumentEntity | None:
        if doc is None:
            return None
        decoded = decode_document(doc)
        return cls(**decoded) if decoded else None

    def to_doc(self) -> dict[str, Any]:
        return encode_document(dict(self.__dict__))

    def __repr__(self) -> str:
        name = self.__class__.__name__
        keys = ", ".join(f"{k}={v!r}" for k, v in list(self.__dict__.items())[:4])
        return f"{name}({keys}...)"
