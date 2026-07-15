"""Engagement layer API — multi-channel outreach."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response, StreamingResponse

from app.dependencies import get_engagement_service
from app.engagement.service import EngagementService
from app.engagement.voice_bridge import VoiceBridgeError
from app.schemas.conversation import ConversationThreadResponse, InboundMessageRequest
from app.schemas.engagement import (
    ChannelStatusResponse,
    CustomSendRequest,
    CustomSendResponse,
    EngagementExportResponse,
    EngagementLeadRecord,
    OutreachRequest,
    OutreachResponse,
    VoiceCallOutcomeRequest,
    VoiceCallOutcomeResponse,
    VoiceCampaignRequest,
    VoiceCampaignResponse,
)
from app.schemas.voice_session import VoiceAgentContext, VoiceCallbackStartRequest, VoiceCallbackStartResponse

router = APIRouter(prefix="/api/engagement", tags=["Engagement Layer"])


@router.get("/channels/status", response_model=ChannelStatusResponse)
def engagement_channel_status(
    service: EngagementService = Depends(get_engagement_service),
) -> ChannelStatusResponse:
    return service.channel_status()


@router.get(
    "/preview",
    response_model=list[EngagementLeadRecord],
    summary="Preview engagement-ready leads",
)
def preview_engagement_leads(
    limit: int = Query(default=10, ge=1, le=500),
    profile_types: str = Query(default="External", description="Comma-separated: External, Internal"),
    min_conversion_probability: float | None = Query(default=None, ge=0, le=100),
    service: EngagementService = Depends(get_engagement_service),
) -> list[EngagementLeadRecord]:
    types = [part.strip() for part in profile_types.split(",") if part.strip()]
    return service.preview_leads(
        profile_types=types,
        limit=limit,
        min_conversion_probability=min_conversion_probability,
    )


@router.post(
    "/export",
    response_model=EngagementExportResponse,
    status_code=status.HTTP_200_OK,
    summary="Export engagement CSV",
)
def export_engagement_leads(
    limit: int | None = Query(default=None, ge=1, le=1000),
    profile_types: str = Query(default="External"),
    min_conversion_probability: float | None = Query(default=None, ge=0, le=100),
    service: EngagementService = Depends(get_engagement_service),
) -> EngagementExportResponse:
    types = [part.strip() for part in profile_types.split(",") if part.strip()]
    output_path = Path("data/exports/tara_engagement_leads.csv")
    return service.export_leads(
        output_path,
        profile_types=types,
        limit=limit,
        min_conversion_probability=min_conversion_probability,
    )


@router.post(
    "/send",
    response_model=CustomSendResponse,
    summary="Send custom WhatsApp/SMS/Email to one number",
    description=(
        "Sends a personalized custom message using Tara ML + explainability. "
        "For WhatsApp sandbox: recipient must have messaged the sandbox first (24h window)."
    ),
)
@router.post(
    "/send-custom",
    response_model=CustomSendResponse,
    include_in_schema=False,
)
def send_custom_message(
    request: CustomSendRequest,
    service: EngagementService = Depends(get_engagement_service),
) -> CustomSendResponse:
    return service.send_custom(request)


@router.get(
    "/lead/{entity_id}",
    response_model=EngagementLeadRecord,
    summary="Get engagement lead details (for voice agent seeding)",
)
def get_engagement_lead_record(
    entity_id: str,
    entity_type: str = Query(default="Internal", description="Internal or External"),
    service: EngagementService = Depends(get_engagement_service),
) -> EngagementLeadRecord:
    record = service._export.build_record_for_entity(entity_id, entity_type)
    if not record:
        raise HTTPException(status_code=404, detail="Lead not found")
    return record


def _callback_reason_detail(reason: str | None) -> str:
    """Map internal callback failure codes to user-facing copy."""
    code = (reason or "").split(":")[0].strip()
    messages = {
        "dedup_recent": (
            "A callback to this number was started recently. "
            "Please wait a few minutes before trying again."
        ),
        "voice_not_configured": "Voice calling is not configured on this server.",
        "no_phone": "No phone number was found for this callback request.",
    }
    return messages.get(code, reason or "Unknown error")


def _callback_trigger_html(*, phone: str, success: bool, message: str, detail: str = "") -> str:
    title = "Call Connecting..." if success else "Callback Unavailable"
    color = "#10b981" if success else "#ef4444"
    extra = f'<p class="detail">{detail}</p>' if detail else ""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title} - IDBI Bank</title>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            body {{
                background-color: #0b0f19;
                color: #f3f4f6;
                font-family: 'Outfit', sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
            }}
            .container {{
                text-align: center;
                background: rgba(17, 24, 39, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 24px;
                padding: 40px;
                max-width: 520px;
            }}
            h1 {{ color: {color}; font-size: 2rem; margin-bottom: 16px; }}
            p {{ color: #9ca3af; font-size: 1.05rem; line-height: 1.6; }}
            .phone {{ color: #f3f4f6; font-weight: 600; }}
            .detail {{ color: #d1d5db; font-size: 0.9rem; margin-top: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{title}</h1>
            <p>{message}</p>
            <p>Registered number: <span class="phone">{phone}</span></p>
            {extra}
        </div>
    </body>
    </html>
    """


