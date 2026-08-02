"""
KanhaERP Demo AI — complete ERP knowledge on live data.
No personal details: no customer names, phones, emails, or user credentials in replies.
When LLM_API_KEY is set, integrations_llm takes over with the same privacy rules.
"""
from __future__ import annotations

import json
from datetime import date
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.modules import ALL_MODULES, gst_split
from app.models import (
    Customer,
    Delivery,
    Invoice,
    JournalEntry,
    Lead,
    Opportunity,
    Product,
    PurchaseInvoice,
    PurchaseOrder,
    Quotation,
    SalesOrder,
    ServiceTicket,
    StockBalance,
    Vendor,
    WorkOrder,
)


def _money(n: float) -> str:
    return f"₹{float(n or 0):,.0f}"


def _doc_ref(entity: str, doc_id: int | None) -> str:
    return f"{entity}#{doc_id}" if doc_id else entity


def erp_module_guide() -> list[dict[str, str]]:
    """Static A–Z module map — what each area does and how to navigate."""
    flows = {
        "dashboard": "KPIs · approvals pending · open orders · revenue snapshot",
        "crm": "Lead → Opportunity → Quotation · follow-up via WhatsApp templates",
        "dealers": "Dealer portal orders · pricing lists · channel credit",
        "sales": "Quote → SO (≥₹5L needs approval) → Delivery → Invoice → Payment · Credit note/return",
        "pos": "Barcode scan billing · instant invoice · cash/UPI",
        "rfid": "EPC bind · warehouse location · RFID stock moves",
        "purchase": "Vendor → PO → GRN → Purchase Invoice → Vendor payment",
        "inventory": "Products · stock adjust · WH transfer · batches · labels",
        "logistics": "Packing · dispatch · e-Invoice IRN · e-Way bill",
        "accounting": "COA · journals · P&L · GST register · trial balance · period lock",
        "manufacturing": "BOM → Work order · machines · MRP shortage plan",
        "quality": "Inspections · NC reports · CAPA",
        "hrms": "Attendance · leave approve · expense claims · payroll · GPS field",
        "projects": "Delivery projects · kanban tasks todo/doing/done",
        "service": "AMC tickets · start/resolve/close · field visits",
        "documents": "Upload files (local) · link to entities",
        "reports": "Run seeded report codes · output below",
        "bi": "Revenue trend · ABC analysis · forecast",
        "ai": "Full chat · purchase suggest · WhatsApp draft",
        "agents": "Cash chase · Stock reorder PO · Compliance IRN/e-Way fix",
        "whatsapp": "Templates · send · inbound simulate · approval YES/NO",
        "compliance": "GST scan · e-Invoice health · e-Way register",
        "ha": "Blackout freeze · portable pack · auto-config · replica sync",
        "watch": "Live monitor sites · cameras · team chat",
        "automation": "Rules · WA hub · scheduled jobs",
        "settings": "Brand · modules · users · roles · go-live checklist · backup",
    }
    return [
        {"id": k, "name": v["name"], "flow": flows.get(k, ""), "href": f"#/{k}"}
        for k, v in ALL_MODULES.items()
    ]


