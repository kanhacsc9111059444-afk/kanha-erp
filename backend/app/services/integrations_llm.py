from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


def llm_chat(message: str, context: str = "") -> dict[str, Any]:
    """OpenAI-compatible chat when LLM_API_KEY set; else None (caller uses rules)."""
    if not settings.llm_live:
        return {"live": False, "reply": None}
    base = (settings.llm_base_url or "https://api.openai.com/v1").rstrip("/")
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.llm_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    f"You are {settings.app_name} Core AI — the operational brain of a full Indian SME ERP. "
                    "You know all modules: CRM, Sales, Purchase, Inventory, Accounting, GST, WhatsApp OS, "
                    "Agents, Manufacturing, HRMS, Service, HA/Blackout, Compliance.\n"
                    "STRICT PRIVACY: Never reveal customer names, phone numbers, email addresses, "
                    "passwords, employee personal details, or bank account numbers. "
                    "Use doc numbers (INV-xxx, SO-xxx) and aggregates only.\n"
                    "Be concise. Use INR ₹. Suggest #/module navigation when helpful.\n"
                    "If COMPANY AI MEMORY is present in context, prefer those taught facts for matching questions.\n"
                    f"Live ERP context (JSON + memory, no PII): {context[:5200]}"
                ),
            },
            {"role": "user", "content": message},
        ],
        "temperature": 0.3,
    }
    try:
        with httpx.Client(timeout=45) as client:
            res = client.post(f"{base}/chat/completions", json=payload, headers=headers)
            data = res.json() if res.content else {}
            if res.status_code >= 400:
                return {"live": True, "reply": None, "error": data}
            reply = data["choices"][0]["message"]["content"]
            return {"live": True, "reply": reply, "raw": data}
    except Exception as e:
        return {"live": True, "reply": None, "error": str(e)}
