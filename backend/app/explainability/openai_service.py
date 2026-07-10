"""OpenAI / Azure OpenAI service for explanation generation only."""

from __future__ import annotations

from typing import Any, Literal

from app.config import Settings, get_settings
from app.explainability.prompt_builder import PromptBuilder
from app.explainability.response_parser import ResponseParser
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

LLMProvider = Literal["openai", "azure"]


class OpenAIService:
    """
    Generates human-readable explanations from structured ML decision summaries.

    This service NEVER makes lending decisions — explanation only.
    Prefers standard OpenAI when OPENAI_API_KEY is set; otherwise Azure OpenAI.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        prompt_builder: PromptBuilder | None = None,
        response_parser: ResponseParser | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._prompt_builder = prompt_builder or PromptBuilder()
        self._response_parser = response_parser or ResponseParser()
        self._openai_client = None
        self._azure_client = None

    @property
    def provider(self) -> LLMProvider | None:
        if not self._settings.explainability_use_llm:
            return None
        if self._settings.openai_api_key:
            return "openai"
        if self._settings.azure_openai_api_key and self._settings.azure_openai_endpoint:
            return "azure"
        return None

    @property
    def is_configured(self) -> bool:
        return self.provider is not None

    def generate_explanation(self, decision_summary: dict[str, Any]) -> dict[str, Any]:
        if not self.is_configured:
            logger.info("OpenAI not configured — using deterministic fallback explanation")
            return self._prompt_builder.build_fallback(decision_summary)

        provider = self.provider
        try:
            messages = self._prompt_builder.build_messages(decision_summary)
            if provider == "openai":
                client = self._get_openai_client()
                model = self._settings.openai_model
            else:
                client = self._get_azure_client()
                model = self._settings.azure_gpt_deployment

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.2,
                max_tokens=1200,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content or ""
            logger.info("%s explanation generated successfully", provider)
            return self._response_parser.parse(
                raw,
                fallback_reason_codes=decision_summary.get("top_reason_codes", []),
            )
        except Exception as exc:
            logger.warning("%s explanation failed, using fallback: %s", provider, exc)
            return self._prompt_builder.build_fallback(decision_summary)

    def _get_openai_client(self):
        if self._openai_client is None:
            from openai import OpenAI

            self._openai_client = OpenAI(api_key=self._settings.openai_api_key)
        return self._openai_client

    def _get_azure_client(self):
        if self._azure_client is None:
            from openai import AzureOpenAI

            self._azure_client = AzureOpenAI(
                api_key=self._settings.azure_openai_api_key,
                api_version=self._settings.azure_api_version,
                azure_endpoint=self._settings.azure_openai_endpoint,
            )
        return self._azure_client
