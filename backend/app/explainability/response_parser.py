"""Parse and validate LLM explanation responses."""

from __future__ import annotations

import json
import re
from typing import Any

from app.utils.logging_config import get_logger

logger = get_logger(__name__)

REQUIRED_KEYS = (
    "summary",
    "repayment_explanation",
    "product_explanation",
    "conversion_explanation",
    "confidence_summary",
    "reason_codes",
)


class ResponseParser:
    """Parses Azure OpenAI JSON responses into structured explanations."""

    def parse(self, raw_content: str, fallback_reason_codes: list[str]) -> dict[str, Any]:
        data = self._extract_json(raw_content)
        if data is None:
            raise ValueError("LLM response did not contain valid JSON")

        for key in REQUIRED_KEYS:
            if key not in data:
                raise ValueError(f"LLM response missing required key: {key}")

        reason_codes = data.get("reason_codes", [])
        if not isinstance(reason_codes, list):
            reason_codes = fallback_reason_codes
        else:
            reason_codes = [str(c) for c in reason_codes]

        if not reason_codes:
            reason_codes = fallback_reason_codes

        return {
            "summary": str(data["summary"]).strip(),
            "repayment_explanation": str(data["repayment_explanation"]).strip(),
            "product_explanation": str(data["product_explanation"]).strip(),
            "conversion_explanation": str(data["conversion_explanation"]).strip(),
            "confidence_summary": str(data["confidence_summary"]).strip(),
            "reason_codes": reason_codes,
        }

    def _extract_json(self, content: str) -> dict[str, Any] | None:
        content = content.strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON from LLM response substring")
        return None