def build_erp_context(db: Session, company_id: int) -> dict[str, Any]:
    sales_inv = (
        db.query(Invoice)
        .filter(Invoice.company_id == company_id, (Invoice.invoice_type == None) | (Invoice.invoice_type != "credit"))  # noqa: E711
        .all()
    )
    revenue = sum(i.total for i in sales_inv)
    outstanding = sum(max(0, i.total - i.paid) for i in sales_inv)
    stock_val = (
        db.query(func.coalesce(func.sum(StockBalance.qty * StockBalance.avg_cost), 0))
        .filter(StockBalance.company_id == company_id)
        .scalar()
        or 0
    )
    overdue = [
        i
        for i in sales_inv
        if (i.total - i.paid) > 1 and i.due_date and i.due_date < date.today()
    ]
    low: list[dict] = []
    for bal in db.query(StockBalance).filter(StockBalance.company_id == company_id).all():
        p = db.get(Product, bal.product_id)
        if not p:
            continue
        point = float((p.custom or {}).get("reorder_point", 50))
        if bal.qty < point:
            low.append({"sku": p.sku, "name": p.name, "qty": bal.qty, "point": point})
    pending_so = (
        db.query(SalesOrder)
        .filter(
            SalesOrder.company_id == company_id,
            SalesOrder.approval_status == "pending",
        )
        .count()
    )
    open_po = (
        db.query(PurchaseOrder)
        .filter(PurchaseOrder.company_id == company_id, PurchaseOrder.status != "received")
        .count()
    )
    pi_open = sum(
        max(0, (pi.total or 0) - (pi.paid or 0))
        for pi in db.query(PurchaseInvoice).filter(PurchaseInvoice.company_id == company_id).all()
    )
    result = {
        "revenue": float(revenue),
        "outstanding": float(outstanding),
        "inventory_value": float(stock_val),
        "leads": db.query(Lead).filter(Lead.company_id == company_id).count(),
        "open_quotes": db.query(Quotation).filter(
            Quotation.company_id == company_id, Quotation.status != "accepted"
        ).count(),
        "open_orders": db.query(SalesOrder).filter(
            SalesOrder.company_id == company_id, SalesOrder.status != "invoiced"
        ).count(),
        "pending_approvals": pending_so,
        "open_tickets": db.query(ServiceTicket).filter(
            ServiceTicket.company_id == company_id,
            ServiceTicket.status.in_(["open", "in_progress"]),
        ).count(),
        "vendors": db.query(Vendor).filter(Vendor.company_id == company_id).count(),
        "open_pos": open_po,
        "payables": float(pi_open),
        "work_orders": db.query(WorkOrder).filter(WorkOrder.company_id == company_id).count(),
        "deliveries": db.query(Delivery).filter(Delivery.company_id == company_id).count(),
        "journals": db.query(JournalEntry).filter(JournalEntry.company_id == company_id).count(),
        "overdue_count": len(overdue),
        "overdue_amount": sum(i.total - i.paid for i in overdue),
        "low_stock": low[:10],
        "top_overdue": [
            {"number": i.number, "balance": round(i.total - i.paid, 2), "customer_ref": _doc_ref("cust", i.customer_id)}
            for i in overdue[:5]
        ],
        "bridge_intelligence": None,
    }
    try:
        from app.services.bridge_intelligence import get_state as intel_state

        ist = intel_state(db, company_id)
        result["bridge_intelligence"] = {
            "trust_score": ist.get("trust_score"),
            "last_accuracy": ist.get("last_accuracy"),
            "runs": ist.get("runs"),
            "open_gaps": len(ist.get("open_gaps") or []),
            "improvements_applied": ist.get("improvements_applied"),
        }
    except Exception:
        pass
    return result


def build_llm_context(db: Session, company_id: int, query: str = "") -> str:
    """Rich context for live LLM — aggregates + module map + taught memory, zero PII."""
    ctx = build_erp_context(db, company_id)
    modules = erp_module_guide()
    payload = {
        "brand": settings.app_name or "KanhaERP",
        "privacy": "Never reveal customer names, phone numbers, emails, passwords, or employee personal data.",
        "kpis": {
            "revenue": ctx["revenue"],
            "outstanding": ctx["outstanding"],
            "inventory_value": ctx["inventory_value"],
            "pending_approvals": ctx["pending_approvals"],
            "payables": ctx["payables"],
            "overdue_count": ctx["overdue_count"],
        },
        "modules": [{m["id"]: m["flow"]} for m in modules[:12]],
        "low_stock_skus": [x["sku"] for x in ctx["low_stock"][:5]],
        "navigation": "Use #/module paths e.g. #/sales #/purchase #/accounting #/whatsapp",
    }
    base = json.dumps(payload, ensure_ascii=False)[:2800]
    try:
        from app.services.ai_memory import memory_context_block

        mem = memory_context_block(db, company_id, query or "", limit=4)
        if mem:
            return (base + "\n\n" + mem)[:6500]
    except Exception:
        pass
    return base


