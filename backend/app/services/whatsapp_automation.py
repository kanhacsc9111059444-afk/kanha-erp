"""WhatsApp Automation OS — templates + scheduled flows, all inside Automation."""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import (
    AutomationJob,
    CommsMessage,
    Customer,
    Invoice,
    Lead,
    Notification,
    Product,
    StockBalance,
    WhatsAppTemplate,
)

DEFAULT_TEMPLATES: list[dict[str, Any]] = [
    {
        "code": "lead_followup",
        "name": "Lead follow-up",
        "category": "crm",
        "auto_trigger": "lead_open",
        "variables": ["name", "company", "value"],
        "body": (
            "Namaste {{name}}! {{brand}} se follow-up: "
            "{{company}} (₹{{value}}) pe baat karna hai. Reply YES for demo slot."
        ),
    },
    {
        "code": "invoice_overdue",
        "name": "Overdue invoice chase",
        "category": "collection",
        "auto_trigger": "invoice_overdue",
        "variables": ["name", "number", "amount", "due_date"],
        "body": (
            "Namaste {{name}}, invoice {{number}} overdue hai — balance ₹{{amount}} "
            "(due {{due_date}}). Pay link / UPI ke liye reply PAY."
        ),
    },
    {
        "code": "payment_thanks",
        "name": "Payment thank you",
        "category": "collection",
        "auto_trigger": "payment_received",
        "variables": ["name", "amount", "number"],
        "body": "Dhanyavaad {{name}}! Payment ₹{{amount}} for {{number}} receive ho gaya. — {{brand}}",
    },
    {
        "code": "order_confirm",
        "name": "Order confirmation",
        "category": "sales",
        "auto_trigger": "order_created",
        "variables": ["name", "number", "amount"],
        "body": "Order {{number}} confirm — total ₹{{amount}}. Thanks {{name}}! Track / changes: reply HELP.",
    },
    {
        "code": "quote_followup",
        "name": "Quote follow-up",
        "category": "sales",
        "auto_trigger": "quote_open",
        "variables": ["name", "number", "amount"],
        "body": "Hi {{name}}, quote {{number}} (₹{{amount}}) review ho gaya? Reply YES to convert to order.",
    },
    {
        "code": "stock_alert",
        "name": "Low stock alert (internal)",
        "category": "ops",
        "auto_trigger": "stock_low",
        "variables": ["sku", "qty", "point"],
        "body": "⚠ Low stock: {{sku}} on-hand {{qty}} (reorder {{point}}). Draft PO automation ready.",
    },
    {
        "code": "delivery_dispatch",
        "name": "Dispatch update",
        "category": "ops",
        "auto_trigger": "dispatch",
        "variables": ["name", "number", "vehicle"],
        "body": (
            "Namaste {{name}}, aapka consignment {{number}} dispatch ho gaya"
            "{{vehicle}}. Delivery update ke liye reply STATUS."
        ),
    },
    {
        "code": "welcome_customer",
        "name": "New customer welcome",
        "category": "crm",
        "auto_trigger": "customer_created",
        "variables": ["name"],
        "body": "Welcome {{name}}! Aapka account {{brand}} pe active hai. Orders WhatsApp pe bhi: ORDER <item>.",
    },
]


def render_template(body: str, vars: dict[str, Any]) -> str:
    text = body or ""
    for k, v in (vars or {}).items():
        text = text.replace("{{" + k + "}}", str(v if v is not None else ""))
    # clean unused placeholders
    text = re.sub(r"\{\{[a-zA-Z0-9_]+\}\}", "", text)
    return text.strip()


def ensure_whatsapp_automation(db: Session, company_id: int, brand: str = "KanhaERP") -> dict:
    """Seed templates + WhatsApp automation jobs (idempotent)."""
    created_t = 0
    for t in DEFAULT_TEMPLATES:
        exists = (
            db.query(WhatsAppTemplate)
            .filter(WhatsAppTemplate.company_id == company_id, WhatsAppTemplate.code == t["code"])
            .first()
        )
        if exists:
            continue
        db.add(
            WhatsAppTemplate(
                company_id=company_id,
                code=t["code"],
                name=t["name"],
                category=t["category"],
                body=t["body"],
                variables=t["variables"],
                auto_trigger=t["auto_trigger"],
                active=True,
                meta={"brand_default": brand},
            )
        )
        created_t += 1

    jobs_spec = [
        ("WA Auto: Lead follow-up", "schedule.hourly", "whatsapp_lead_followup", {"template": "lead_followup", "limit": 10}),
        ("WA Auto: Overdue chase", "schedule.daily", "whatsapp_invoice_overdue", {"template": "invoice_overdue", "limit": 20}),
        ("WA Auto: Low stock alert", "schedule.daily", "whatsapp_stock_alert", {"template": "stock_alert", "limit": 15}),
        ("WA Auto: Quote follow-up", "schedule.daily", "whatsapp_quote_followup", {"template": "quote_followup", "limit": 10}),
    ]
    names = {j.name for j in db.query(AutomationJob).filter(AutomationJob.company_id == company_id).all()}
    created_j = 0
    for name, trigger, action, config in jobs_spec:
        if name in names:
            continue
        db.add(
            AutomationJob(
                company_id=company_id,
                name=name,
                trigger=trigger,
                action=action,
                config=config,
                active=True,
            )
        )
        created_j += 1
    db.flush()
    return {"templates": created_t, "jobs": created_j}


