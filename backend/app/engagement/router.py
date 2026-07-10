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


@router.get(
    "/callback/trigger",
    summary="Trigger immediate voice call callback to phone",
)
def trigger_voice_callback_route(
    phone: str,
    entity_id: str | None = None,
    entity_type: str = "External",
    service: EngagementService = Depends(get_engagement_service),
):
    from fastapi.responses import HTMLResponse
    try:
        service.trigger_voice_callback(
            phone=phone,
            entity_id=entity_id,
            entity_type=entity_type,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Call Scheduled - IDBI Bank</title>
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
                background-image: radial-gradient(at 0% 0%, rgba(79, 70, 229, 0.15) 0px, transparent 50%), radial-gradient(at 100% 100%, rgba(16, 185, 129, 0.1) 0px, transparent 50%);
            }}
            .container {{
                text-align: center;
                background: rgba(17, 24, 39, 0.7);
                backdrop-filter: blur(20px);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 24px;
                padding: 40px;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
                max-width: 480px;
            }}
            h1 {{
                color: #10b981;
                font-size: 2rem;
                margin-bottom: 16px;
            }}
            p {{
                color: #9ca3af;
                font-size: 1.1rem;
                line-height: 1.6;
            }}
            .phone {{
                color: #f3f4f6;
                font-weight: 600;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Call Initiating...</h1>
            <p>Thank you! Our AI Banker is placing a call to your registered phone number (<span class="phone">{phone}</span>) right now.</p>
            <p>Please keep your phone nearby and answer when it rings.</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


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
    return RedirectResponse(url=url or "https://www.idbi.bank.in")
