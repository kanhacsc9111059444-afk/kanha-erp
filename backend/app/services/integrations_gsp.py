from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.core.config import settings


def _pick(data: dict[str, Any], *keys: str) -> Any:
    for k in keys:
        if data.get(k) not in (None, ""):
            return data[k]
    # nested common GSP shapes
    for nest in ("data", "result", "response", "IrnDetails", "EwbDetails"):
        inner = data.get(nest)
        if isinstance(inner, dict):
            for k in keys:
                if inner.get(k) not in (None, ""):
                    return inner[k]
    return None


def push_einvoice_irn(payload: dict[str, Any]) -> dict[str, Any]:
    """Push IRN to GSP when configured; otherwise local demo IRN remains source of truth."""
    if not settings.gsp_live:
        return {
            "live": False,
            "status": "local_demo_irn",
            "note": "Set GSP_BASE_URL + GSP_API_KEY for NIC/GSP push",
            "payload": payload,
            "irn": payload.get("irn"),
        }
    headers = {
        "Authorization": f"Bearer {settings.gsp_api_key}",
        "Content-Type": "application/json",
        "X-Gsp-Secret": settings.gsp_api_secret or "",
    }
    url = f"{settings.gsp_base_url.rstrip('/')}/einvoice/generate"
    try:
        with httpx.Client(timeout=60) as client:
            res = client.post(url, json=payload, headers=headers)
            data = res.json() if res.content else {}
            if not isinstance(data, dict):
                data = {"raw": data}
            ok = res.status_code < 400
            irn = _pick(data, "Irn", "irn", "IRN") if ok else None
            ack_no = _pick(data, "AckNo", "ack_no", "AckNum") if ok else None
            ack_date = _pick(data, "AckDt", "ack_date", "AckDate") if ok else None
            return {
                "live": True,
                "status": "ok" if ok else "failed",
                "http_status": res.status_code,
                "response": data,
                "irn": irn,
                "ack_no": ack_no,
                "ack_date": ack_date,
            }
    except Exception as e:
        return {"live": True, "status": "failed", "error": str(e)}


def push_eway(payload: dict[str, Any]) -> dict[str, Any]:
    if not settings.gsp_live:
        return {
            "live": False,
            "status": "local_demo_eway",
            "note": "Set GSP keys for live e-Way",
            "payload": payload,
            "ewb_no": payload.get("ewb_no"),
        }
    headers = {
        "Authorization": f"Bearer {settings.gsp_api_key}",
        "Content-Type": "application/json",
        "X-Gsp-Secret": settings.gsp_api_secret or "",
    }
    url = f"{settings.gsp_base_url.rstrip('/')}/eway/generate"
    try:
        with httpx.Client(timeout=60) as client:
            res = client.post(url, json=payload, headers=headers)
            data = res.json() if res.content else {}
            if not isinstance(data, dict):
                data = {"raw": data}
            ok = res.status_code < 400
            ewb_no = _pick(data, "EwbNo", "ewb_no", "ewayBillNo", "EwbNumber") if ok else None
            valid_upto = _pick(data, "ValidUpto", "valid_upto", "validUpto") if ok else None
            return {
                "live": True,
                "status": "ok" if ok else "failed",
                "http_status": res.status_code,
                "response": data,
                "ewb_no": ewb_no,
                "valid_upto": valid_upto,
            }
    except Exception as e:
        return {"live": True, "status": "failed", "error": str(e)}


def gsp_stamp() -> str:
    return datetime.utcnow().isoformat() + "Z"
