"""SSE broadcast bus for real-time CRM conversation updates."""

from __future__ import annotations

import asyncio
import json
import logging

logger = logging.getLogger("TaraEvents")

_sse_listeners: list[asyncio.Queue] = []


def broadcast_event(event_type: str, data: dict) -> None:
    payload = f"event: {event_type}\ndata: {json.dumps(data, default=str, ensure_ascii=False)}\n\n"
    for q in list(_sse_listeners):
        try:
            q.put_nowait(payload)
        except Exception:
            pass


def add_listener(q: asyncio.Queue) -> None:
    _sse_listeners.append(q)


def remove_listener(q: asyncio.Queue) -> None:
    try:
        _sse_listeners.remove(q)
    except ValueError:
        pass
