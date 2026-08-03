from __future__ import annotations

ALL_MODULES: dict[str, dict] = {
    "dashboard": {"name": "Dashboard", "phase": 0, "icon": "grid"},
    "crm": {"name": "CRM", "phase": 1, "icon": "users"},
    "dealers": {"name": "Dealers / Portal", "phase": 1, "icon": "store"},
    "sales": {"name": "Sales", "phase": 1, "icon": "cart"},
    "pos": {"name": "Scan Billing", "phase": 1, "icon": "scan"},
    "rfid": {"name": "RFID Warehouse", "phase": 1, "icon": "radio"},
    "purchase": {"name": "Purchase", "phase": 1, "icon": "truck"},
    "inventory": {"name": "Inventory", "phase": 1, "icon": "box"},
    "store": {"name": "Store", "phase": 1, "icon": "box"},
    "logistics": {"name": "Logistics / Dispatch", "phase": 1, "icon": "ship"},
    "accounting": {"name": "Accounting", "phase": 1, "icon": "ledger"},
    "manufacturing": {"name": "Manufacturing", "phase": 3, "icon": "factory"},
    "quality": {"name": "Quality", "phase": 3, "icon": "check"},
    "hrms": {"name": "HRMS", "phase": 4, "icon": "badge"},
    "projects": {"name": "Projects", "phase": 4, "icon": "kanban"},
    "service": {"name": "Service", "phase": 3, "icon": "wrench"},
    "documents": {"name": "Documents", "phase": 2, "icon": "file"},
    "reports": {"name": "Reports", "phase": 2, "icon": "chart"},
    "bi": {"name": "Business Intelligence", "phase": 4, "icon": "pulse"},
    "ai": {"name": "AI Assistant", "phase": 4, "icon": "spark"},
    "agents": {"name": "Kanha Agents", "phase": 4, "icon": "bot"},
    "whatsapp": {"name": "WhatsApp OS", "phase": 1, "icon": "wa"},
    "compliance": {"name": "India Compliance", "phase": 1, "icon": "shield"},
    "approvals": {"name": "Approvals / Hierarchy", "phase": 0, "icon": "check"},
    "ops-board": {"name": "Ops Pending Board", "phase": 0, "icon": "grid"},
    "visit": {"name": "Visit / Field", "phase": 1, "icon": "users"},
    "tasks": {"name": "Task Desk", "phase": 1, "icon": "kanban"},
    "followup": {"name": "Followups", "phase": 1, "icon": "bolt"},
    "payments-ops": {"name": "Payment Requests", "phase": 1, "icon": "ledger"},
    "indents": {"name": "Indents / Store Req", "phase": 3, "icon": "box"},
    "mis": {"name": "MIS Analytics", "phase": 2, "icon": "chart"},
    "rfq": {"name": "RFQ / Vendor Rates", "phase": 1, "icon": "truck"},
    "books": {"name": "Kanha Books", "phase": 1, "icon": "ledger"},
    # "tally" removed — was duplicate label of Kanha Books; #/tally redirects to #/books
    "bridges": {"name": "Connected Apps", "phase": 0, "icon": "bolt"},
    "ha": {"name": "Resilience / HA", "phase": 0, "icon": "shield"},
    "watch": {"name": "Live Monitor", "phase": 0, "icon": "cam"},
    "activity": {"name": "Activity / Tracking", "phase": 0, "icon": "pulse"},
    "automation": {"name": "Automation", "phase": 4, "icon": "bolt"},
    "extras": {"name": "Kanha Extras", "phase": 4, "icon": "spark"},
    "masters": {"name": "Masters", "phase": 0, "icon": "box"},
    "settings": {"name": "Admin / Settings", "phase": 0, "icon": "gear"},
}

DEFAULT_PERMISSIONS = [
    "dashboard.view",
    "crm.*",
    "dealers.*",
    "sales.*",
    "pos.*",
    "rfid.*",
    "purchase.*",
    "inventory.*",
    "store.*",
    "logistics.*",
    "accounting.*",
    "books.*",
    "manufacturing.*",
    "quality.*",
    "hrms.*",
    "projects.*",
    "service.*",
    "documents.*",
    "reports.*",
    "bi.*",
    "ai.*",
    "agents.*",
    "whatsapp.*",
    "compliance.*",
    "approvals.*",
    "ops-board.*",
    "visit.*",
    "tasks.*",
    "followup.*",
    "payments-ops.*",
    "indents.*",
    "mis.*",
    "rfq.*",
    "books.*",
    "bridges.*",
    "ha.*",
    "watch.*",
    "activity.*",
    "automation.*",
    "extras.*",
    "masters.*",
    "comms.*",
    "settings.*",
]


def default_modules_enabled() -> dict[str, bool]:
    return {k: True for k in ALL_MODULES}


# Old hash routes → canonical module (no second nav item)
MODULE_ALIASES: dict[str, str] = {
    "tally": "books",
}


def canonicalize_modules_enabled(enabled: dict | None) -> dict[str, bool]:
    """Drop retired aliases (e.g. tally) and keep a single books flag."""
    out = dict(enabled or {})
    if "tally" in out:
        if out.pop("tally") and not out.get("books"):
            out["books"] = True
    # Keep only known modules
    return {k: bool(out.get(k, True)) for k in ALL_MODULES}


def gst_split(amount: float, rate: float, intra_state: bool = True) -> dict[str, float]:
    tax = round(amount * rate / 100.0, 2)
    if intra_state:
        half = round(tax / 2.0, 2)
        return {"cgst": half, "sgst": half, "igst": 0.0, "total_tax": tax}
    return {"cgst": 0.0, "sgst": 0.0, "igst": tax, "total_tax": tax}
