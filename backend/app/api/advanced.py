"""Kanha advanced intelligence — ageing, party ledgers, smart alerts, MIS compare."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import func

from app.core.deps import CurrentUser, DbDep, audit, next_number
from app.models import (
    Account,
    Customer,
    FieldTask,
    FieldVisit,
    FollowUp,
    Invoice,
    JournalEntry,
    PaymentRequest,
    Product,
    PurchaseInvoice,
    PurchaseOrder,
    PurchaseRequisition,
    SalesOrder,
    StockBalance,
    Vendor,
    Warehouse,
)

router = APIRouter(prefix="/api/advanced", tags=["advanced"])


def _age_bucket(days: int) -> str:
    if days <= 30:
        return "0-30"
    if days <= 60:
        return "31-60"
    if days <= 90:
        return "61-90"
    return "90+"


@router.get("/flow-guide")
def flow_guide(user: CurrentUser) -> dict:
    """Explain where demo data lives — for training / first login."""
    return {
        "ok": True,
        "title": "Kanha live data map",
        "flows": [
            {
                "name": "Sales money in",
                "steps": ["CRM Lead", "Quote", "Sales Order", "Invoice", "Kanha Books receipt", "WhatsApp chase if overdue"],
                "href": "#/flow",
            },
            {
                "name": "Purchase money out",
                "steps": ["Indent", "PR Approve", "RFQ rate", "PO", "GRN", "Payment request / Books payment"],
                "href": "#/indents",
            },
            {
                "name": "Shop floor",
                "steps": ["BOM", "Work Order Advance", "Production Challan", "Receive stock → Godown"],
                "href": "#/manufacturing",
            },
            {
                "name": "Field desk",
                "steps": ["Plan Visit", "Task Desk", "Followup", "WhatsApp"],
                "href": "#/visit",
            },
            {
                "name": "Accounts",
                "steps": ["Post voucher", "Cash/Bank book", "Bank recon match", "GSTR-3B desk", "Trial balance"],
                "href": "#/books",
            },
            {
                "name": "People pay",
                "steps": ["Employee", "Attendance", "Payroll run", "Payslip", "Disburse"],
                "href": "#/hr-flow",
            },
        ],
        "tip": "Har row pe Details / Done / Approve dabao — data DB me save hota hai, page reload ke baad dikhega.",
    }


@router.get("/smart-alerts")
def smart_alerts(user: CurrentUser, db: DbDep) -> dict:
    """Owner command alerts — what needs action today (market differentiator)."""
    cid = user.company_id
    today = date.today()
    alerts: list[dict[str, Any]] = []

    overdue = (
        db.query(Invoice)
        .filter(
            Invoice.company_id == cid,
            Invoice.total > Invoice.paid,
            Invoice.due_date != None,  # noqa: E711
            Invoice.due_date < today,
        )
        .all()
    )
    if overdue:
        amt = sum(float(i.total or 0) - float(i.paid or 0) for i in overdue)
        alerts.append(
            {
                "level": "critical",
                "code": "ar_overdue",
                "title": f"{len(overdue)} overdue invoices",
                "detail": f"₹{round(amt, 2):,.2f} stuck — chase via WhatsApp",
                "href": "#/payments-ops",
                "action": "Chase receivables",
            }
        )

    low = []
    bals = db.query(StockBalance).filter(StockBalance.company_id == cid).all()
    for b in bals:
        p = db.get(Product, b.product_id)
        if not p:
            continue
        rp = float((p.custom or {}).get("reorder_point") or 50)
        if float(b.qty or 0) <= rp:
            low.append(p.sku)
    if low:
        alerts.append(
            {
                "level": "warn",
                "code": "low_stock",
                "title": f"{len(low)} SKUs at/below reorder",
                "detail": ", ".join(low[:6]) + ("…" if len(low) > 6 else ""),
                "href": "#/inventory",
                "action": "Reorder / PR",
            }
        )

    pending_pr = (
        db.query(PurchaseRequisition)
        .filter(PurchaseRequisition.company_id == cid, PurchaseRequisition.status == "pending")
        .count()
    )
    if pending_pr:
        alerts.append(
            {
                "level": "info",
                "code": "pr_pending",
                "title": f"{pending_pr} PRs awaiting approval",
                "detail": "Unblock purchase path Indent→PR→PO",
                "href": "#/indents",
                "action": "Approve PRs",
            }
        )

    visits = (
        db.query(FieldVisit)
        .filter(FieldVisit.company_id == cid, FieldVisit.status == "planned", FieldVisit.visit_date <= today)
        .count()
    )
    if visits:
        alerts.append(
            {
                "level": "info",
                "code": "visits_due",
                "title": f"{visits} field visits due/overdue",
                "detail": "Mark done or reschedule",
                "href": "#/visit",
                "action": "Open visits",
            }
        )

    fus = (
        db.query(FollowUp)
        .filter(
            FollowUp.company_id == cid,
            FollowUp.status == "open",
            FollowUp.next_followup_date != None,  # noqa: E711
            FollowUp.next_followup_date <= today,
        )
        .count()
    )
    if fus:
        alerts.append(
            {
                "level": "warn",
                "code": "followups_due",
                "title": f"{fus} followups due today",
                "detail": "Close or WhatsApp chase",
                "href": "#/followup",
                "action": "Followups",
            }
        )

    pay_req = (
        db.query(PaymentRequest)
        .filter(PaymentRequest.company_id == cid, PaymentRequest.status == "pending")
        .count()
    )
    if pay_req:
        alerts.append(
            {
                "level": "info",
                "code": "pay_req",
                "title": f"{pay_req} payment requests pending",
                "detail": "Approve / mark paid",
                "href": "#/payments-ops",
                "action": "Payment desk",
            }
        )

    open_so = (
        db.query(SalesOrder)
        .filter(SalesOrder.company_id == cid, SalesOrder.status.in_(["confirmed", "draft"]))
        .count()
    )
    if open_so >= 5:
        alerts.append(
            {
                "level": "info",
                "code": "open_orders",
                "title": f"{open_so} open sales orders",
                "detail": "Invoice / dispatch backlog",
                "href": "#/sales",
                "action": "Sales desk",
            }
        )

    # Credit pressure: customers near limit
    for c in db.query(Customer).filter(Customer.company_id == cid, Customer.credit_limit > 0).limit(40).all():
        from app.services.ops_intelligence import customer_outstanding

        out = customer_outstanding(db, cid, c.id)
        lim = float(c.credit_limit or 0)
        if lim and out >= lim * 0.85:
            alerts.append(
                {
                    "level": "warn" if out < lim else "critical",
                    "code": "credit_pressure",
                    "title": f"Credit tight · {c.name}",
                    "detail": f"Outstanding ₹{out:,.0f} / limit ₹{lim:,.0f}",
                    "href": "#/crm",
                    "action": "Collect / raise limit",
                }
            )

    score = 100
    for a in alerts:
        score -= {"critical": 18, "warn": 10, "info": 5}.get(a["level"], 5)
    score = max(35, min(100, score))

    return {
        "ok": True,
        "date": today.isoformat(),
        "health_score": score,
        "alert_count": len(alerts),
        "alerts": alerts,
        "advanced_note": "Kanha smart alerts — classic ERPs leave this to Excel",
    }


@router.get("/ageing/receivables")
def ar_ageing(user: CurrentUser, db: DbDep) -> dict:
    cid = user.company_id
    today = date.today()
    buckets = {"0-30": 0.0, "31-60": 0.0, "61-90": 0.0, "90+": 0.0}
    parties: dict[str, dict] = {}
    for inv in db.query(Invoice).filter(Invoice.company_id == cid).all():
        bal = float(inv.total or 0) - float(inv.paid or 0)
        if bal <= 0.01:
            continue
        due = inv.due_date or inv.invoice_date or today
        days = (today - due).days
        b = _age_bucket(max(0, days))
        buckets[b] += bal
        cust = db.get(Customer, inv.customer_id)
        name = cust.name if cust else f"Customer#{inv.customer_id}"
        row = parties.setdefault(name, {"party": name, "balance": 0.0, "0-30": 0, "31-60": 0, "61-90": 0, "90+": 0, "invoices": 0})
        row["balance"] += bal
        row[b] += bal
        row["invoices"] += 1
    rows = sorted(parties.values(), key=lambda x: -x["balance"])
    for r in rows:
        for k in ("balance", "0-30", "31-60", "61-90", "90+"):
            r[k] = round(r[k], 2)
    return {
        "ok": True,
        "as_of": today.isoformat(),
        "buckets": {k: round(v, 2) for k, v in buckets.items()},
        "total": round(sum(buckets.values()), 2),
        "parties": rows[:40],
    }


@router.get("/ageing/payables")
def ap_ageing(user: CurrentUser, db: DbDep) -> dict:
    cid = user.company_id
    today = date.today()
    buckets = {"0-30": 0.0, "31-60": 0.0, "61-90": 0.0, "90+": 0.0}
    parties: dict[str, dict] = {}
    for inv in db.query(PurchaseInvoice).filter(PurchaseInvoice.company_id == cid).all():
        bal = float(inv.total or 0) - float(inv.paid or 0)
        if bal <= 0.01:
            continue
        created = inv.created_at.date() if inv.created_at else today
        days = (today - created).days
        b = _age_bucket(max(0, days))
        buckets[b] += bal
        vend = db.get(Vendor, inv.vendor_id)
        name = vend.name if vend else f"Vendor#{inv.vendor_id}"
        row = parties.setdefault(name, {"party": name, "balance": 0.0, "0-30": 0, "31-60": 0, "61-90": 0, "90+": 0, "bills": 0})
        row["balance"] += bal
        row[b] += bal
        row["bills"] += 1
    rows = sorted(parties.values(), key=lambda x: -x["balance"])
    for r in rows:
        for k in ("balance", "0-30", "31-60", "61-90", "90+"):
            r[k] = round(r[k], 2)
    return {
        "ok": True,
        "as_of": today.isoformat(),
        "buckets": {k: round(v, 2) for k, v in buckets.items()},
        "total": round(sum(buckets.values()), 2),
        "parties": rows[:40],
    }


@router.get("/party-ledger")
def party_ledger(user: CurrentUser, db: DbDep, party: str, party_type: str = "customer") -> dict:
    """Customer / vendor running ledger — advanced vs form-only ERPs."""
    cid = user.company_id
    party = (party or "").strip()
    if not party:
        raise HTTPException(400, "party required")
    entries: list[dict] = []
    bal = 0.0

    if party_type == "customer":
        custs = db.query(Customer).filter(Customer.company_id == cid, Customer.name.ilike(f"%{party}%")).all()
        ids = [c.id for c in custs]
        invs = []
        if ids:
            invs = (
                db.query(Invoice)
                .filter(Invoice.company_id == cid, Invoice.customer_id.in_(ids))
                .order_by(Invoice.invoice_date, Invoice.id)
                .all()
            )
        for inv in invs:
            bal += float(inv.total or 0)
            entries.append(
                {
                    "date": inv.invoice_date.isoformat() if inv.invoice_date else None,
                    "doc": inv.number,
                    "type": "invoice",
                    "debit": float(inv.total or 0),
                    "credit": 0,
                    "balance": round(bal, 2),
                    "narration": "Sales invoice",
                }
            )
            if float(inv.paid or 0) > 0:
                bal -= float(inv.paid or 0)
                entries.append(
                    {
                        "date": inv.invoice_date.isoformat() if inv.invoice_date else None,
                        "doc": inv.number,
                        "type": "receipt",
                        "debit": 0,
                        "credit": float(inv.paid or 0),
                        "balance": round(bal, 2),
                        "narration": "Payment received",
                    }
                )
    else:
        vendors = db.query(Vendor).filter(Vendor.company_id == cid, Vendor.name.ilike(f"%{party}%")).all()
        ids = [v.id for v in vendors]
        invs = []
        if ids:
            invs = (
                db.query(PurchaseInvoice)
                .filter(PurchaseInvoice.company_id == cid, PurchaseInvoice.vendor_id.in_(ids))
                .order_by(PurchaseInvoice.id)
                .all()
            )
        for inv in invs:
            bal += float(inv.total or 0)
            entries.append(
                {
                    "date": inv.created_at.date().isoformat() if inv.created_at else None,
                    "doc": inv.number,
                    "type": "bill",
                    "debit": 0,
                    "credit": float(inv.total or 0),
                    "balance": round(bal, 2),
                    "narration": "Purchase bill",
                }
            )
            if float(inv.paid or 0) > 0:
                bal -= float(inv.paid or 0)
                entries.append(
                    {
                        "date": inv.created_at.date().isoformat() if inv.created_at else None,
                        "doc": inv.number,
                        "type": "payment",
                        "debit": float(inv.paid or 0),
                        "credit": 0,
                        "balance": round(bal, 2),
                        "narration": "Payment made",
                    }
                )

    # Books vouchers tagged with party (non-duplicate of invoice/bill lines)
    for j in (
        db.query(JournalEntry)
        .filter(JournalEntry.company_id == cid)
        .order_by(JournalEntry.entry_date, JournalEntry.id)
        .all()
    ):
        pname = (getattr(j, "party_name", None) or "").lower()
        if party.lower() not in pname:
            continue
        vtype = (getattr(j, "voucher_type", None) or "journal").lower()
        # Invoice/bill + paid already captured above — skip sales/purchase/receipt/payment
        if vtype in ("sales", "purchase", "receipt", "payment"):
            continue
        debit = sum(float(ln.get("debit") or 0) for ln in (j.lines or []))
        credit = sum(float(ln.get("credit") or 0) for ln in (j.lines or []))
        entries.append(
            {
                "date": j.entry_date.isoformat() if j.entry_date else None,
                "doc": j.number,
                "type": vtype,
                "debit": debit,
                "credit": credit,
                "balance": round(bal, 2),
                "narration": j.narration,
            }
        )

    return {
        "ok": True,
        "party": party,
        "party_type": party_type,
        "closing": round(bal, 2),
        "entries": entries,
        "count": len(entries),
    }


@router.get("/party-ledger.csv")
def party_ledger_csv(user: CurrentUser, db: DbDep, party: str, party_type: str = "customer"):
    """Download party statement as CSV (CA / WhatsApp share)."""
    import csv
    import io

    from fastapi.responses import StreamingResponse

    data = party_ledger(user, db, party=party, party_type=party_type)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Date", "Doc", "Type", "Narration", "Debit", "Credit", "Balance"])
    for e in data.get("entries") or []:
        w.writerow(
            [
                e.get("date") or "",
                e.get("doc") or "",
                e.get("type") or "",
                e.get("narration") or "",
                e.get("debit") or 0,
                e.get("credit") or 0,
                e.get("balance") if e.get("balance") is not None else "",
            ]
        )
    w.writerow([])
    w.writerow(["Party", data.get("party"), "Type", data.get("party_type"), "Closing", data.get("closing")])
    buf.seek(0)
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in (party or "party"))[:40]
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="kanha-party-{safe}.csv"'},
    )


@router.get("/stock-ageing")
def stock_ageing(user: CurrentUser, db: DbDep) -> dict:
    """Proxy stock ageing by last move / value — flags slow movers."""
    from app.models import StockMove

    cid = user.company_id
    today = date.today()
    bals = db.query(StockBalance).filter(StockBalance.company_id == cid, StockBalance.qty > 0).all()
    rows = []
    for b in bals:
        p = db.get(Product, b.product_id)
        wh = db.get(Warehouse, b.warehouse_id)
        last = (
            db.query(StockMove)
            .filter(
                StockMove.company_id == cid,
                StockMove.product_id == b.product_id,
                StockMove.warehouse_id == b.warehouse_id,
            )
            .order_by(StockMove.id.desc())
            .first()
        )
        last_dt = last.created_at.date() if last and last.created_at else today - timedelta(days=45)
        days = (today - last_dt).days
        value = float(b.qty or 0) * float(b.avg_cost or (p.sale_price if p else 0) or 0)
        rows.append(
            {
                "sku": p.sku if p else "",
                "name": p.name if p else str(b.product_id),
                "warehouse": wh.code if wh else "",
                "qty": b.qty,
                "days_idle": days,
                "bucket": _age_bucket(days),
                "value": round(value, 2),
                "slow": days > 60,
            }
        )
    rows.sort(key=lambda x: -x["days_idle"])
    slow = sum(1 for r in rows if r["slow"])
    return {"ok": True, "lines": rows[:60], "slow_movers": slow, "skus": len(rows)}


@router.get("/mis/compare")
def mis_compare(user: CurrentUser, db: DbDep) -> dict:
    """This month vs last month — advanced owner MIS."""
    cid = user.company_id
    today = date.today()
    this_key = today.strftime("%Y-%m")
    last_month = (today.replace(day=1) - timedelta(days=1))
    last_key = last_month.strftime("%Y-%m")

    def month_sales(key: str) -> float:
        total = 0.0
        for i in db.query(Invoice).filter(Invoice.company_id == cid).all():
            if i.invoice_date and i.invoice_date.strftime("%Y-%m") == key:
                total += float(i.total or 0)
        return total

    def month_purchase(key: str) -> float:
        total = 0.0
        for p in db.query(PurchaseOrder).filter(PurchaseOrder.company_id == cid).all():
            # approximate by created_at
            if p.created_at and p.created_at.strftime("%Y-%m") == key:
                total += float(p.total or 0)
        return total

    s0, s1 = month_sales(this_key), month_sales(last_key)
    p0, p1 = month_purchase(this_key), month_purchase(last_key)

    def pct(cur: float, prev: float) -> float:
        if prev <= 0:
            return 100.0 if cur > 0 else 0.0
        return round((cur - prev) / prev * 100.0, 1)

    return {
        "ok": True,
        "this_month": this_key,
        "last_month": last_key,
        "sales": {"this": round(s0, 2), "last": round(s1, 2), "change_pct": pct(s0, s1)},
        "purchase": {"this": round(p0, 2), "last": round(p1, 2), "change_pct": pct(p0, p1)},
        "gross_spread": {"this": round(s0 - p0, 2), "last": round(s1 - p1, 2)},
    }


@router.get("/bill-wise")
def bill_wise(user: CurrentUser, db: DbDep, party_type: str = "customer", party_id: int | None = None) -> dict:
    """CA-grade open bills (invoice-wise outstanding)."""
    from app.services.ops_intelligence import bill_wise_ap, bill_wise_ar

    if party_type == "vendor":
        rows = bill_wise_ap(db, user.company_id, party_id)
    else:
        rows = bill_wise_ar(db, user.company_id, party_id)
    return {
        "ok": True,
        "party_type": party_type,
        "bills": rows,
        "count": len(rows),
        "total_balance": round(sum(float(r["balance"]) for r in rows), 2),
        "note": "Bill-by-bill open invoices — allocate receipts against each bill",
    }


@router.get("/godown-valuation")
def godown_valuation(user: CurrentUser, db: DbDep) -> dict:
    """Stock valuation by godown (qty × avg_cost) — Tally-style inventory valuation."""
    bals = db.query(StockBalance).filter(StockBalance.company_id == user.company_id, StockBalance.qty > 0).all()
    by_wh: dict[int, dict] = {}
    grand = 0.0
    for b in bals:
        wh = db.get(Warehouse, b.warehouse_id)
        p = db.get(Product, b.product_id)
        val = round(float(b.qty or 0) * float(b.avg_cost or 0), 2)
        grand += val
        bucket = by_wh.setdefault(
            b.warehouse_id,
            {"warehouse_id": b.warehouse_id, "code": wh.code if wh else "", "name": wh.name if wh else "", "value": 0.0, "lines": []},
        )
        bucket["value"] = round(bucket["value"] + val, 2)
        bucket["lines"].append(
            {
                "sku": p.sku if p else "",
                "name": p.name if p else "",
                "qty": b.qty,
                "avg_cost": b.avg_cost,
                "value": val,
            }
        )
    return {
        "ok": True,
        "godowns": list(by_wh.values()),
        "total_value": round(grand, 2),
        "note": "Valuation at weighted average cost (GRN/WIP→FG)",
    }


@router.get("/chase/overdue")
def chase_overdue(user: CurrentUser, db: DbDep) -> dict:
    """WhatsApp-ready chase drafts for overdue AR — advanced vs static ERP."""
    cid = user.company_id
    today = date.today()
    drafts = []
    for inv in db.query(Invoice).filter(Invoice.company_id == cid).all():
        bal = float(inv.total or 0) - float(inv.paid or 0)
        if bal <= 0.01:
            continue
        due = inv.due_date or inv.invoice_date
        if not due or due >= today:
            continue
        cust = db.get(Customer, inv.customer_id)
        name = cust.name if cust else "Customer"
        phone = getattr(cust, "phone", "") or ""
        days = (today - due).days
        msg = (
            f"Namaste {name}, invoice {inv.number} for ₹{bal:,.2f} is overdue by {days} days "
            f"(due {due.isoformat()}). Kindly arrange payment. — KanhaERP"
        )
        drafts.append(
            {
                "invoice": inv.number,
                "party": name,
                "phone": phone,
                "balance": round(bal, 2),
                "days_overdue": days,
                "whatsapp_draft": msg,
                "href": "#/whatsapp",
            }
        )
    drafts.sort(key=lambda x: -x["days_overdue"])
    return {"ok": True, "count": len(drafts), "drafts": drafts[:30]}


class ChaseSendIn(BaseModel):
    invoice: str = ""
    phone: str = ""
    limit: int = 10


@router.post("/chase/send")
def chase_send_one(body: ChaseSendIn, user: CurrentUser, db: DbDep) -> dict:
    """Send one overdue chase via WhatsApp (demo or Meta)."""
    from app.api.extended import WhatsAppSendIn, whatsapp_send

    pack = chase_overdue(user, db)
    drafts = pack.get("drafts") or []
    row = None
    if body.invoice:
        row = next((d for d in drafts if str(d.get("invoice")) == str(body.invoice)), None)
    if not row and drafts:
        row = drafts[0]
    if not row:
        raise HTTPException(404, "No overdue chase draft")
    phone = (body.phone or row.get("phone") or "").strip() or "919876543210"
    res = whatsapp_send(
        WhatsAppSendIn(
            to_phone=phone,
            to_name=row.get("party") or "",
            body=row.get("whatsapp_draft") or "",
            template="invoice_overdue",
            related_entity="invoice",
            related_id="",
        ),
        user,
        db,
    )
    return {
        "ok": True,
        "invoice": row.get("invoice"),
        "party": row.get("party"),
        "phone": phone,
        "send": res,
        "message": f"Chase sent · {row.get('invoice')} → {phone}",
    }


@router.post("/chase/send-all")
def chase_send_all(user: CurrentUser, db: DbDep, body: ChaseSendIn | None = None) -> dict:
    """Batch send overdue chase drafts (cap 10) — Ops Chase Pack."""
    from app.api.extended import WhatsAppSendIn, whatsapp_send

    lim = max(1, min(int((body.limit if body else 10) or 10), 20))
    pack = chase_overdue(user, db)
    drafts = (pack.get("drafts") or [])[:lim]
    results = []
    for row in drafts:
        phone = (row.get("phone") or "").strip() or "919876543210"
        try:
            res = whatsapp_send(
                WhatsAppSendIn(
                    to_phone=phone,
                    to_name=row.get("party") or "",
                    body=row.get("whatsapp_draft") or "",
                    template="invoice_overdue",
                    related_entity="invoice",
                    related_id="",
                ),
                user,
                db,
            )
            results.append({"invoice": row.get("invoice"), "phone": phone, "status": res.get("status"), "ok": True})
        except Exception as exc:  # noqa: BLE001
            results.append({"invoice": row.get("invoice"), "phone": phone, "ok": False, "error": str(exc)})
    ok_n = sum(1 for r in results if r.get("ok"))
    return {
        "ok": True,
        "sent": ok_n,
        "total": len(results),
        "results": results,
        "message": f"Chase batch · {ok_n}/{len(results)} sent (demo or Meta)",
    }


# ── Kanha Extras: WhatsApp Login · Meta webhook · OCR · Store slots ───────────

extras_router = APIRouter(prefix="/api/extras", tags=["extras"])
meta_router = APIRouter(prefix="/api/meta", tags=["meta"])


def _extras_blob(db: DbDep, company_id: int) -> dict[str, Any]:
    from app.models import Company

    co = db.get(Company, company_id)
    sj = dict((co.settings_json if co else None) or {})
    return dict(sj.get("extras") or {})


def _save_extras(db: DbDep, company_id: int, mutator) -> dict[str, Any]:
    from app.models import Company

    co = db.get(Company, company_id)
    if not co:
        raise HTTPException(404, "Company not found")
    sj = dict(co.settings_json or {})
    ex = dict(sj.get("extras") or {})
    mutator(ex)
    sj["extras"] = ex
    co.settings_json = sj
    db.add(co)
    db.commit()
    return ex


@extras_router.get("/whatsapp-login")
def extras_wa_login_get(user: CurrentUser, db: DbDep) -> dict:
    """SBAC Whatsapp Login (whatsappset) — mobile + type + instance/QR status."""
    from app.core.config import settings as cfg

    ex = _extras_blob(db, user.company_id)
    wa = dict(ex.get("whatsapp_login") or {})
    return {
        "ok": True,
        "mobile": wa.get("mobile") or "",
        "login_type": wa.get("login_type") or "Default",
        "instance_id": wa.get("instance_id") or "",
        "status": wa.get("status") or ("linked" if cfg.whatsapp_live else "demo"),
        "qr_hint": wa.get("qr_hint") or "Demo QR — Meta Cloud uses webhook, not session QR",
        "meta_live": bool(cfg.whatsapp_live),
        "webhook_path": "/api/meta/whatsapp/webhook",
        "verify_token_set": bool(cfg.whatsapp_verify_token),
    }


class WaLoginIn(BaseModel):
    mobile: str = ""
    login_type: str = "Default"  # Default / User
    action: str = "save"  # save | instance | qr | reset


@extras_router.post("/whatsapp-login")
def extras_wa_login_save(body: WaLoginIn, user: CurrentUser, db: DbDep) -> dict:
    action = (body.action or "save").lower()
    mobile = (body.mobile or "").strip()
    login_type = body.login_type if body.login_type in ("Default", "User") else "Default"

    def mut(ex: dict) -> None:
        wa = dict(ex.get("whatsapp_login") or {})
        if action == "reset":
            ex["whatsapp_login"] = {
                "mobile": "",
                "login_type": "Default",
                "instance_id": "",
                "status": "reset",
                "qr_hint": "Reset — create instance again",
                "updated_at": datetime.utcnow().isoformat() + "Z",
            }
            return
        wa["mobile"] = mobile
        wa["login_type"] = login_type
        wa["updated_at"] = datetime.utcnow().isoformat() + "Z"
        if action == "instance":
            wa["instance_id"] = wa.get("instance_id") or f"kanha-wa-{user.company_id}-{int(datetime.utcnow().timestamp())}"
            wa["status"] = "instance_ready"
            wa["qr_hint"] = "Instance created (demo) — Get QR or connect Meta webhook"
        elif action == "qr":
            if not wa.get("instance_id"):
                wa["instance_id"] = f"kanha-wa-{user.company_id}-{int(datetime.utcnow().timestamp())}"
            wa["status"] = "qr_ready"
            wa["qr_hint"] = f"DEMO-QR · instance {wa['instance_id']} · scan not required when Meta Cloud keys set"
        else:
            wa["status"] = wa.get("status") or "saved"
        ex["whatsapp_login"] = wa

    ex = _save_extras(db, user.company_id, mut)
    wa = ex.get("whatsapp_login") or {}
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action=f"wa_login_{action}",
        entity="extras",
        entity_id="whatsapp_login",
        detail={"mobile": mobile, "type": login_type},
    )
    return {
        "ok": True,
        **wa,
        "message": {
            "reset": "WhatsApp login reset",
            "instance": f"Instance {wa.get('instance_id')} ready",
            "qr": "QR ready (demo)",
            "save": "WhatsApp login saved",
        }.get(action, "Saved"),
    }


@extras_router.get("/store-slots")
def extras_store_slots_get(user: CurrentUser, db: DbDep) -> dict:
    ex = _extras_blob(db, user.company_id)
    slots = dict(ex.get("store_slots") or {})
    return {
        "ok": True,
        "android_url": slots.get("android_url")
        or "https://play.google.com/store/apps/details?id=com.kanhaerp.app",
        "ios_url": slots.get("ios_url") or "https://apps.apple.com/app/kanhaerp/id0000000000",
        "android_status": slots.get("android_status") or "slot_ready",
        "ios_status": slots.get("ios_status") or "slot_ready",
        "pwa_note": "PWA works now · store URLs = publish slots",
    }


class StoreSlotsIn(BaseModel):
    android_url: str = ""
    ios_url: str = ""
    android_status: str = "slot_ready"
    ios_status: str = "slot_ready"


@extras_router.post("/store-slots")
def extras_store_slots_save(body: StoreSlotsIn, user: CurrentUser, db: DbDep) -> dict:
    def mut(ex: dict) -> None:
        ex["store_slots"] = {
            "android_url": (body.android_url or "").strip()
            or "https://play.google.com/store/apps/details?id=com.kanhaerp.app",
            "ios_url": (body.ios_url or "").strip() or "https://apps.apple.com/app/kanhaerp/id0000000000",
            "android_status": body.android_status or "slot_ready",
            "ios_status": body.ios_status or "slot_ready",
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }

    slots = _save_extras(db, user.company_id, mut)["store_slots"]
    return {"ok": True, **slots, "message": "Store slots updated"}


class OcrParseIn(BaseModel):
    text: str = ""
    filename: str = ""
    doc_kind: str = "invoice"  # invoice | po | challan | other


@extras_router.post("/ocr/parse")
def extras_ocr_parse(body: OcrParseIn, user: CurrentUser, db: DbDep) -> dict:
    """Demo OCR — regex extract from pasted bill text (no external OCR key required)."""
    import re

    text = body.text or ""
    if not text.strip():
        raise HTTPException(400, "Paste invoice / bill text to parse")
    gstin_m = re.search(r"\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][A-Z0-9]Z[A-Z0-9])\b", text, re.I)
    inv_m = re.search(
        r"(?:invoice|inv|bill)\s*(?:no\.?|number|#|:)?\s*([A-Z0-9][A-Z0-9\-\/]{2,})",
        text,
        re.I,
    )
    amt_m = re.search(
        r"(?:grand\s*total|net\s*amount|total\s*amount|amount\s*payable|total)\s*:?\s*(?:rs\.?|inr|₹)?\s*([\d,]+\.?\d*)",
        text,
        re.I,
    )
    date_m = re.search(r"\b(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})\b", text)
    party_m = re.search(
        r"(?:bill\s*to|buyer|party|customer|vendor|m/s\.?)\s*[:\-]?\s*([A-Za-z0-9 &.\-]{3,60})",
        text,
        re.I,
    )
    phone_m = re.search(r"(?:\+91[\-\s]?)?([6-9]\d{9})\b", text)
    fields = {
        "gstin": (gstin_m.group(1).upper() if gstin_m else ""),
        "invoice_no": (inv_m.group(1).upper() if inv_m else ""),
        "amount": float(amt_m.group(1).replace(",", "")) if amt_m else 0.0,
        "date": date_m.group(1) if date_m else "",
        "party": (party_m.group(1).strip() if party_m else ""),
        "phone": phone_m.group(1) if phone_m else "",
        "doc_kind": body.doc_kind or "invoice",
        "filename": body.filename or "",
        "source": "kanha_ocr_demo",
    }
    confidence = round(
        sum(1 for k in ("gstin", "invoice_no", "amount", "date", "party") if fields.get(k)) / 5.0,
        2,
    )
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="ocr_parse",
        entity="extras",
        entity_id=fields.get("invoice_no") or "ocr",
        detail={"confidence": confidence},
    )
    return {
        "ok": True,
        "fields": fields,
        "confidence": confidence,
        "message": f"OCR demo · confidence {int(confidence * 100)}% · review before save",
    }


@meta_router.api_route("/whatsapp/webhook", methods=["GET", "POST"])
async def meta_wa_webhook(
    request: Request,
    db: DbDep,
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
):
    """Public Meta WhatsApp webhook — GET verify · POST inbound messages → Comms + OS actions."""
    from app.core.config import settings as cfg
    from app.models import Company, CommsMessage

    if request.method == "GET":
        token = hub_verify_token or ""
        if hub_mode == "subscribe" and token and token == (cfg.whatsapp_verify_token or ""):
            return PlainTextResponse(hub_challenge or "")
        return PlainTextResponse("verify token mismatch", status_code=403)

    payload = {}
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    # Resolve company: phone_number_id match in extras, else first company
    companies = db.query(Company).order_by(Company.id).all()
    company_id = companies[0].id if companies else None
    phone_id = ""
    try:
        phone_id = (
            (((payload.get("entry") or [{}])[0].get("changes") or [{}])[0].get("value") or {}).get(
                "metadata"
            )
            or {}
        ).get("phone_number_id") or ""
    except Exception:
        phone_id = ""
    if phone_id and companies:
        for co in companies:
            sj = dict(co.settings_json or {})
            ex = dict(sj.get("extras") or {})
            wa = dict(ex.get("whatsapp_login") or {})
            if str(wa.get("phone_number_id") or "") == str(phone_id) or str(cfg.whatsapp_phone_number_id) == str(
                phone_id
            ):
                company_id = co.id
                break
    if not company_id:
        return JSONResponse({"ok": False, "detail": "no company"}, status_code=404)

    received = 0
    actions: list[dict] = []
    try:
        for entry in payload.get("entry") or []:
            for change in entry.get("changes") or []:
                value = change.get("value") or {}
                for msg in value.get("messages") or []:
                    text = ""
                    if msg.get("type") == "text":
                        text = (msg.get("text") or {}).get("body") or ""
                    elif msg.get("type") == "button":
                        text = (msg.get("button") or {}).get("text") or ""
                    else:
                        text = str(msg.get("type") or "message")
                    from_phone = msg.get("from") or ""
                    contacts = value.get("contacts") or []
                    from_name = (contacts[0].get("profile") or {}).get("name") if contacts else "WA"
                    db.add(
                        CommsMessage(
                            company_id=company_id,
                            channel="whatsapp",
                            to_phone=from_phone,
                            to_name=from_name or "WA",
                            template="meta_inbound",
                            body=text,
                            status="received",
                            related_entity="whatsapp",
                            related_id=msg.get("id") or "",
                            meta={
                                "direction": "in",
                                "provider": "meta_webhook",
                                "phone_number_id": phone_id,
                                "raw_type": msg.get("type"),
                            },
                        )
                    )
                    received += 1
                    up = (text or "").strip().upper()
                    if up in ("YES", "APPROVE", "PAY", "ORDER", "STOCK", "NO"):
                        actions.append({"from": from_phone, "intent": up})
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"ok": False, "detail": str(exc)}, status_code=400)

    db.commit()
    return {"ok": True, "received": received, "actions": actions, "company_id": company_id}