@router.get(
    "/callback/go/{token}",
    summary="Email/WhatsApp callback CTA — token link (mobile-safe)",
)
def callback_go_token(
    token: str,
    service: EngagementService = Depends(get_engagement_service),
):
    """Resolve email CTA token → CreateSession → LoadContext → Call."""
    from fastapi.responses import HTMLResponse
    from app.engagement.callback_links import CallbackLinkService
    from app.utils.logging_config import get_logger

    logger = get_logger(__name__)
    logger.info("Email callback CTA clicked token=%s", token[:8])

    try:
        links = CallbackLinkService(service._db)
        doc = links.resolve_token(token)
        if not doc:
            html = _callback_trigger_html(
                phone="—",
                success=False,
                message="This callback link has expired or is invalid.",
                detail="Please request a new email or reply CALL ME on WhatsApp.",
            )
            return HTMLResponse(content=html, status_code=410)

        result = service.run_voice_callback(
            phone=doc["phone"],
            entity_id=doc["entity_id"],
            entity_type=doc.get("entity_type", "External"),
            source_channel=doc.get("source_channel", "Email"),
            campaign=doc.get("campaign"),
            skip_dedup=True,
        )
        links.mark_used(token)

        if result.triggered:
            ms = result.timing_ms.get("total", 0)
            html = _callback_trigger_html(
                phone=doc["phone"],
                success=True,
                message=(
                    "Our AI banker is calling you now. Please answer the incoming call. "
                    f"Call initiated in {ms:.0f}ms."
                ),
                detail=f"Session: {result.session_id}",
            )
            return HTMLResponse(content=html)

        html = _callback_trigger_html(
            phone=doc["phone"],
            success=False,
            message="We could not place your callback call right now.",
            detail=_callback_reason_detail(result.reason or result.message),
        )
        return HTMLResponse(content=html, status_code=503)
    except Exception as exc:
        logger.exception("Callback CTA failed token=%s", token[:8])
        html = _callback_trigger_html(
            phone="—",
            success=False,
            message="Something went wrong starting your callback.",
            detail=str(exc)[:300],
        )
        return HTMLResponse(content=html, status_code=500)


@router.get(
    "/callback/trigger",
    summary="Trigger immediate voice call callback to phone",
)
def trigger_voice_callback_route(
    phone: str,
    entity_id: str | None = None,
    entity_type: str = "External",
    source_channel: str = Query(default="Email", description="Email | WhatsApp | Web"),
    campaign: str | None = None,
    service: EngagementService = Depends(get_engagement_service),
):
    from fastapi.responses import HTMLResponse

    result = service.run_voice_callback(
        phone=phone,
        entity_id=entity_id,
        entity_type=entity_type,
        source_channel=source_channel,
        campaign=campaign,
    )

    if result.triggered:
        ms = result.timing_ms.get("total", 0)
        html = _callback_trigger_html(
            phone=phone,
            success=True,
            message=(
                "Our AI banker is calling you now. Please answer the incoming call. "
                f"Call initiated in {ms:.0f}ms."
            ),
            detail=f"Session: {result.session_id}",
        )
        return HTMLResponse(content=html)

    html = _callback_trigger_html(
        phone=phone,
        success=False,
        message="We could not place your callback call right now.",
        detail=_callback_reason_detail(result.reason or result.message),
    )
    return HTMLResponse(content=html, status_code=503)