def get_template(db: Session, company_id: int, code: str) -> WhatsAppTemplate | None:
    return (
        db.query(WhatsAppTemplate)
        .filter(WhatsAppTemplate.company_id == company_id, WhatsAppTemplate.code == code, WhatsAppTemplate.active.is_(True))
        .first()
    )


def list_templates(db: Session, company_id: int) -> list[dict]:
    ensure_whatsapp_automation(db, company_id)
    rows = (
        db.query(WhatsAppTemplate)
        .filter(WhatsAppTemplate.company_id == company_id)
        .order_by(WhatsAppTemplate.category, WhatsAppTemplate.code)
        .all()
    )
    return [
        {
            "id": t.id,
            "code": t.code,
            "name": t.name,
            "category": t.category,
            "body": t.body,
            "variables": t.variables or [],
            "language": t.language,
            "active": t.active,
            "auto_trigger": t.auto_trigger,
        }
        for t in rows
    ]


def _send_out(
    db: Session,
    *,
    company_id: int,
    user_id: int | None,
    phone: str,
    to_name: str,
    template_code: str,
    body: str,
    related_entity: str = "",
    related_id: str = "",
    live: bool = True,
) -> dict:
    phone = (phone or "").strip()
    if not phone:
        return {"ok": False, "error": "no phone"}
    provider = {"status": "queued_local", "live": False}
    try:
        from app.services.integrations_whatsapp import send_whatsapp_cloud_sync

        provider = send_whatsapp_cloud_sync(phone, body, template=template_code)
    except Exception as e:
        provider = {"status": "failed", "error": str(e), "live": False}
    status = "sent" if provider.get("status") in ("sent", "queued_local") else "failed"
    msg = CommsMessage(
        company_id=company_id,
        channel="whatsapp",
        to_phone=phone,
        to_name=to_name or "",
        template=template_code,
        body=body,
        status=status,
        related_entity=related_entity,
        related_id=related_id,
        meta={"provider": provider, "auto": True, "message_id": provider.get("message_id")},
    )
    db.add(msg)
    if user_id:
        db.add(
            Notification(
                company_id=company_id,
                user_id=user_id,
                title=f"WA Auto → {to_name or phone}",
                body=body[:140],
            )
        )
    db.flush()
    return {"ok": status != "failed", "id": msg.id, "to": to_name or phone, "template": template_code, "status": status}


