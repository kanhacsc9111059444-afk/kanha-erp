"""
WhatsApp Cloud API + Demo adapter.
Without Meta keys: still fully functional — messages marked sent_demo with fake wamid.
With WHATSAPP_TOKEN + PHONE_NUMBER_ID: real Meta Cloud send.
"""
from __future__ import annotations

import hashlib
import time
from typing import Any

import httpx

from app.core.config import settings


def re_phone(raw: str) -> str:
    digits = "".join(ch for ch in (raw or "") if ch.isdigit())
    if digits and not digits.startswith("91") and len(digits) == 10:
        digits = "91" + digits
    return digits


def _demo_wamid(to: str, body: str) -> str:
    h = hashlib.sha1(f"{to}:{body}:{time.time()}".encode()).hexdigest()[:16]
    return f"wamid.DEMO{h.upper()}"


def demo_send(to_phone: str, body: str, *, template: str = "") -> dict[str, Any]:
    """Local fully-working send path — looks like Meta success for UI/flows."""
    phone = re_phone(to_phone)
    wamid = _demo_wamid(phone, body or template)
    return {
        "provider": "demo_meta",
        "status": "sent",
        "live": False,
        "demo": True,
        "to": phone,
        "message_id": wamid,
        "template": template or None,
        "note": (
            "Demo WhatsApp send OK — message stored as sent. "
            "Go-live: set WHATSAPP_TOKEN + WHATSAPP_PHONE_NUMBER_ID for Meta Cloud."
        ),
        "response": {
            "messaging_product": "whatsapp",
            "contacts": [{"input": phone, "wa_id": phone}],
            "messages": [{"id": wamid}],
        },
    }


async def send_whatsapp_cloud(to_phone: str, body: str, template: str = "") -> dict[str, Any]:
    phone = re_phone(to_phone)
    if not settings.whatsapp_live:
        return demo_send(phone, body, template=template)
    url = (
        f"https://graph.facebook.com/{settings.whatsapp_api_version}/"
        f"{settings.whatsapp_phone_number_id}/messages"
    )
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": (body or "")[:4096]},
    }
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_token}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(url, json=payload, headers=headers)
        data = res.json() if res.content else {}
        if res.status_code >= 400:
            return {"provider": "meta", "status": "failed", "live": True, "error": data, "to": phone}
        mid = None
        try:
            mid = data["messages"][0]["id"]
        except Exception:
            mid = None
        return {
            "provider": "meta",
            "status": "sent",
            "live": True,
            "response": data,
            "to": phone,
            "message_id": mid,
        }


def send_whatsapp_cloud_sync(to_phone: str, body: str, template: str = "") -> dict[str, Any]:
    phone = re_phone(to_phone)
    if not settings.whatsapp_live:
        return demo_send(phone, body, template=template)
    url = (
        f"https://graph.facebook.com/{settings.whatsapp_api_version}/"
        f"{settings.whatsapp_phone_number_id}/messages"
    )
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": (body or "")[:4096]},
    }
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_token}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=30) as client:
        res = client.post(url, json=payload, headers=headers)
        data = res.json() if res.content else {}
        if res.status_code >= 400:
            return {"provider": "meta", "status": "failed", "live": True, "error": data, "to": phone}
        mid = None
        try:
            mid = data["messages"][0]["id"]
        except Exception:
            mid = None
        return {
            "provider": "meta",
            "status": "sent",
            "live": True,
            "response": data,
            "to": phone,
            "message_id": mid,
        }