@router.post(
    "/callback/start",
    response_model=VoiceCallbackStartResponse,
    summary="AI Callback — CreateSession → LoadContext → Call",
    description=(
        "Orchestrates an AI voice callback after Email/WhatsApp CTA click. "
        "Creates a session, loads full agent context, and initiates the outbound call."
    ),
)
def start_ai_callback(
    request: VoiceCallbackStartRequest,
    service: EngagementService = Depends(get_engagement_service),
) -> VoiceCallbackStartResponse:
    if not request.entity_id:
        raise HTTPException(status_code=400, detail="entity_id is required")
    return service.start_ai_callback(
        phone=request.phone,
        entity_id=request.entity_id,
        entity_type=request.entity_type,
        name=request.name,
        campaign=request.campaign,
        source_channel=request.source_channel,
    )


@router.get(
    "/callback/session/{session_id}/context",
    response_model=VoiceAgentContext,
    summary="Load voice agent context for a callback session",
)
def get_callback_session_context(
    session_id: str,
    service: EngagementService = Depends(get_engagement_service),
) -> VoiceAgentContext:
    context = service.get_callback_session_context(session_id)
    if not context:
        raise HTTPException(status_code=404, detail="Callback session not found")
    return context


@router.post(
    "/outreach",
    response_model=OutreachResponse,
    summary="Run multi-channel engagement outreach",
    description=(
        "Personalize & Sequence agent. Routes each lead by preferred_channel "
        "(Voice / WhatsApp / SMS / Email). Use dry_run=true to preview. "
        "Voice uses Twilio Media Streams via bank/bank; SMS/WhatsApp use Twilio; Email uses SMTP/SendGrid."
    ),
)
def run_engagement_outreach(
    request: OutreachRequest,
    service: EngagementService = Depends(get_engagement_service),
) -> OutreachResponse:
    try:
        return service.run_outreach(request)
    except VoiceBridgeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post(
    "/voice/push-campaign",
    response_model=VoiceCampaignResponse,
    status_code=status.HTTP_200_OK,
    summary="Create voice campaign (Twilio + Media Streams)",
)
def push_voice_campaign(
    request: VoiceCampaignRequest,
    service: EngagementService = Depends(get_engagement_service),
) -> VoiceCampaignResponse:
    try:
        return service.push_voice_campaign(request, output_dir=Path("data/exports"))
    except VoiceBridgeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/voice/health", summary="Check voice platform connectivity")
def voice_platform_health(
    service: EngagementService = Depends(get_engagement_service),
) -> dict:
    return service.voice_health()


@router.api_route(
    "/voice/twiml/callback/{session_id}",
    methods=["GET", "POST"],
    summary="TwiML for AI callback greeting (Twilio fallback)",
)
async def voice_callback_twiml(
    session_id: str,
    service: EngagementService = Depends(get_engagement_service),
) -> Response:
    from app.config import get_settings
    from app.engagement.callback_links import resolve_public_api_base, twilio_webhook_url
    from app.engagement.voice_conversation_agent import VoiceConversationAgent
    from app.engagement.voice_twiml import build_conversation_twiml
    from app.utils.logging_config import get_logger

    logger = get_logger(__name__)

    context = service.get_callback_session_context(session_id)
    if not context:
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response><Say>Sorry, session not found.</Say></Response>',
            media_type="application/xml",
        )

    base = resolve_public_api_base(get_settings()).rstrip("/")
    gather_url = twilio_webhook_url(base, f"/api/engagement/voice/twiml/gather/{session_id}")
    outcome_url = twilio_webhook_url(
        base, f"/api/engagement/voice/twiml/outcome/{session_id}?outcome=neutral"
    )

    agent = VoiceConversationAgent(service._db)
    opening = agent.generate_opening(session_id, context)
    _sync_voice_turn(service, context, agent_body=opening.reply, session_id=session_id)
    logger.info("Voice callback opening session=%s lang=%s", session_id, opening.language)

    twiml = build_conversation_twiml(
        say_text=opening.reply,
        gather_url=gather_url,
        outcome_url=outcome_url,
        polly_voice=opening.polly_voice,
        polly_language=opening.polly_language,
        speech_hints=opening.speech_hints,
    )
    return Response(content=twiml, media_type="application/xml")


