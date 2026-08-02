"""
Industry profiles — same ERP kernel, different module scopes.
Manufacturing / trading / service / retail / professional each get their own concept.
"""
from __future__ import annotations

from typing import Any

# Core always on for every company type
_CORE = {
    "dashboard": True,
    "settings": True,
    "documents": True,
    "reports": True,
    "automation": True,
    "ha": True,
    "agents": True,
    "watch": True,  # Live monitor (stream-only)
}

INDUSTRY_PROFILES: dict[str, dict[str, Any]] = {
    "manufacturing": {
        "label": "Manufacturing / Production",
        "blurb": "BOM, work orders, machines, MRP, QC, inventory, purchase, sales",
        "modules": {
            **_CORE,
            "crm": True,
            "sales": True,
            "purchase": True,
            "inventory": True,
            "logistics": True,
            "manufacturing": True,
            "quality": True,
            "accounting": True,
            "hrms": True,
            "projects": False,
            "service": True,
            "pos": False,
            "rfid": True,
            "dealers": True,
            "whatsapp": True,
            "compliance": True,
            "bi": True,
            "ai": True,
            "apps": True,
        },
    },
    "trading": {
        "label": "Trading / Distribution",
        "blurb": "Buy–sell, dealers, logistics, GST, WhatsApp chase",
        "modules": {
            **_CORE,
            "crm": True,
            "dealers": True,
            "sales": True,
            "purchase": True,
            "inventory": True,
            "logistics": True,
            "manufacturing": False,
            "quality": False,
            "accounting": True,
            "hrms": True,
            "projects": False,
            "service": False,
            "pos": True,
            "rfid": True,
            "whatsapp": True,
            "compliance": True,
            "bi": True,
            "ai": True,
            "apps": True,
        },
    },
    "service": {
        "label": "Service / AMC / Consulting",
        "blurb": "Tickets, projects, HR, CRM, billing — light inventory",
        "modules": {
            **_CORE,
            "crm": True,
            "sales": True,
            "purchase": False,
            "inventory": False,
            "logistics": False,
            "manufacturing": False,
            "quality": False,
            "accounting": True,
            "hrms": True,
            "projects": True,
            "service": True,
            "pos": False,
            "rfid": False,
            "dealers": False,
            "whatsapp": True,
            "compliance": True,
            "bi": True,
            "ai": True,
            "apps": True,
        },
    },
    "retail": {
        "label": "Retail / Shop / POS",
        "blurb": "Scan billing, stock, GST, walk-in customers",
        "modules": {
            **_CORE,
            "crm": True,
            "sales": True,
            "pos": True,
            "purchase": True,
            "inventory": True,
            "logistics": False,
            "manufacturing": False,
            "quality": False,
            "accounting": True,
            "hrms": True,
            "projects": False,
            "service": False,
            "rfid": False,
            "dealers": False,
            "whatsapp": True,
            "compliance": True,
            "bi": True,
            "ai": True,
            "apps": True,
        },
    },
    "professional": {
        "label": "Individual / Solo / Freelancer",
        "blurb": "Lean: CRM, invoices, expenses, WhatsApp — minimal factory modules",
        "modules": {
            **_CORE,
            "crm": True,
            "sales": True,
            "purchase": False,
            "inventory": False,
            "logistics": False,
            "manufacturing": False,
            "quality": False,
            "accounting": True,
            "hrms": False,
            "projects": True,
            "service": True,
            "pos": False,
            "rfid": False,
            "dealers": False,
            "whatsapp": True,
            "compliance": True,
            "bi": False,
            "ai": True,
            "apps": True,
            "automation": True,
        },
    },
    "hybrid": {
        "label": "Hybrid (all modules)",
        "blurb": "Full KanhaERP — manufacture + trade + service together",
        "modules": {k: True for k in (
            list(_CORE.keys())
            + [
                "crm", "dealers", "sales", "pos", "rfid", "purchase", "inventory",
                "logistics", "accounting", "manufacturing", "quality", "hrms",
                "projects", "service", "whatsapp", "compliance", "bi", "ai", "apps",
            ]
        )},
    },
}


def apply_profile(profile_id: str) -> dict[str, bool]:
    p = INDUSTRY_PROFILES.get(profile_id) or INDUSTRY_PROFILES["hybrid"]
    return dict(p["modules"])


def list_profiles() -> list[dict]:
    return [
        {"id": k, "label": v["label"], "blurb": v["blurb"], "module_count": sum(1 for x in v["modules"].values() if x)}
        for k, v in INDUSTRY_PROFILES.items()
    ]
