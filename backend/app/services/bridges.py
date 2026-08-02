"""
Kanha Bridges — dual-mode channels.

Where Kanha is strong → native default.
Where market tools are stronger → optional bridge (Tally, Razorpay, Bank, GSP, Meta, SMTP, Maps, LLM).

Company picks per channel: native | bridge | hybrid.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Company, Customer, Invoice, JournalEntry, Product, Vendor

# ERP accounting data targets — Tally stays; Marg / Busy / Vyapar / Other added alongside
ERP_DATA_TARGETS: list[dict[str, Any]] = [
    {
        "id": "tally",
        "label": "Tally",
        "format": "kanha_tally_pack_v1",
        "hint": "CA / GST habit — export pack → Tally import / CSV mapper. Existing Tally APIs remain.",
        "events": ["invoice.created", "payment.recorded", "party.upsert", "journal.posted"],
    },
    {
        "id": "marg",
        "label": "Marg ERP",
        "format": "kanha_marg_pack_v1",
        "hint": "Client pe Marg chal raha ho — party / item / voucher / stock pack + webhook hook.",
        "events": ["invoice.created", "payment.recorded", "party.upsert", "stock.adjust"],
    },
    {
        "id": "busy",
        "label": "Busy Accounting",
        "format": "kanha_busy_pack_v1",
        "hint": "Busy books primary — daybook / journal / party handoff pack.",
        "events": ["invoice.created", "payment.recorded", "journal.posted"],
    },
    {
        "id": "vyapar",
        "label": "Vyapar / billing",
        "format": "kanha_vyapar_pack_v1",
        "hint": "Shop billing app — party + invoice lightweight pack.",
        "events": ["invoice.created", "party.upsert"],
    },
    {
        "id": "other",
        "label": "Other ERP / CSV",
        "format": "kanha_erp_generic_pack_v1",
        "hint": "Focus / Logic / Odoo / any — generic JSON/CSV-shaped pack + custom hook.",
        "events": ["invoice.created", "payment.recorded", "party.upsert", "stock.adjust", "journal.posted", "generic"],
    },
]


# Channel catalog — UI + API single source of truth
BRIDGE_CHANNELS: list[dict[str, Any]] = [
    {
        "id": "accounting",
        "title": "Accounting / Books",
        "why": "CA habit in Tally / Marg / Busy — Kanha Books native; bridge any ERP data pack.",
        "native": {"id": "kanha_books", "label": "Kanha Books (built-in)"},
        "bridge": {"id": "erp_pack", "label": "Tally · Marg · Busy · Other ERP pack"},
        "modes": ["native", "bridge", "hybrid"],
        "default_mode": "native",
        "live_flag": None,
        "edge": "Ops in Kanha · export/import packs for Tally + Marg + other (existing Tally path kept)",
    },
    {
        "id": "payments",
        "title": "Customer payments",
        "why": "Checkout / UPI collect is stronger on Razorpay.",
        "native": {"id": "kanha_pay", "label": "Kanha settle (demo-live / manual)"},
        "bridge": {"id": "razorpay", "label": "Razorpay bridge"},
        "modes": ["native", "bridge", "hybrid"],
        "default_mode": "hybrid",
        "live_flag": "razorpay_live",
        "edge": "Intent + capture in ERP; live keys = real checkout path",
    },
    {
        "id": "payroll_payout",
        "title": "Salary / vendor bank payout",
        "why": "Real NEFT needs bank / payout partner — we stay honest.",
        "native": {"id": "demo_neft", "label": "Kanha DEMO-NEFT + books voucher"},
        "bridge": {"id": "bank_api", "label": "Bank / RazorpayX bridge (when keyed)"},
        "modes": ["native", "bridge"],
        "default_mode": "native",
        "live_flag": None,
        "edge": "Always posts books; live transfer only on bridge + keys + Legal gate",
    },
    {
        "id": "einvoice",
        "title": "e-Invoice (IRN)",
        "why": "NIC filing needs GSP — local IRN is ops-ready watermark.",
        "native": {"id": "local_irn", "label": "Kanha local DEMO-IRN"},
        "bridge": {"id": "gsp", "label": "GSP / NIC bridge"},
        "modes": ["native", "bridge", "hybrid"],
        "default_mode": "hybrid",
        "live_flag": "gsp_live",
        "edge": "Generate always; live push when GSP + Legal gate",
    },
    {
        "id": "eway",
        "title": "e-Way bill",
        "why": "Same as IRN — local register + optional GSP push.",
        "native": {"id": "local_ewb", "label": "Kanha local DEMO-EWB"},
        "bridge": {"id": "gsp_eway", "label": "GSP e-Way bridge"},
        "modes": ["native", "bridge", "hybrid"],
        "default_mode": "hybrid",
        "live_flag": "gsp_live",
        "edge": "Challan linked always; NIC live optional",
    },
    {
        "id": "whatsapp",
        "title": "WhatsApp OS",
        "why": "Meta Cloud for live; demo adapter keeps full OS process.",
        "native": {"id": "demo_wa", "label": "Kanha demo WhatsApp (sent + wamid)"},
        "bridge": {"id": "meta", "label": "Meta Cloud bridge"},
        "modes": ["native", "bridge", "hybrid"],
        "default_mode": "hybrid",
        "live_flag": "whatsapp_live",
        "edge": "ORDER/YES/NO/PAY flows always; Meta when token set",
    },
    {
        "id": "email",
        "title": "Email reminders",
        "why": "SMTP delivers; without keys we still queue outbox.",
        "native": {"id": "demo_email", "label": "Kanha email outbox (demo-sent)"},
        "bridge": {"id": "smtp", "label": "SMTP bridge"},
        "modes": ["native", "bridge", "hybrid"],
        "default_mode": "hybrid",
        "live_flag": "smtp_live",
        "edge": "Overdue automation always writes CommsMessage",
    },
    {
        "id": "maps",
        "title": "Maps / field plot",
        "why": "Phone GPS is enough for tracking; tiles optional.",
        "native": {"id": "phone_gps", "label": "Phone GPS + Kanha track map"},
        "bridge": {"id": "map_tiles", "label": "Google / Mapbox tiles bridge"},
        "modes": ["native", "bridge", "hybrid"],
        "default_mode": "native",
        "live_flag": "maps_live",
        "edge": "Realtime ping never blocked by Maps key",
    },
    {
        "id": "ai",
        "title": "AI assistant",
        "why": "Demo AI on ERP data; cloud LLM when keyed.",
        "native": {"id": "demo_ai", "label": "Kanha Demo AI (ERP brain)"},
        "bridge": {"id": "llm", "label": "OpenAI / LLM bridge"},
        "modes": ["native", "bridge", "hybrid"],
        "default_mode": "hybrid",
        "live_flag": "llm_live",
        "edge": "Always answers from company data; LLM upgrades tone",
    },
]


def _live_ok(flag: str | None) -> bool:
    if not flag:
        return False
    return bool(getattr(settings, flag, False))


def default_bridges_state() -> dict[str, Any]:
    out = {}
    for ch in BRIDGE_CHANNELS:
        out[ch["id"]] = {
            "mode": ch["default_mode"],
            "native": ch["native"]["id"],
            "bridge": ch["bridge"]["id"],
            "enabled": True,
            "updated_at": None,
        }
    return out


def get_bridges(db: Session, company_id: int) -> dict[str, Any]:
    co = db.get(Company, company_id)
    sj = dict((co.settings_json if co else None) or {})
    saved = dict(sj.get("bridges") or {})
    base = default_bridges_state()
    for k, v in saved.items():
        if k in base and isinstance(v, dict):
            base[k] = {**base[k], **v}
    return base


def get_outbox(db: Session, company_id: int) -> list[dict[str, Any]]:
    co = db.get(Company, company_id)
    sj = dict((co.settings_json if co else None) or {})
    rows = list(sj.get("bridge_outbox") or [])
    return rows[-100:]


def _save_sj(db: Session, company_id: int, mutator) -> dict[str, Any]:
    co = db.get(Company, company_id)
    if not co:
        raise ValueError("Company not found")
    sj = dict(co.settings_json or {})
    mutator(sj)
    co.settings_json = sj
    db.add(co)
    db.commit()
    db.refresh(co)
    return sj


def set_bridge_mode(
    db: Session,
    company_id: int,
    channel_id: str,
    mode: str,
    *,
    updated_by: str = "",
) -> dict[str, Any]:
    ch = next((x for x in BRIDGE_CHANNELS if x["id"] == channel_id), None)
    if not ch:
        raise ValueError(f"Unknown channel {channel_id}")
    if mode not in ch["modes"]:
        raise ValueError(f"Mode must be one of {ch['modes']}")

    def mut(sj: dict) -> None:
        bridges = dict(sj.get("bridges") or default_bridges_state())
        cur = dict(bridges.get(channel_id) or {})
        cur.update(
            {
                "mode": mode,
                "native": ch["native"]["id"],
                "bridge": ch["bridge"]["id"],
                "enabled": True,
                "updated_at": datetime.utcnow().isoformat() + "Z",
                "updated_by": updated_by,
            }
        )
        bridges[channel_id] = cur
        sj["bridges"] = bridges

    _save_sj(db, company_id, mut)
    return get_bridges(db, company_id)[channel_id]


def channel_mode(db: Session, company_id: int, channel_id: str) -> str:
    st = get_bridges(db, company_id).get(channel_id) or {}
    return str(st.get("mode") or "native")


def uses_bridge(db: Session, company_id: int, channel_id: str) -> bool:
    return channel_mode(db, company_id, channel_id) in ("bridge", "hybrid")


def enqueue(
    db: Session,
    company_id: int,
    *,
    channel: str,
    action: str,
    payload: dict[str, Any],
    title: str = "",
) -> dict[str, Any]:
    job = {
        "id": f"bj-{int(datetime.utcnow().timestamp() * 1000)}",
        "channel": channel,
        "action": action,
        "title": title or f"{channel}:{action}",
        "status": "queued",
        "payload": payload,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "result": None,
    }

    def mut(sj: dict) -> None:
        box = list(sj.get("bridge_outbox") or [])
        box.append(job)
        sj["bridge_outbox"] = box[-200:]

    _save_sj(db, company_id, mut)
    return job


def mark_outbox(db: Session, company_id: int, job_id: str, status: str, result: dict | None = None) -> dict | None:
    found = {"job": None}

    def mut(sj: dict) -> None:
        box = list(sj.get("bridge_outbox") or [])
        for i, j in enumerate(box):
            if j.get("id") == job_id:
                j = dict(j)
                j["status"] = status
                j["result"] = result or {}
                j["updated_at"] = datetime.utcnow().isoformat() + "Z"
                box[i] = j
                found["job"] = j
                break
        sj["bridge_outbox"] = box

    _save_sj(db, company_id, mut)
    return found["job"]


def build_erp_pack(db: Session, company_id: int, target: str = "tally") -> dict[str, Any]:
    """Unified ERP data pack — Tally / Marg / Busy / Vyapar / Other. Same Kanha source data."""
    tid = (target or "tally").strip().lower()
    meta = next((t for t in ERP_DATA_TARGETS if t["id"] == tid), None)
    if not meta:
        raise ValueError(f"Unknown ERP target {target}. Use: {[t['id'] for t in ERP_DATA_TARGETS]}")

    customers = db.query(Customer).filter(Customer.company_id == company_id).limit(300).all()
    vendors = db.query(Vendor).filter(Vendor.company_id == company_id).limit(300).all()
    products = db.query(Product).filter(Product.company_id == company_id).limit(400).all()
    invs = db.query(Invoice).filter(Invoice.company_id == company_id).order_by(Invoice.id.desc()).limit(150).all()
    journals = (
        db.query(JournalEntry)
        .filter(JournalEntry.company_id == company_id)
        .order_by(JournalEntry.id.desc())
        .limit(150)
        .all()
    )
    pack: dict[str, Any] = {
        "ok": True,
        "target": tid,
        "target_label": meta["label"],
        "format": meta["format"],
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "mode_hint": channel_mode(db, company_id, "accounting"),
        "ledgers": {
            "customers": [
                {
                    "name": c.name,
                    "gstin": getattr(c, "gstin", "") or "",
                    "code": c.code,
                    "phone": getattr(c, "phone", "") or "",
                }
                for c in customers
            ],
            "vendors": [
                {
                    "name": v.name,
                    "gstin": getattr(v, "gstin", "") or "",
                    "code": v.code,
                    "phone": getattr(v, "phone", "") or "",
                }
                for v in vendors
            ],
        },
        "items": [
            {
                "sku": (getattr(p, "sku", None) or getattr(p, "code", "") or ""),
                "code": (getattr(p, "code", None) or getattr(p, "sku", "") or ""),
                "name": p.name,
                "uom": getattr(p, "uom", "") or "NOS",
                "sale_price": float(getattr(p, "sale_price", 0) or 0),
                "cost_price": float(getattr(p, "cost_price", 0) or 0),
                "hsn": getattr(p, "hsn", "") or "",
                "gst_rate": float(getattr(p, "gst_rate", 0) or 0),
            }
            for p in products
        ],
        "vouchers": [
            {
                "number": i.number,
                "date": i.invoice_date.isoformat() if i.invoice_date else None,
                "party": "",
                "total": i.total,
                "tax": i.tax,
                "paid": i.paid,
                "status": i.status,
                "type": "sales",
                "lines": i.lines or [],
            }
            for i in invs
        ],
        "journal_vouchers": [
            {
                "number": j.number,
                "date": j.entry_date.isoformat() if j.entry_date else None,
                "voucher_type": getattr(j, "voucher_type", "journal") or "journal",
                "party_name": getattr(j, "party_name", "") or "",
                "narration": j.narration,
                "lines": j.lines or [],
                "status": j.status,
            }
            for j in journals
        ],
        "counts": {
            "customers": len(customers),
            "vendors": len(vendors),
            "items": len(products),
            "vouchers": len(invs),
            "journals": len(journals),
        },
        "note": (
            f"{meta['label']} data pack from Kanha. "
            f"{meta['hint']} Hybrid = Kanha Books stays ops source; pack is handoff only. "
            "No client legacy DB import — fresh Kanha data only."
        ),
        "hook_hint": {
            "preset": tid if tid in ("marg", "busy", "vyapar") else "custom",
            "events": meta.get("events") or [],
        },
    }
    return pack


def build_tally_pack(db: Session, company_id: int) -> dict[str, Any]:
    """Kept for existing Tally callers — same pack via unified ERP builder."""
    return build_erp_pack(db, company_id, "tally")


def list_erp_targets() -> list[dict[str, Any]]:
    return list(ERP_DATA_TARGETS)


def catalog_with_status(db: Session, company_id: int) -> dict[str, Any]:
    state = get_bridges(db, company_id)
    channels = []
    for ch in BRIDGE_CHANNELS:
        st = state.get(ch["id"]) or {}
        flag = ch.get("live_flag")
        live = _live_ok(flag) if flag else False
        mode = st.get("mode") or ch["default_mode"]
        channels.append(
            {
                **ch,
                "mode": mode,
                "state": st,
                "connectivity": {
                    "keys_live": live,
                    "flag": flag,
                    "status_label": (
                        "LIVE keys"
                        if live
                        else ("Bridge ready (demo process)" if mode in ("bridge", "hybrid") else "Native only")
                    ),
                },
            }
        )
    outbox = list(reversed(get_outbox(db, company_id)))[:40]
    from app.services import connectors as cx

    hooks = cx.list_hooks(db, company_id)
    out: dict[str, Any] = {
        "ok": True,
        "channels": channels,
        "outbox": outbox,
        "erp_targets": list_erp_targets(),
        "tally_sync": tally_sync_desk(db, company_id),
        "hooks": {
            "presets": cx.list_presets(),
            "items": [
                {
                    **{k: v for k, v in h.items() if k != "inbound_token"},
                    "token_fingerprint": cx.fingerprint_token(h.get("inbound_token") or ""),
                    "inbound_path": cx.public_inbound_path(h["id"]),
                    "has_token": bool(h.get("inbound_token")),
                }
                for h in hooks
            ],
            "inbox": cx.inbox(db, company_id)[:20],
            "log": cx.activity_log(db, company_id)[:30],
            "active": sum(1 for h in hooks if h.get("status") == "active"),
        },
        "intelligence": None,
        "summary": {
            "native": sum(1 for c in channels if c["mode"] == "native"),
            "bridge": sum(1 for c in channels if c["mode"] == "bridge"),
            "hybrid": sum(1 for c in channels if c["mode"] == "hybrid"),
            "queued": sum(1 for j in outbox if j.get("status") == "queued"),
            "hooks_active": sum(1 for h in hooks if h.get("status") == "active"),
        },
        "pitch": "KanhaERP runs the business. Link Tally (kept) + Marg / Busy / Vyapar / Other ERP data packs + Razorpay/GSP/hooks. Bridge Intelligence learns gaps.",
    }
    try:
        from app.services.bridge_intelligence import get_state as intel_state

        out["intelligence"] = intel_state(db, company_id)
        out["summary"]["trust_score"] = out["intelligence"].get("trust_score")
    except Exception:
        pass
    return out


def maybe_queue_tally_sales(db: Session, company_id: int, invoice: Invoice) -> dict | None:
    if not uses_bridge(db, company_id, "accounting"):
        return None
    cust = db.get(Customer, invoice.customer_id) if invoice.customer_id else None
    return enqueue(
        db,
        company_id,
        channel="accounting",
        action="tally_sales_voucher",
        title=f"Tally ← {invoice.number}",
        payload={
            "invoice_id": invoice.id,
            "number": invoice.number,
            "total": invoice.total,
            "tax": invoice.tax,
            "party": cust.name if cust else "",
            "gstin": cust.gstin if cust else "",
            "date": invoice.invoice_date.isoformat() if invoice.invoice_date else None,
            "lines": invoice.lines or [],
        },
    )


# ── SBAC Tally desk (Parent mapping · Inactive · Errors) ─────────────────────

TALLY_ERP_PARENTS: list[str] = [
    "Agent/Salesman A/C",
    "Bank Accounts",
    "Bank OCC A/c",
    "Bank OD A/c",
    "Branch / Divisions",
    "Capital Account",
    "Cash-in-hand",
    "Current Liabilities",
    "Deposits (Asset)",
    "Direct Expence",
    "Direct Incomes(SALE)",
    "DUTIES and TAXES",
    "EMPLOYEE",
    "Employee A/c",
    "Expenses (Direct)",
    "Expenses (Indirect)",
    "Fixed Assets",
    "Freight Outward",
    "Income (Direct)",
    "Income (Indirect)",
    "Indirect Expenses",
    "Investments",
    "Loans & Advances (Asset)",
    "Loans (Liability)",
    "Misc. Expenses (ASSET)",
    "Provisions",
    "Purchase Accounts",
    "Reserves & Surplus",
    "Sales Accounts",
    "Secured Loans",
    "Stock-in-hand",
    "Sundry Creditors",
    "Sundry Debtors",
    "Suspense A/c",
    "Unsecured Loans",
]


def _tally_sync(db: Session, company_id: int) -> dict[str, Any]:
    co = db.get(Company, company_id)
    sj = dict((co.settings_json if co else None) or {})
    ts = dict(sj.get("tally_sync") or {})
    return {
        "parent_mappings": list(ts.get("parent_mappings") or []),
        "inactive_ledgers": list(ts.get("inactive_ledgers") or []),
        "inactive_items": list(ts.get("inactive_items") or []),
        "errors": list(ts.get("errors") or []),
        "erp_parents": list(TALLY_ERP_PARENTS),
    }


def _save_tally_sync(db: Session, company_id: int, mutator) -> dict[str, Any]:
    def mut(sj: dict) -> None:
        ts = dict(sj.get("tally_sync") or {})
        mutator(ts)
        sj["tally_sync"] = ts

    _save_sj(db, company_id, mut)
    return _tally_sync(db, company_id)


def tally_sync_desk(db: Session, company_id: int) -> dict[str, Any]:
    """SBAC Tally Erp Parent Mapping + Inactive + Error queue snapshot."""
    data = _tally_sync(db, company_id)
    outbox = get_outbox(db, company_id)
    bridge_errors = [
        j
        for j in outbox
        if (j.get("status") or "").lower() in ("error", "failed", "rejected")
        or "error" in str(j.get("action") or "").lower()
        or "tally" in str(j.get("action") or "").lower()
        and (j.get("status") or "").lower() not in ("exported", "imported", "synced")
    ]
    # Prefer explicit tally_sync.errors; fall back to outbox issues
    errors = list(data["errors"])
    if not errors:
        for j in reversed(outbox):
            st = (j.get("status") or "").lower()
            if st in ("error", "failed", "rejected") or (
                "tally" in str(j.get("action") or "").lower() and st == "queued"
            ):
                errors.append(
                    {
                        "id": j.get("id"),
                        "at": j.get("created_at") or j.get("updated_at"),
                        "doc_type": (j.get("payload") or {}).get("doc_type")
                        or str(j.get("action") or "").replace("tally_", "").title(),
                        "message": j.get("title") or j.get("status"),
                        "ref": (j.get("payload") or {}).get("number") or j.get("id"),
                        "status": j.get("status"),
                        "source": "outbox",
                    }
                )
    return {
        **data,
        "errors": errors[-80:],
        "bridge_error_hint": len(bridge_errors),
        "counts": {
            "mappings": len(data["parent_mappings"]),
            "inactive_ledgers": len(data["inactive_ledgers"]),
            "inactive_items": len(data["inactive_items"]),
            "errors": len(errors),
        },
    }


def upsert_parent_mapping(db: Session, company_id: int, *, erp_parent: str, tally_name: str) -> dict[str, Any]:
    erp_parent = (erp_parent or "").strip()
    tally_name = (tally_name or "").strip()
    if not erp_parent or not tally_name:
        raise ValueError("ERP parent and Tally name required")

    def mut(ts: dict) -> None:
        rows = list(ts.get("parent_mappings") or [])
        found = False
        for r in rows:
            if str(r.get("erp_parent") or "").lower() == erp_parent.lower():
                r["tally_name"] = tally_name
                r["updated_at"] = datetime.utcnow().isoformat() + "Z"
                found = True
                break
        if not found:
            rows.append(
                {
                    "id": f"tpm-{len(rows)+1}-{int(datetime.utcnow().timestamp())}",
                    "erp_parent": erp_parent,
                    "tally_name": tally_name,
                    "created_at": datetime.utcnow().isoformat() + "Z",
                }
            )
        ts["parent_mappings"] = rows

    return _save_tally_sync(db, company_id, mut)


def set_inactive_ledger(db: Session, company_id: int, *, name: str, code: str = "", inactive: bool = True) -> dict[str, Any]:
    name = (name or "").strip()
    code = (code or "").strip().upper()
    if not name and not code:
        raise ValueError("Party / ledger name or code required")

    def mut(ts: dict) -> None:
        rows = list(ts.get("inactive_ledgers") or [])
        key = (code or name).lower()
        rows = [r for r in rows if (str(r.get("code") or r.get("name") or "").lower()) != key]
        if inactive:
            rows.append(
                {
                    "name": name or code,
                    "code": code,
                    "inactive": True,
                    "inactive_at": datetime.utcnow().isoformat() + "Z",
                }
            )
        ts["inactive_ledgers"] = rows

    data = _save_tally_sync(db, company_id, mut)
    # Flag Account.custom if code matches COA
    if code:
        from app.models import Account

        acc = db.query(Account).filter(Account.company_id == company_id, Account.code == code).first()
        if acc:
            cust = dict(acc.custom or {})
            cust["tally_inactive"] = bool(inactive)
            acc.custom = cust
            try:
                from sqlalchemy.orm.attributes import flag_modified

                flag_modified(acc, "custom")
            except Exception:
                pass
            db.commit()
    return data


def set_inactive_item(db: Session, company_id: int, *, name: str, sku: str = "", inactive: bool = True) -> dict[str, Any]:
    name = (name or "").strip()
    sku = (sku or "").strip().upper()
    if not name and not sku:
        raise ValueError("Item name or SKU required")

    def mut(ts: dict) -> None:
        rows = list(ts.get("inactive_items") or [])
        key = (sku or name).lower()
        rows = [r for r in rows if (str(r.get("sku") or r.get("name") or "").lower()) != key]
        if inactive:
            rows.append(
                {
                    "name": name or sku,
                    "sku": sku,
                    "inactive": True,
                    "inactive_at": datetime.utcnow().isoformat() + "Z",
                }
            )
        ts["inactive_items"] = rows

    data = _save_tally_sync(db, company_id, mut)
    if sku:
        prod = db.query(Product).filter(Product.company_id == company_id, Product.sku == sku).first()
        if prod:
            cust = dict(getattr(prod, "custom", None) or {})
            cust["tally_inactive"] = bool(inactive)
            prod.custom = cust
            try:
                from sqlalchemy.orm.attributes import flag_modified

                flag_modified(prod, "custom")
            except Exception:
                pass
            db.commit()
    return data


def log_tally_error(
    db: Session,
    company_id: int,
    *,
    doc_type: str,
    message: str,
    ref: str = "",
    from_date: str = "",
    to_date: str = "",
) -> dict[str, Any]:
    doc_type = (doc_type or "Sale").strip()
    message = (message or "").strip() or "Tally sync error"

    def mut(ts: dict) -> None:
        rows = list(ts.get("errors") or [])
        rows.append(
            {
                "id": f"terr-{len(rows)+1}-{int(datetime.utcnow().timestamp())}",
                "at": datetime.utcnow().isoformat() + "Z",
                "doc_type": doc_type,
                "message": message,
                "ref": ref,
                "from_date": from_date,
                "to_date": to_date,
                "status": "open",
                "source": "manual",
            }
        )
        ts["errors"] = rows[-200:]

    return _save_tally_sync(db, company_id, mut)


def filter_tally_errors(
    db: Session,
    company_id: int,
    *,
    from_date: str = "",
    to_date: str = "",
    doc_type: str = "",
) -> list[dict[str, Any]]:
    desk = tally_sync_desk(db, company_id)
    rows = list(desk.get("errors") or [])
    dt = (doc_type or "").strip().lower()
    if dt and dt not in ("--select--", "all", ""):
        rows = [r for r in rows if str(r.get("doc_type") or "").lower().startswith(dt[:4]) or dt in str(r.get("doc_type") or "").lower()]
    # Date filter on `at` / from_date fields when present
    if from_date:
        rows = [r for r in rows if str(r.get("at") or r.get("from_date") or "")[:10] >= from_date[:10]]
    if to_date:
        rows = [r for r in rows if str(r.get("at") or r.get("to_date") or r.get("from_date") or "")[:10] <= to_date[:10]]
    return rows