@router.post("/voice/twiml/gather/{session_id}", summary="TwiML gather handler for callback")
async def voice_callback_gather_twiml(
    session_id: str,
    request: Request,
    service: EngagementService = Depends(get_engagement_service),
) -> Response:
    from app.config import get_settings
    from app.engagement.callback_links import resolve_public_api_base, twilio_webhook_url
    from app.engagement.voice_conversation_agent import VoiceConversationAgent
    from app.engagement.voice_twiml import build_conversation_twiml, build_redirect_twiml
    from app.utils.logging_config import get_logger

    logger = get_logger(__name__)

    context = service.get_callback_session_context(session_id)
    if not context:
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response><Say>Sorry, session not found.</Say></Response>',
            media_type="application/xml",
        )

    form = dict(await request.form())
    speech = str(form.get("SpeechResult") or form.get("Digits") or "")
    call_sid = str(form.get("CallSid") or "")
    logger.info(
        "Voice gather session=%s speech=%r digits=%r call_sid=%s",
        session_id,
        form.get("SpeechResult"),
        form.get("Digits"),
        call_sid[:12] if call_sid else "",
    )

    base = resolve_public_api_base(get_settings()).rstrip("/")
    gather_url = twilio_webhook_url(base, f"/api/engagement/voice/twiml/gather/{session_id}")
    transfer_url = twilio_webhook_url(base, f"/api/engagement/voice/twiml/transfer/{session_id}")
    outcome_url = twilio_webhook_url(
        base, f"/api/engagement/voice/twiml/outcome/{session_id}?outcome=neutral"
    )

    agent = VoiceConversationAgent(service._db)
    turn = agent.handle_turn(
        session_id=session_id,
        context=context,
        user_input=speech,
        call_sid=call_sid or None,
    )
    if speech:
        _sync_voice_turn(
            service, context,
            customer_body=speech, agent_body=turn.reply, call_sid=call_sid, session_id=session_id,
        )
    elif turn.reply:
        _sync_voice_turn(
            service, context,
            customer_body="", agent_body=turn.reply, call_sid=call_sid, session_id=session_id,
        )

    if turn.action == "transfer_rm":
        twiml = build_redirect_twiml(
            say_text=turn.reply,
            redirect_url=transfer_url,
            polly_voice=turn.polly_voice,
            polly_language=turn.polly_language,
        )
        return Response(content=twiml, media_type="application/xml")

    if turn.action == "end_call":
        closing_url = f"{outcome_url.split('?')[0]}?outcome={turn.outcome or 'neutral'}"
        twiml = build_redirect_twiml(
            say_text=turn.reply,
            redirect_url=closing_url,
            polly_voice=turn.polly_voice,
            polly_language=turn.polly_language,
        )
        return Response(content=twiml, media_type="application/xml")

    twiml = build_conversation_twiml(
        say_text=turn.reply,
        gather_url=gather_url,
        outcome_url=outcome_url,
        polly_voice=turn.polly_voice,
        polly_language=turn.polly_language,
        speech_hints=turn.speech_hints,
    )
    return Response(content=twiml, media_type="application/xml")


def _sync_voice_turn(
    service: EngagementService,
    context: VoiceAgentContext,
    *,
    customer_body: str | None = None,
    agent_body: str | None = None,
    call_sid: str = "",
    session_id: str = "",
) -> None:
    if not customer_body and not agent_body:
        return
    try:
        service.sync_conversation_turn(
            {
                "channel": "Voice",
                "phone": context.phone,
                "entity_id": context.customer_id,
                "entity_type": context.entity_type,
                "customer_body": customer_body or "(call connected)",
                "agent_body": agent_body,
                "provider_sid": call_sid or None,
                "session_id": session_id or None,
            }
        )
    except Exception:
        pass


def _record_twilio_voice_outcome(
    service: EngagementService,
    *,
    session_id: str,
    context: VoiceAgentContext | None,
    outcome: str,
    call_sid: str = "",
) -> None:
    if not context:
        return
    from app.engagement.voice_conversation_agent import VoiceConversationAgent
    from app.schemas.engagement import VoiceCallOutcomeRequest

    preview = VoiceConversationAgent(service._db).get_transcript_preview(session_id)
    try:
        service.record_voice_call_outcome(
            VoiceCallOutcomeRequest(
                call_sid=call_sid or f"session:{session_id}",
                entity_id=context.customer_id,
                entity_type=context.entity_type,
                recipient=context.phone,
                call_status="completed",
                duration_seconds=0,
                intent=context.intent,
                outcome=outcome,
                transcript_preview=preview or None,
                metadata={"session_id": session_id, "provider": "twilio_conversational"},
            )
        )
    except Exception:
        pass


