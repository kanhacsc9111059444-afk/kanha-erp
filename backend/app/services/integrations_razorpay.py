from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any

import httpx

from app.core.config import settings


def create_razorpay_order(amount_inr: float, receipt: str = "") -> dict[str, Any]:
    """Create Razorpay order when keys set; otherwise deterministic demo intent."""
    amount_paise = int(round(float(amount_inr) * 100))
    if not settings.razorpay_live:
        return {
            "provider": "razorpay",
            "live": False,
            "order_id": f"order_local_{int(time.time())}_{amount_paise}",
            "amount": amount_paise,
            "currency": "INR",
            "status": "created",
            "key_id": None,
            "note": "Set RAZORPAY_KEY_ID + RAZORPAY_KEY_SECRET for live checkout",
        }
    auth = (settings.razorpay_key_id, settings.razorpay_key_secret)
    payload = {
        "amount": amount_paise,
        "currency": "INR",
        "receipt": (receipt or f"rcpt_{int(time.time())}")[:40],
        "payment_capture": 1,
    }
    with httpx.Client(timeout=30) as client:
        res = client.post("https://api.razorpay.com/v1/orders", json=payload, auth=auth)
        data = res.json() if res.content else {}
        if res.status_code >= 400:
            return {"provider": "razorpay", "live": True, "status": "failed", "error": data}
        return {
            "provider": "razorpay",
            "live": True,
            "order_id": data.get("id"),
            "amount": data.get("amount", amount_paise),
            "currency": data.get("currency", "INR"),
            "status": data.get("status", "created"),
            "key_id": settings.razorpay_key_id,
            "raw": data,
        }


def verify_razorpay_signature(order_id: str, payment_id: str, signature: str) -> bool:
    # Demo-live: accept deterministic demo payment ids without keys
    if not settings.razorpay_live:
        return bool(order_id) and bool(payment_id) and str(payment_id).startswith("pay_demo_")
    msg = f"{order_id}|{payment_id}".encode()
    dig = hmac.new(settings.razorpay_key_secret.encode(), msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(dig, signature or "")


def demo_capture_payload(order_id: str, amount_paise: int) -> dict[str, Any]:
    """Simulated checkout capture — mirrors Razorpay success payload for UI/flows."""
    pid = f"pay_demo_{int(time.time())}_{amount_paise}"
    return {
        "provider": "razorpay",
        "live": False,
        "demo": True,
        "order_id": order_id,
        "payment_id": pid,
        "signature": f"sig_demo_{pid[-8:]}",
        "amount": amount_paise,
        "currency": "INR",
        "status": "captured",
        "note": "Demo capture — invoice settled in ERP books. Live checkout needs Razorpay keys.",
    }
