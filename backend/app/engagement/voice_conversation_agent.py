"""LLM-driven multi-turn voice agent for Twilio callback conversations."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from app.config import Settings, get_settings
from app.db.mongo import MongoDatabase
from app.engagement.banking_copy import humanize_reasons
from app.engagement.voice_locale import detect_language_switch, normalize_language, resolve_voice_locale
from app.onboarding.response_parser import classify_response
from app.schemas.voice_session import VoiceAgentContext
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

_MAX_TURNS = 8
_ACTION = Literal["continue", "transfer_rm", "end_call"]


@dataclass
class AgentTurn:
    reply: str
    language: str
    action: _ACTION
    outcome: str | None = None
    polly_voice: str = "Polly.Aditi"
    polly_language: str = "en-IN"
    speech_hints: list[str] | None = None


class VoiceConversationAgent:
    """Runs humanized callback conversations using full VoiceAgentContext."""

    def __init__(self, db: MongoDatabase, settings: Settings | None = None) -> None:
        self._db = db
        self._settings = settings or get_settings()
        self._openai_client = None
        self._azure_client = None

    @property
    def llm_configured(self) -> bool:
        if not self._settings.explainability_use_llm:
            return False
        return bool(self._settings.openai_api_key) or bool(
            self._settings.azure_openai_api_key and self._settings.azure_openai_endpoint
        )

    @staticmethod
    def build_opening_text(context: VoiceAgentContext, lang: str | None = None) -> str:
        """Exact callback opening: name, product, reason1, shall I explain."""
        language = normalize_language(lang or context.lang)
        name = context.name or "there"
        product = context.product or "our lending offer"
        reason1 = humanize_reasons(context.top3_reasons[:1]) if context.top3_reasons else "your banking profile"

        templates = {
            "hindi": (
                f"नमस्ते {name}, आपने {product} के लिए कॉलबैक का अनुरोध किया था। "
                f"आप {reason1} के कारण पात्र हैं। क्या मैं संक्षेप में समझाऊँ?"
            ),
            "tamil": (
                f"வணக்கம் {name}, {product} க்கான callback நீங்கள் கோரினீர்கள். "
                f"{reason1} காரணமாக நீங்கள் தகுதியானவர். சுருக்கமாக விளக்கவா?"
            ),
            "telugu": (
                f"నమస్కారం {name}, మీరు {product} కోసం callback అభ్యర్థించారు. "
                f"{reason1} కారణంగా మీరు అర్హులు. సంక్షిప్తంగా వివరించనా?"
            ),
            "english": (
                f"Hi {name}, you requested a callback for {product}. "
                f"You're eligible because {reason1}. Shall I explain?"
            ),
        }
        return templates.get(language, templates["english"])

    def generate_opening(self, session_id: str, context: VoiceAgentContext) -> AgentTurn:
        lang = normalize_language(context.lang)
        reply = self.build_opening_text(context, lang)
        turn = self._wrap_turn(reply, lang, action="continue")
        self._append_turn(session_id, role="agent", text=turn.reply, language=turn.language)
        return turn

    def handle_turn(
        self,
        *,
        session_id: str,
        context: VoiceAgentContext,
        user_input: str,
        call_sid: str | None = None,
    ) -> AgentTurn:
        state = self._load_state(session_id)
        active_lang = state.get("active_lang") or normalize_language(context.lang)
        history: list[dict[str, str]] = list(state.get("turns") or [])
        turn_count = int(state.get("turn_count") or 0)

        speech = (user_input or "").strip()
        switched = detect_language_switch(speech)
        if switched:
            active_lang = switched
            self._set_active_lang(session_id, active_lang)

        if speech:
            self._append_turn(session_id, role="customer", text=speech, language=active_lang)
            history.append({"role": "customer", "text": speech})
            turn_count += 1
            logger.info("Voice callback input session=%s speech=%r", session_id, speech[:120])

        if not speech:
            if history or turn_count > 0:
                reply = self._no_input_message(active_lang)
                turn = self._wrap_turn(reply, active_lang, action="continue")
                self._append_turn(session_id, role="agent", text=reply, language=active_lang)
                if turn_count >= _MAX_TURNS - 1:
                    turn.action = "end_call"
                    turn.outcome = "neutral"
                    self._finalize_session(session_id, outcome="neutral", call_sid=call_sid)
                return turn

        if turn_count >= _MAX_TURNS:
            reply = self._closing_message(active_lang, "neutral")
            turn = self._wrap_turn(reply, active_lang, action="end_call", outcome="neutral")
            self._append_turn(session_id, role="agent", text=reply, language=active_lang)
            self._finalize_session(session_id, outcome="neutral", call_sid=call_sid)
            return turn

        turn = self._generate_turn(
            context=context,
            user_input=speech,
            history=history,
            active_lang=active_lang,
        )
        self._append_turn(session_id, role="agent", text=turn.reply, language=turn.language)

        if turn.action in ("transfer_rm", "end_call"):
            self._finalize_session(session_id, outcome=turn.outcome or "neutral", call_sid=call_sid)

        return turn

    def get_transcript_preview(self, session_id: str, limit: int = 6) -> str:
        state = self._load_state(session_id)
        turns = state.get("turns") or []
        lines = []
        for item in turns[-limit:]:
            role = "Customer" if item.get("role") == "customer" else "Agent"
            lines.append(f"{role}: {item.get('text', '')}")
        return " | ".join(lines)

    def _generate_turn(
        self,
        *,
        context: VoiceAgentContext,
        user_input: str,
        history: list[dict[str, str]],
        active_lang: str,
    ) -> AgentTurn:
        if self.llm_configured:
            try:
                return self._llm_turn(context, user_input, history, active_lang)
            except Exception as exc:
                logger.warning("Voice LLM turn failed, using fallback: %s", exc)
        return self._fallback_turn(context, user_input, history, active_lang)

    def _llm_turn(
        self,
        context: VoiceAgentContext,
        user_input: str,
        history: list[dict[str, str]],
        active_lang: str,
    ) -> AgentTurn:
        context_blob = {
            "name": context.name,
            "lang": context.lang,
            "campaign": context.campaign,
            "intent": context.intent,
            "product": context.product,
            "reasons": context.top3_reasons,
            "confidence": context.confidence,
            "eligibility": context.eligibility,
            "customer_id": context.customer_id,
            "talking_points": context.talking_points,
        }
        history_text = "\n".join(
            f"{item['role'].upper()}: {item['text']}" for item in history[-8:]
        )
        system = (
            "You are IDBI Bank callback voice agent on a live phone call.\n"
            "Respond ONLY with JSON:\n"
            '{"reply":"one short sentence","language":"English|Hindi|etc",'
            '"action":"continue|transfer_rm|end_call","outcome":"interested|declined|neutral|null"}\n'
            "Rules: use context only; no repeated questions; max 1 short sentence; "
            "never ask name/phone/product/eligibility again; "
            "if customer says yes/explain give brief product info from context; "
            "transfer_rm only on clear interest/apply/transfer; "
            "end_call on decline; switch language if asked.\n"
            f"Active language: {active_lang}."
        )
        user_parts = [
            f"Context: {json.dumps(context_blob, ensure_ascii=False)}",
            f"History:\n{history_text}",
            f"Customer said: {user_input}",
        ]

        if self._settings.openai_api_key:
            client = self._get_openai_client()
            model = self._settings.openai_model
        else:
            client = self._get_azure_client()
            model = self._settings.azure_gpt_deployment

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": "\n\n".join(user_parts)},
            ],
            temperature=0.2,
            max_tokens=200,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        data = json.loads(raw)
        reply = str(data.get("reply") or "").strip()
        language = str(data.get("language") or active_lang).strip()
        action = str(data.get("action") or "continue").strip().lower()
        outcome = data.get("outcome")
        if action not in ("continue", "transfer_rm", "end_call"):
            action = "continue"
        if outcome is not None:
            outcome = str(outcome).strip().lower()
        if not reply:
            return self._fallback_turn(context, user_input, history, active_lang)
        return self._wrap_turn(reply, language, action=action, outcome=outcome)

    def _fallback_turn(
        self,
        context: VoiceAgentContext,
        user_input: str,
        history: list[dict[str, str]],
        active_lang: str,
    ) -> AgentTurn:
        lang = normalize_language(active_lang)
        name = context.name or "there"

        if self._wants_transfer(user_input):
            return self._wrap_turn(
                self._transfer_message(lang, name),
                lang,
                action="transfer_rm",
                outcome="interested",
            )

        classification = classify_response(raw_text=user_input)
        if classification == "declined":
            return self._wrap_turn(
                self._closing_message(lang, "declined"),
                lang,
                action="end_call",
                outcome="declined",
            )

        if classification == "interested" or self._wants_apply(user_input):
            if self._wants_apply(user_input) or self._already_explained(history) or not self._is_simple_ack(user_input):
                return self._wrap_turn(
                    self._transfer_message(lang, name),
                    lang,
                    action="transfer_rm",
                    outcome="interested",
                )

        if self._wants_explain(user_input) and not self._already_explained(history):
            return self._wrap_turn(self._brief_explain(context, lang), lang, action="continue")

        if self._is_product_question(user_input):
            return self._wrap_turn(self._brief_explain(context, lang), lang, action="continue")

        return self._wrap_turn(
            self._short_nudge(context, lang),
            lang,
            action="continue",
        )

    def _wrap_turn(
        self,
        reply: str,
        language: str,
        *,
        action: _ACTION,
        outcome: str | None = None,
    ) -> AgentTurn:
        locale = resolve_voice_locale(language)
        return AgentTurn(
            reply=reply,
            language=locale["language_key"],
            action=action,
            outcome=outcome,
            polly_voice=str(locale["polly_voice"]),
            polly_language=str(locale["polly_language"]),
            speech_hints=list(locale["hints"]),
        )

    def _brief_explain(self, context: VoiceAgentContext, lang: str) -> str:
        product = context.product or "this offer"
        points = (
            context.talking_points
            or f"{product} with competitive rates, flexible tenure, and {context.eligibility or 'good'} eligibility."
        )
        points = points.split(".")[0].strip() + "."
        if lang == "hindi":
            return f"{product}: {points} रुचि हो तो हाँ कहें या manager के लिए transfer कहें।"
        return f"{product}: {points} Say yes to proceed or transfer for a manager."

    def _short_nudge(self, context: VoiceAgentContext, lang: str) -> str:
        product = context.product or "the offer"
        if lang == "hindi":
            return f"मैं {product} के बारे में संक्षेप में बता सकती हूँ — हाँ, नहीं, या transfer कहें।"
        return f"I can help with {product} — say yes, no, or transfer."

    def _transfer_message(self, lang: str, name: str) -> str:
        if lang == "hindi":
            return f"धन्यवाद {name}, मैं अभी relationship manager से जोड़ रही हूँ।"
        return f"Thank you {name}, connecting you to a relationship manager now."

    def _closing_message(self, lang: str, outcome: str) -> str:
        if outcome == "declined":
            if lang == "hindi":
                return "ठीक है, धन्यवाद। विवरण WhatsApp पर भेज देंगे।"
            return "Thank you. We'll share details on WhatsApp."
        if lang == "hindi":
            return "धन्यवाद। IDBI Bank जल्द संपर्क करेगा।"
        return "Thank you. IDBI Bank will follow up shortly."

    def _no_input_message(self, lang: str) -> str:
        if normalize_language(lang) == "hindi":
            return "सुनाई नहीं दिया। कृपया हाँ, नहीं, या transfer कहें।"
        return "I didn't catch that. Please say yes, no, or transfer."

    @staticmethod
    def _is_simple_ack(text: str) -> bool:
        return text.strip().lower() in ("yes", "yeah", "yep", "ok", "okay", "sure", "haan", "ha", "1")

    @staticmethod
    def _wants_explain(text: str) -> bool:
        lowered = text.lower()
        return bool(
            re.search(r"\b(yes|yeah|yep|ok|okay|sure|explain|tell me|haan|ha|1)\b", lowered)
        )

    @staticmethod
    def _wants_apply(text: str) -> bool:
        lowered = text.lower()
        return any(
            k in lowered
            for k in ("interested", "apply", "proceed", "go ahead", "sign up", "लेना", "चाहिए")
        )

    @staticmethod
    def _wants_transfer(text: str) -> bool:
        lowered = text.lower()
        return any(k in lowered for k in ("transfer", "manager", "rm", "human", "agent", "advisor"))

    @staticmethod
    def _already_explained(history: list[dict[str, str]]) -> bool:
        agent_turns = [t["text"] for t in history if t.get("role") == "agent"]
        return len(agent_turns) > 1

    @staticmethod
    def _is_product_question(text: str) -> bool:
        lowered = text.lower()
        return bool(
            re.search(
                r"\b(rate|interest|emi|tenure|amount|fee|document|कितना|ब्याज|details|explain)\b",
                lowered,
            )
        )

    def _load_state(self, session_id: str) -> dict[str, Any]:
        doc = self._db.voice_callback_sessions.find_one({"session_id": session_id}) or {}
        return dict(doc.get("conversation") or {})

    def _append_turn(self, session_id: str, *, role: str, text: str, language: str) -> None:
        now = datetime.now(timezone.utc)
        self._db.voice_callback_sessions.update_one(
            {"session_id": session_id},
            {
                "$push": {
                    "conversation.turns": {
                        "role": role,
                        "text": text,
                        "language": normalize_language(language),
                        "at": now,
                    }
                },
                "$inc": {"conversation.turn_count": 1 if role == "customer" else 0},
                "$set": {
                    "conversation.active_lang": normalize_language(language),
                    "conversation.updated_at": now,
                },
            },
        )

    def _set_active_lang(self, session_id: str, language: str) -> None:
        self._db.voice_callback_sessions.update_one(
            {"session_id": session_id},
            {"$set": {"conversation.active_lang": normalize_language(language)}},
        )

    def _finalize_session(self, session_id: str, *, outcome: str, call_sid: str | None) -> None:
        self._db.voice_callback_sessions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "conversation.outcome": outcome,
                    "conversation.call_sid": call_sid,
                    "conversation.completed_at": datetime.now(timezone.utc),
                    "status": "completed",
                }
            },
        )

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