@router.post("/voice/twiml/transfer/{session_id}", summary="RM handoff after interested callback")
async def voice_callback_transfer(
    session_id: str,
    request: Request,
    service: EngagementService = Depends(get_engagement_service),
) -> Response:
    from app.engagement.voice_locale import resolve_voice_locale
    from app.engagement.voice_twiml import build_end_twiml
    from app.onboarding.orchestrator import OnboardingOrchestrator
    from app.schemas.onboarding import LeadResponseCaptureRequest

    form = dict(await request.form())
    call_sid = str(form.get("CallSid") or "")
    context = service.get_callback_session_context(session_id)
    if context:
        OnboardingOrchestrator(service._db).process_lead_response(
            LeadResponseCaptureRequest(
                entity_id=context.customer_id,
                entity_type=context.entity_type,
                channel="Voice",
                response_type="interested",
                phone=context.phone,
                name=context.name,
            )
        )
        _record_twilio_voice_outcome(
            service,
            session_id=session_id,
            context=context,
            outcome="interested",
            call_sid=call_sid,
        )

    locale = resolve_voice_locale(context.lang if context else "english")
    from app.config import get_settings

    rm_phone = get_settings().engagement_callback_phone or "our relationship manager"
    closing = (
        f"Thank you. A relationship manager will call you shortly. "
        f"You can also reach us at {rm_phone}. Goodbye."
    )
    twiml = build_end_twiml(
        say_text=closing,
        polly_voice=str(locale["polly_voice"]),
        polly_language=str(locale["polly_language"]),
    )
    return Response(content=twiml, media_type="application/xml")


@router.post("/voice/twiml/outcome/{session_id}", summary="Neutral/declined callback outcome")
async def voice_callback_outcome(
    session_id: str,
    request: Request,
    outcome: str = Query(default="neutral"),
    service: EngagementService = Depends(get_engagement_service),
) -> Response:
    from app.engagement.voice_locale import resolve_voice_locale
    from app.engagement.voice_twiml import build_end_twiml

    form = dict(await request.form())
    call_sid = str(form.get("CallSid") or "")
    context = service.get_callback_session_context(session_id)
    resolved_outcome = (outcome or "neutral").strip().lower()
    if context:
        _record_twilio_voice_outcome(
            service,
            session_id=session_id,
            context=context,
            outcome=resolved_outcome,
            call_sid=call_sid,
        )

    locale = resolve_voice_locale(context.lang if context else "english")
    if resolved_outcome == "declined":
        message = "Thank you for your time. We will share offer details on WhatsApp or SMS."
    else:
        message = "Thank you for speaking with IDBI Bank. We will follow up shortly."
    twiml = build_end_twiml(
        say_text=message,
        polly_voice=str(locale["polly_voice"]),
        polly_language=str(locale["polly_language"]),
    )
    return Response(content=twiml, media_type="application/xml")


@router.post(
    "/voice/call-outcome",
    response_model=VoiceCallOutcomeResponse,
    summary="Record voice call outcome from bank/bank runtime",
)
def record_voice_call_outcome(
    request: VoiceCallOutcomeRequest,
    service: EngagementService = Depends(get_engagement_service),
) -> VoiceCallOutcomeResponse:
    result = service.record_voice_call_outcome(request)
    return VoiceCallOutcomeResponse(**result)


@router.get("/events/{entity_id}", summary="Engagement delivery history for a lead/customer")
def get_engagement_events(
    entity_id: UUID,
    service: EngagementService = Depends(get_engagement_service),
) -> list[dict]:
    return service.get_events_for_entity(entity_id)


@router.post("/sequence/create", summary="Create multi-touch outreach sequence for a lead")
def create_engagement_sequence(
    entity_id: str,
    entity_type: str = "External",
    service: EngagementService = Depends(get_engagement_service),
) -> dict:
    return service.create_sequence(entity_id, entity_type=entity_type)


@router.post("/sequence/process-due", summary="Send due sequence touches")
def process_due_sequences(
    dry_run: bool = False,
    limit: int = 50,
    service: EngagementService = Depends(get_engagement_service),
) -> dict:
    return service.process_due_sequences(dry_run=dry_run, limit=limit)