def _suggestions() -> list[str]:
    return [
        "ERP modules guide",
        "Outstanding receivables",
        "Kya seekha hai memory me?",
        "Low stock reorder",
        "GST register summary",
        "Draft WhatsApp overdue chase",
        "Yaad rakh: payment terms Net 30",
        "How to credit note",
        "Period lock books",
        "Run Kanha Agents",
    ]


def demo_ai_reply(db: Session, company_id: int, message: str) -> dict[str, Any]:
    ctx = build_erp_context(db, company_id)
    msg = (message or "").strip().lower()
    brand = settings.app_name or "KanhaERP"
    suggestions = _suggestions()

    if msg == "__suggestions__":
        return {"suggestions": suggestions}

    def ok(reply: str, **extra):
        return {
            "reply": reply,
            "live": False,
            "mode": "demo_ai",
            "provider": "kanha_erp_brain",
            "note": "Kanha Core AI — full ERP knowledge, no personal details shared.",
            "suggestions": suggestions,
            "context": {
                "revenue": ctx["revenue"],
                "outstanding": ctx["outstanding"],
                "inventory_value": ctx["inventory_value"],
                "pending_approvals": ctx["pending_approvals"],
            },
            **extra,
        }

    # Teach command: "yaad rakh: ..." / "learn: ..."
    try:
        from app.services.ai_memory import answer_from_memory, learn_text, try_parse_teach_command

        teach = try_parse_teach_command(message or "")
        if teach:
            title, body = teach
            r = learn_text(db, company_id, body, title=title)
            return ok(r["message"] + "\n\nPreview: " + (r.get("item") or {}).get("preview", "")[:180], learned=True)

        ask_memory = any(
            k in msg
            for k in (
                "yaad",
                "memory",
                "seekha",
                "seekh",
                "learned",
                "what did you learn",
                "kya seekha",
                "kya yaad",
                "tumhe kya",
                "jo maine sikhaya",
                "taught",
                "policy",
                "sop",
            )
        )
        if ask_memory:
            mem_ans = answer_from_memory(db, company_id, message or "")
            if mem_ans:
                return ok(mem_ans["reply"], from_memory=True, memory_hits=mem_ans.get("hits"))
    except Exception:
        pass

    # Module guide / navigation
    if any(k in msg for k in ("module", "menu", "guide", "kya kya", "features", "erp modules", "a to z", "atoz")):
        lines = [f"• **{m['name']}** (`{m['href']}`) — {m['flow']}" for m in erp_module_guide()]
        return ok(
            f"{brand} — complete module map:\n" + "\n".join(lines[:14])
            + "\n… aur bhi modules sidebar me. Kisi bhi module ka flow poochho.",
            action={"type": "open", "href": "#/dashboard"},
        )

    # Bridge intelligence / trust growth
    if any(
        k in msg
        for k in (
            "bridge intelligence",
            "trust score",
            "parity",
            "cross check",
            "cross-check",
            "learn from bridge",
            "hook learn",
            "native trust",
            "learning phase",
            "curriculum",
            "learn full",
            "internal learning",
        )
    ):
        from app.services.bridge_intelligence import ai_brief

        return ok(
            ai_brief(db, company_id)
            + "\n9 phases: ingest→normalize→compare→score→taxonomy→safe-fix→rules→advance→retain. "
            "Goal: trust 80+ → hybrid se native standalone.",
            action={"type": "open", "href": "#/bridges"},
        )

    # Pending approvals
    if any(k in msg for k in ("approval", "approve", "pending so", "so pending")):
        pending = (
            db.query(SalesOrder)
            .filter(SalesOrder.company_id == company_id, SalesOrder.approval_status == "pending")
            .order_by(SalesOrder.id.desc())
            .limit(5)
            .all()
        )
        lines = [f"• {o.number} — {_money(o.total)} (needs manager approve)" for o in pending]
        body = "\n".join(lines) or "• Koi pending approval nahi."
        return ok(
            f"Pending SO approvals: {ctx['pending_approvals']}.\n{body}\n"
            f"Sales module → Approve button, ya WhatsApp pe YES reply.\n"
            f"≥ ₹5L SO auto-pending hota hai — invoice tab tak block.",
            action={"type": "open", "href": "#/sales"},
        )

    # WhatsApp draft (before outstanding — "overdue" contains "due")
    if any(k in msg for k in ("whatsapp", "wa ", "message", "chase", "follow-up", "followup")) or (
        "draft" in msg and any(k in msg for k in ("wa", "whatsapp", "overdue", "invoice", "chase"))
    ):
        inv = None
        for i in db.query(Invoice).filter(Invoice.company_id == company_id).order_by(Invoice.id.desc()).all():
            if (i.invoice_type or "sales") == "credit":
                continue
            if (i.total - i.paid) > 1:
                inv = i
                break
        bal = (inv.total - inv.paid) if inv else 0
        draft = (
            f"Namaste, invoice {inv.number if inv else 'INV'} pe balance {_money(bal)} pending hai. "
            f"UPI/NEFT ke liye reply PAY. — {brand}"
        )
        return ok(
            f"WhatsApp draft ready (customer contact on file — not shown here):\n\n\"{draft}\"\n\n"
            f"Send: Automation/WhatsApp OS ya dock se Send draft.",
            whatsapp_draft={
                "to_name": "Customer",
                "to_phone": None,
                "body": draft,
                "template": "invoice_overdue",
                "invoice_id": inv.id if inv else None,
            },
            action={"type": "open", "href": "#/whatsapp"},
        )

    # Outstanding
    if any(k in msg for k in ("outstanding", "receivable", "udhaar", "pending payment", " overdue", "overdue ")):
        lines = [f"• {row['number']} — {row['customer_ref']}: {_money(row['balance'])}" for row in ctx["top_overdue"]]
        body = "\n".join(lines) or "• Koi overdue invoice nahi."
        return ok(
            f"Outstanding: {_money(ctx['outstanding'])} ({ctx['overdue_count']} overdue).\n{body}\n"
            f"Action: Cash Agent, WhatsApp chase, ya Sales → Record payment.",
            action={"type": "open", "href": "#/sales"},
        )

    # Stock
    if any(k in msg for k in ("stock", "inventory", "reorder", "purchase suggest", "low stock")):
        if not ctx["low_stock"]:
            return ok(
                f"Inventory {_money(ctx['inventory_value'])} — sab SKUs reorder point ke upar.",
                action={"type": "open", "href": "#/inventory"},
            )
        lines = [f"• {x['sku']} {x['name']}: on-hand {x['qty']} (point {x['point']})" for x in ctx["low_stock"]]
        return ok(
            f"Inventory {_money(ctx['inventory_value'])}. Low stock ({len(ctx['low_stock'])}):\n"
            + "\n".join(lines)
            + "\nStock Agent → draft PO · Purchase module → GRN → vendor pay.",
            action={"type": "open", "href": "#/purchase"},
        )

    # Purchase / payables
    if any(k in msg for k in ("purchase", "vendor", "payable", "grn", "po ", "supplier")):
        return ok(
            f"Purchase loop: Vendor → PO ({ctx['open_pos']} open) → GRN → PI → Vendor payment.\n"
            f"Open payables ≈ {_money(ctx['payables'])} · {ctx['vendors']} vendors.\n"
            f"Purchase module → Pay vendor on open PI.",
            action={"type": "open", "href": "#/purchase"},
        )

    # Credit note
    if any(k in msg for k in ("credit note", "credit note", "return", "sales return", "cn ")):
        return ok(
            "Credit note flow:\n"
            "1. Sales → open invoice with balance\n"
            "2. Credit note / return → amount + reason\n"
            "3. Optional stock return + GL reverse\n"
            "Period lock closed month me block karta hai.",
            action={"type": "open", "href": "#/sales"},
        )

    # Accounting / period lock
    if any(k in msg for k in ("accounting", "journal", "books", "period lock", "close books", "trial balance", "pnl", "p&l")):
        from app.services.period_lock import period_status

        pl = period_status(db, company_id)
        closed = pl.get("closed_through") or "open"
        return ok(
            f"Accounting: {ctx['journals']} journals posted.\n"
            f"Period lock: {closed}.\n"
            f"Flows: COA · balanced JV · P&L · trial balance · GST register · vendor/customer payments.\n"
            f"Closed month me naye posts block (HTTP 423).",
            action={"type": "open", "href": "#/accounting"},
        )

    # GST
    if "gst" in msg or ("tax" in msg and "payroll" not in msg):
        sales = db.query(Invoice).filter(Invoice.company_id == company_id).all()
        purchases = db.query(PurchaseInvoice).filter(PurchaseInvoice.company_id == company_id).all()
        output = sum(i.tax for i in sales if (i.invoice_type or "sales") != "credit")
        input_t = sum(i.tax for i in purchases)
        split_out = gst_split(sum(i.subtotal for i in sales if (i.invoice_type or "sales") != "credit"), 18)
        return ok(
            f"GST register summary:\n"
            f"• Output GST {_money(output)} (CGST {_money(split_out['cgst'])} + SGST {_money(split_out['sgst'])})\n"
            f"• Input ITC {_money(input_t)}\n"
            f"• Net payable {_money(output - input_t)}\n"
            f"Accounting → GST KPI · Compliance → e-Invoice/e-Way · live GSP keys for filing.",
            action={"type": "open", "href": "#/accounting"},
        )

    # Sales / revenue
    if any(k in msg for k in ("sales", "revenue", "turnover", "invoice flow", "quote")):
        return ok(
            f"Sales: Revenue {_money(ctx['revenue'])} · open SOs {ctx['open_orders']} · quotes {ctx['open_quotes']}.\n"
            f"Flow: CRM Quote → SO (approval if ≥₹5L) → Delivery+Invoice → Payment/Credit note.\n"
            f"Deliveries posted: {ctx['deliveries']}.",
            action={"type": "open", "href": "#/sales"},
        )

    # CRM
    if any(k in msg for k in ("lead", "pipeline", "crm", "opportunity", "forecast")):
        opps = db.query(Opportunity).filter(Opportunity.company_id == company_id).all()
        weighted = sum((o.amount or 0) * (o.probability or 0) / 100 for o in opps)
        return ok(
            f"CRM: {ctx['leads']} leads · {len(opps)} opportunities · weighted pipeline {_money(weighted)}.\n"
            f"Open quotes: {ctx['open_quotes']}. WA lead_followup template Automation me.",
            action={"type": "open", "href": "#/crm"},
        )

    # Agents
    if any(k in msg for k in ("agent", "cash agent", "stock agent", "compliance agent", "run agent")):
        return ok(
            "Kanha Agents (3):\n"
            "• **Cash** — overdue invoices → WhatsApp chase\n"
            "• **Stock** — low SKU → draft PO\n"
            "• **Compliance** — IRN/e-Way health fix\n"
            "Agents module → Run all ya individual.",
            action={"type": "open", "href": "#/agents"},
        )

    # HA / blackout
    if any(k in msg for k in ("blackout", "portable", "ha ", "resilience", "replica", "failover")):
        return ok(
            "Resilience / HA:\n"
            "• BLACKOUT NOW — freeze writes · portable ERP pack download\n"
            "• RESUME LIVE — unlock\n"
            "• Auto-config LAN discovery · replica sync\n"
            "Settings → Resilience panel.",
            action={"type": "open", "href": "#/ha"},
        )

    # HR
    if any(k in msg for k in ("payroll", "salary", "hr", "leave", "attendance", "expense")):
        return ok(
            "HRMS: Attendance · Leave approve/reject · Expense claims · Payroll PF/ESIC · Bank NEFT batch.\n"
            "Field GPS simulate — HR Live Flow (#/hr-flow) end-to-end demo.",
            action={"type": "open", "href": "#/hrms"},
        )

    # Manufacturing
    if any(k in msg for k in ("manufactur", "production", "bom", "mrp", "work order")):
        return ok(
            f"Manufacturing: {ctx['work_orders']} work orders · BOM → WO → MRP shortage.\n"
            "Production module → Run MRP for purchase/WO suggestions.",
            action={"type": "open", "href": "#/manufacturing"},
        )

    # Service
    if any(k in msg for k in ("ticket", "service", "amc", "complaint")):
        return ok(
            f"Service: {ctx['open_tickets']} open tickets. Start → Resolve → Close in Service module.",
            action={"type": "open", "href": "#/service"},
        )

    # POS / RFID / Logistics shortcuts
    if any(k in msg for k in ("pos", "scan bill", "barcode")):
        return ok("Scan Billing: barcode scan → instant invoice. #/pos", action={"type": "open", "href": "#/pos"})
    if "rfid" in msg:
        return ok("RFID: EPC bind · location · stock moves. #/rfid", action={"type": "open", "href": "#/rfid"})
    if any(k in msg for k in ("dispatch", "logistics", "e-way", "einvoice", "e-invoice")):
        return ok(
            "Logistics: packing → dispatch → e-Invoice IRN → e-Way. Demo IRN local · live GSP with keys.",
            action={"type": "open", "href": "#/logistics"},
        )

    # Help
    if any(k in msg for k in ("help", "kya kar", "what can", "kaise", "how to")):
        return ok(
            f"Main {brand} Core AI — poori ERP ki operational jaankari (personal details nahi).\n\n"
            f"Poochho: modules guide · outstanding · approvals · stock · GST · purchase · credit note · "
            f"agents · blackout · HR · manufacturing · service.\n\n"
            f"Sikhane ke liye: chat me `Yaad rakh: ...` likho, ya AI page pe file/folder Teach karo — "
            f"main company memory me hamesha yaad rakhunga.\n\n"
            f"KPIs abhi: Revenue {_money(ctx['revenue'])} · Outstanding {_money(ctx['outstanding'])} · "
            f"Stock {_money(ctx['inventory_value'])} · Pending approvals {ctx['pending_approvals']}."
        )

    # If memory has a soft hit (keywords match), append a short hint
    try:
        from app.services.ai_memory import search_memory

        soft = search_memory(db, company_id, message or "", limit=2)
        if soft:
            extra_mem = "\n\n(Related taught memory: " + "; ".join(f"{s.get('title')}" for s in soft) + " — detail: “kya seekha”)"
        else:
            extra_mem = ""
    except Exception:
        extra_mem = ""

    # Default — rich operational summary
    return ok(
        f"{brand} Core AI online.\n"
        f"Revenue {_money(ctx['revenue'])} · Outstanding {_money(ctx['outstanding'])} · "
        f"Stock {_money(ctx['inventory_value'])} · Payables {_money(ctx['payables'])} · "
        f"Pending SO approvals {ctx['pending_approvals']} · Open tickets {ctx['open_tickets']}.\n"
        f"Poori module list: type **ERP modules guide**. Privacy: names/phones share nahi hote.\n"
        f"Sikhane ke liye: `Yaad rakh: ...` ya AI page pe file/folder Teach."
        + extra_mem
    )