def run_whatsapp_flow(db: Session, company_id: int, user_id: int | None, flow: str, brand: str = "KanhaERP") -> dict:
    """Run one automated WhatsApp flow using templates."""
    ensure_whatsapp_automation(db, company_id, brand)
    created: list[dict] = []

    if flow in ("lead_followup", "all"):
        tpl = get_template(db, company_id, "lead_followup")
        leads = (
            db.query(Lead)
            .filter(Lead.company_id == company_id, Lead.stage.in_(["new", "qualified"]))
            .order_by(Lead.id.desc())
            .limit(10)
            .all()
        )
        for lead in leads:
            phone = (lead.phone or "").strip()
            if not phone:
                continue
            body = render_template(
                tpl.body if tpl else DEFAULT_TEMPLATES[0]["body"],
                {
                    "name": lead.name,
                    "company": lead.company_name or "your enquiry",
                    "value": f"{float(lead.value or 0):,.0f}",
                    "brand": brand,
                },
            )
            created.append(
                _send_out(
                    db,
                    company_id=company_id,
                    user_id=user_id,
                    phone=phone,
                    to_name=lead.name,
                    template_code="lead_followup",
                    body=body,
                    related_entity="lead",
                    related_id=str(lead.id),
                )
            )

    if flow in ("invoice_overdue", "all"):
        tpl = get_template(db, company_id, "invoice_overdue")
        invs = (
            db.query(Invoice)
            .filter(Invoice.company_id == company_id, Invoice.status.in_(["posted", "partial", "overdue"]))
            .order_by(Invoice.id.desc())
            .limit(20)
            .all()
        )
        for inv in invs:
            bal = float(inv.total or 0) - float(inv.paid or 0)
            if bal <= 0:
                continue
            cust = db.get(Customer, inv.customer_id) if inv.customer_id else None
            phone = (cust.phone if cust else "") or ""
            if not phone:
                continue
            body = render_template(
                tpl.body if tpl else DEFAULT_TEMPLATES[1]["body"],
                {
                    "name": cust.name if cust else "Customer",
                    "number": inv.number,
                    "amount": f"{bal:,.0f}",
                    "due_date": inv.due_date.isoformat() if inv.due_date else "—",
                    "brand": brand,
                },
            )
            created.append(
                _send_out(
                    db,
                    company_id=company_id,
                    user_id=user_id,
                    phone=phone,
                    to_name=cust.name if cust else "",
                    template_code="invoice_overdue",
                    body=body,
                    related_entity="invoice",
                    related_id=str(inv.id),
                )
            )

    if flow in ("stock_alert", "all"):
        tpl = get_template(db, company_id, "stock_alert")
        # notify company admin phone from first customer? use notification only + optional admin
        admin_phone = ""
        for bal in db.query(StockBalance).filter(StockBalance.company_id == company_id).limit(200).all():
            p = db.get(Product, bal.product_id)
            if not p:
                continue
            point = float((p.custom or {}).get("reorder_point", 50))
            if float(bal.qty or 0) >= point:
                continue
            body = render_template(
                tpl.body if tpl else DEFAULT_TEMPLATES[5]["body"],
                {"sku": p.sku, "qty": bal.qty, "point": point, "brand": brand},
            )
            # Internal: always notification; WA only if meta admin_phone set on template
            phone = ((tpl.meta or {}).get("alert_phone") if tpl else None) or admin_phone
            if phone:
                created.append(
                    _send_out(
                        db,
                        company_id=company_id,
                        user_id=user_id,
                        phone=phone,
                        to_name="Ops",
                        template_code="stock_alert",
                        body=body,
                        related_entity="product",
                        related_id=str(p.id),
                    )
                )
            elif user_id:
                db.add(
                    Notification(
                        company_id=company_id,
                        user_id=user_id,
                        title=f"Low stock {p.sku}",
                        body=body,
                    )
                )
                created.append({"ok": True, "template": "stock_alert", "sku": p.sku, "via": "notification"})

    if flow in ("quote_followup", "all"):
        # reuse leads in proposal-ish stages as quote proxy if no quote table wired
        tpl = get_template(db, company_id, "quote_followup")
        leads = (
            db.query(Lead)
            .filter(Lead.company_id == company_id, Lead.stage.in_(["proposal", "negotiation"]))
            .order_by(Lead.id.desc())
            .limit(10)
            .all()
        )
        for lead in leads:
            phone = (lead.phone or "").strip()
            if not phone:
                continue
            body = render_template(
                tpl.body if tpl else DEFAULT_TEMPLATES[4]["body"],
                {
                    "name": lead.name,
                    "number": f"L-{lead.id}",
                    "amount": f"{float(lead.value or 0):,.0f}",
                    "brand": brand,
                },
            )
            created.append(
                _send_out(
                    db,
                    company_id=company_id,
                    user_id=user_id,
                    phone=phone,
                    to_name=lead.name,
                    template_code="quote_followup",
                    body=body,
                    related_entity="lead",
                    related_id=str(lead.id),
                )
            )

    ok_n = sum(1 for c in created if c.get("ok"))
    return {
        "ok": True,
        "flow": flow,
        "created": created,
        "count": len(created),
        "sent_ok": ok_n,
        "message": f"WhatsApp automation '{flow}': {ok_n}/{len(created)} dispatched",
        "ran_at": datetime.utcnow().isoformat() + "Z",
    }


def run_all_whatsapp_automation(db: Session, company_id: int, user_id: int | None, brand: str = "KanhaERP") -> dict:
    """Run every active WhatsApp automation job."""
    ensure_whatsapp_automation(db, company_id, brand)
    jobs = (
        db.query(AutomationJob)
        .filter(
            AutomationJob.company_id == company_id,
            AutomationJob.active.is_(True),
            AutomationJob.action.like("whatsapp%"),
        )
        .all()
    )
    results = []
    # Always run core "all" pack once for completeness
    results.append(run_whatsapp_flow(db, company_id, user_id, "all", brand))
    for j in jobs:
        j.config = {**(j.config or {}), "last_run": date.today().isoformat()}
    db.flush()
    total = sum(r.get("count") or 0 for r in results)
    return {
        "ok": True,
        "jobs": len(jobs),
        "results": results,
        "count": total,
        "message": f"All WhatsApp automations ran — {total} messages/notifications",
    }