@router.post("/webhooks/sms", summary="Twilio SMS inbound — conversational reply + DB storage")
async def sms_inbound_webhook(
    request: Request,
    service: EngagementService = Depends(get_engagement_service),
) -> Response:
    from xml.sax.saxutils import escape

    form = dict(await request.form())
    result = service.process_sms_inbound(form)
    reply = escape((result.get("reply") or "")[:1500])
    twiml = (
        f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{reply}</Message></Response>'
        if reply
        else '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
    )
    return Response(content=twiml, media_type="application/xml")


@router.post(
    "/webhooks/whatsapp",
    summary="Twilio WhatsApp inbound — conversational reply + DB storage",
)
async def whatsapp_inbound_webhook(
    request: Request,
    service: EngagementService = Depends(get_engagement_service),
) -> Response:
    from xml.sax.saxutils import escape

    form = dict(await request.form())
    result = service.process_whatsapp_inbound(form)
    reply = escape((result.get("reply") or "")[:1500])
    twiml = (
        f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{reply}</Message></Response>'
        if reply
        else '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
    )
    return Response(content=twiml, media_type="application/xml")


@router.post("/webhooks/email", summary="Email reply webhook — capture + auto-reply in DB")
async def email_inbound_webhook(
    request: Request,
    service: EngagementService = Depends(get_engagement_service),
) -> dict:
    body = await request.json()
    return service.process_email_inbound(body)


@router.post("/conversations/sync", summary="Sync customer/agent turn from bank runtime")
def sync_conversation_turn(
    payload: dict,
    service: EngagementService = Depends(get_engagement_service),
) -> dict:
    return service.sync_conversation_turn(payload)


@router.post("/conversations/process-inbound", summary="Process inbound message (JSON — for bank proxy)")
async def process_inbound_json(
    request: Request,
    service: EngagementService = Depends(get_engagement_service),
) -> dict:
    body = await request.json()
    channel = (body.get("channel") or "WhatsApp").strip()
    if channel.lower() == "email":
        return service.process_email_inbound(body)
    return service.process_whatsapp_inbound(
        {
            "Body": body.get("body") or body.get("text") or "",
            "From": body.get("phone") or "",
            "ButtonPayload": body.get("button_payload") or "",
            "MessageSid": body.get("provider_sid"),
        }
    )


@router.post("/conversations/inbound", summary="Simulate inbound message (demo / testing)")
def simulate_inbound_message(
    request: InboundMessageRequest,
    service: EngagementService = Depends(get_engagement_service),
) -> dict:
    if request.channel == "Email":
        return service.process_email_inbound(request.model_dump())
    return service.process_whatsapp_inbound(
        {
            "Body": request.body,
            "From": request.phone or "",
            "ButtonPayload": request.button_payload or "",
        }
    )


@router.get(
    "/conversations/{entity_id}",
    response_model=ConversationThreadResponse,
    summary="Full conversation thread for a customer/lead",
)
def get_conversation_thread(
    entity_id: str,
    channel: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    service: EngagementService = Depends(get_engagement_service),
) -> ConversationThreadResponse:
    data = service.get_conversation_thread(entity_id, channel=channel, limit=limit)
    return ConversationThreadResponse(**data)


@router.get("/conversations/inbox/recent", summary="Recent conversation threads")
def list_conversation_inbox(
    limit: int = Query(default=50, ge=1, le=200),
    service: EngagementService = Depends(get_engagement_service),
) -> list[dict]:
    return service.list_conversation_inbox(limit=limit)


@router.get("/conversations/stream", summary="SSE — real-time conversation updates")
async def conversation_stream(request: Request) -> StreamingResponse:
    import asyncio

    from app.events import add_listener, remove_listener

    async def event_generator():
        queue: asyncio.Queue = asyncio.Queue()
        add_listener(queue)
        try:
            yield "event: connected\ndata: {}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=25.0)
                    yield payload
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            remove_listener(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/sms/compliance-check", summary="Demonstrate SMS DLT compliance validation")
def sms_compliance_check(
    entity_id: str,
    service: EngagementService = Depends(get_engagement_service),
) -> dict:
    return service.check_sms_compliance(entity_id)


@router.get("/cta/{token}", summary="Track email CTA click then redirect")
def track_email_cta(
    token: str,
    service: EngagementService = Depends(get_engagement_service),
):
    from fastapi.responses import RedirectResponse

    url = service.record_cta_click(token)
    return RedirectResponse(url=url or "https://www.idbibank.in/")
