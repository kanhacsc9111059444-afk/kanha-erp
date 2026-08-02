"""Ops intelligence — credit, COGS, BOM consume, GST place-of-supply."""
from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.core.deps import next_number
from app.core.modules import gst_split
from app.models import (
    Account,
    BOM,
    Company,
    Customer,
    Invoice,
    JournalEntry,
    Product,
    PurchaseInvoice,
    StockBalance,
    StockMove,
    Vendor,
    Warehouse,
    WorkOrder,
)


class OpsBlock(Exception):
    """Business rule block — convert to HTTP 400 at API edge."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def state_code_from_gstin(gstin: str | None) -> str:
    g = (gstin or "").strip().upper()
    if len(g) >= 2 and g[:2].isdigit():
        return g[:2]
    return ""


def is_intra_state(company_gstin: str | None, party_gstin: str | None) -> bool:
    c = state_code_from_gstin(company_gstin)
    p = state_code_from_gstin(party_gstin)
    if not c or not p:
        return True
    return c == p


def gst_for_party(
    taxable: float,
    rate: float,
    *,
    company_gstin: str | None,
    party_gstin: str | None,
) -> dict[str, Any]:
    intra = is_intra_state(company_gstin, party_gstin)
    split = gst_split(float(taxable or 0), float(rate or 18), intra_state=intra)
    split["intra_state"] = intra
    split["company_state"] = state_code_from_gstin(company_gstin)
    split["party_state"] = state_code_from_gstin(party_gstin)
    return split


def customer_outstanding(db: Session, company_id: int, customer_id: int) -> float:
    total = 0.0
    for inv in (
        db.query(Invoice)
        .filter(Invoice.company_id == company_id, Invoice.customer_id == customer_id)
        .all()
    ):
        if (inv.invoice_type or "sales") == "credit":
            continue
        total += max(0.0, float(inv.total or 0) - float(inv.paid or 0))
    return round(total, 2)


def assert_credit_ok(
    db: Session,
    company_id: int,
    customer_id: int | None,
    extra_amount: float,
    *,
    soft: bool = False,
) -> dict[str, Any]:
    if not customer_id:
        return {"ok": True, "checked": False}
    cust = db.get(Customer, customer_id)
    if not cust or cust.company_id != company_id:
        return {"ok": True, "checked": False}
    limit = float(cust.credit_limit or 0)
    if limit <= 0:
        return {"ok": True, "checked": True, "unlimited": True, "party": cust.name}
    outstanding = customer_outstanding(db, company_id, customer_id)
    projected = round(outstanding + float(extra_amount or 0), 2)
    info = {
        "ok": projected <= limit + 0.01,
        "checked": True,
        "party": cust.name,
        "credit_limit": limit,
        "outstanding": outstanding,
        "order_amount": round(float(extra_amount or 0), 2),
        "projected": projected,
        "available": round(max(0.0, limit - outstanding), 2),
    }
    if not info["ok"] and not soft:
        raise OpsBlock(
            f"Credit limit exceeded for {cust.name}: outstanding ₹{outstanding:,.0f} + order ₹{extra_amount:,.0f} "
            f"> limit ₹{limit:,.0f} (available ₹{info['available']:,.0f}). Raise limit or collect dues."
        )
    return info


def _coa(db: Session, company_id: int) -> dict[str, Account]:
    return {
        a.code: a
        for a in db.query(Account).filter(Account.company_id == company_id, Account.is_group == False).all()  # noqa: E712
    }


def post_cogs_issue(
    db: Session,
    *,
    company_id: int,
    warehouse_id: int | None,
    lines: list[dict[str, Any]],
    ref: str,
    party_name: str = "",
) -> dict[str, Any]:
    """Dr COGS / Cr Inventory at avg_cost for issued lines."""
    if not warehouse_id or not lines:
        return {"ok": False, "cogs": 0, "journal": None}
    accounts = _coa(db, company_id)
    cogs_acc = accounts.get("5100")
    inv_acc = accounts.get("1400")
    if not cogs_acc or not inv_acc:
        return {"ok": False, "cogs": 0, "journal": None, "note": "COA missing 5100/1400"}

    cogs_total = 0.0
    detail = []
    for ln in lines:
        pid = ln.get("product_id")
        qty = abs(float(ln.get("qty") or 0))
        if not pid or qty <= 0:
            continue
        bal = (
            db.query(StockBalance)
            .filter(
                StockBalance.company_id == company_id,
                StockBalance.warehouse_id == warehouse_id,
                StockBalance.product_id == pid,
            )
            .first()
        )
        avg = float(bal.avg_cost or 0) if bal else 0.0
        if avg <= 0:
            p = db.get(Product, pid)
            avg = float(getattr(p, "cost_price", 0) or 0) if p else 0.0
        line_cogs = round(avg * qty, 2)
        cogs_total += line_cogs
        detail.append({"product_id": pid, "qty": qty, "avg_cost": avg, "cogs": line_cogs})

    cogs_total = round(cogs_total, 2)
    if cogs_total <= 0:
        return {"ok": True, "cogs": 0, "journal": None, "lines": detail}

    jn = next_number(db, company_id, JournalEntry, "CGS")
    db.add(
        JournalEntry(
            company_id=company_id,
            number=jn,
            entry_date=date.today(),
            narration=f"COGS · stock issue {ref}",
            lines=[
                {"account_id": cogs_acc.id, "account_code": "5100", "debit": cogs_total, "credit": 0},
                {"account_id": inv_acc.id, "account_code": "1400", "debit": 0, "credit": cogs_total},
            ],
            status="posted",
            voucher_type="journal",
            party_name=party_name,
        )
    )
    return {"ok": True, "cogs": cogs_total, "journal": jn, "lines": detail}


def consume_bom_for_wo(
    db: Session,
    wo: WorkOrder,
    *,
    warehouse_id: int | None = None,
) -> dict[str, Any]:
    """On WO release: deduct BOM component qty × WO qty from godown."""
    notes = (getattr(wo, "notes", None) or "") if hasattr(wo, "notes") else ""
    # idempotent: if cost already set from BOM and status past released, skip if stock moves exist
    bom = None
    if wo.bom_id:
        bom = db.get(BOM, wo.bom_id)
    if not bom:
        bom = (
            db.query(BOM)
            .filter(BOM.company_id == wo.company_id, BOM.product_id == wo.product_id, BOM.active == True)  # noqa: E712
            .first()
        )
    if not bom or not (bom.components or []):
        return {"ok": True, "skipped": True, "note": "No BOM components"}

    # Skip if already issued for this WO
    already = (
        db.query(StockMove)
        .filter(
            StockMove.company_id == wo.company_id,
            StockMove.ref == wo.number,
            StockMove.notes.ilike("%BOM consume%"),
        )
        .first()
    )
    if already:
        return {"ok": True, "already": True, "consumed": []}

    wh = None
    if warehouse_id:
        wh = db.get(Warehouse, warehouse_id)
    if not wh:
        wh = db.query(Warehouse).filter(Warehouse.company_id == wo.company_id).first()
    if not wh:
        raise OpsBlock("No warehouse for BOM material issue")

    wo_qty = float(wo.qty or 1)
    consumed = []
    total_cost = 0.0
    shortages = []

    for comp in bom.components or []:
        pid = comp.get("product_id")
        per = float(comp.get("qty") or comp.get("quantity") or 0)
        need = round(per * wo_qty, 4)
        if not pid or need <= 0:
            continue
        bal = (
            db.query(StockBalance)
            .filter(
                StockBalance.company_id == wo.company_id,
                StockBalance.warehouse_id == wh.id,
                StockBalance.product_id == pid,
            )
            .first()
        )
        on_hand = float(bal.qty or 0) if bal else 0.0
        if on_hand + 0.0001 < need:
            p = db.get(Product, pid)
            shortages.append(
                {
                    "product_id": pid,
                    "sku": p.sku if p else str(pid),
                    "need": need,
                    "on_hand": on_hand,
                }
            )
            continue
        avg = float(bal.avg_cost or 0) if bal else 0.0
        bal.qty = on_hand - need
        db.add(
            StockMove(
                company_id=wo.company_id,
                product_id=pid,
                warehouse_id=wh.id,
                qty=-need,
                move_type="issue",
                ref=wo.number,
                notes=f"BOM consume for {wo.number}",
            )
        )
        line_cost = round(avg * need, 2)
        total_cost += line_cost
        consumed.append({"product_id": pid, "qty": need, "avg_cost": avg, "cost": line_cost})

    if shortages:
        raise OpsBlock(
            "BOM material short: "
            + "; ".join(f"{s['sku']} need {s['need']} have {s['on_hand']}" for s in shortages[:5])
        )

    wo.cost = round(float(wo.cost or 0) + total_cost, 2)
    wo.wip_value = round(float(getattr(wo, "wip_value", 0) or 0) + total_cost, 2)

    accounts = _coa(db, wo.company_id)
    wip_acc = accounts.get("1450") or accounts.get("5100")
    inv_acc = accounts.get("1400")
    jn = None
    if total_cost > 0 and wip_acc and inv_acc:
        jn = next_number(db, wo.company_id, JournalEntry, "WIP")
        db.add(
            JournalEntry(
                company_id=wo.company_id,
                number=jn,
                entry_date=date.today(),
                narration=f"BOM → WIP {wo.number}",
                lines=[
                    {"account_id": wip_acc.id, "account_code": wip_acc.code, "debit": total_cost, "credit": 0},
                    {"account_id": inv_acc.id, "account_code": "1400", "debit": 0, "credit": total_cost},
                ],
                status="posted",
                voucher_type="journal",
                party_name="",
            )
        )

    return {
        "ok": True,
        "consumed": consumed,
        "material_cost": round(total_cost, 2),
        "wip_value": float(wo.wip_value or 0),
        "warehouse": wh.code,
        "journal": jn,
        "shortages": [],
        "notes": notes,
    }


def release_wip_to_fg(db: Session, wo: WorkOrder | None, *, qty: float, warehouse_id: int, product_id: int, ref: str) -> dict[str, Any]:
    """On production receive: WIP → FG Inventory; set FG avg_cost from WIP."""
    if not wo:
        return {"ok": False, "note": "no WO"}
    wip = float(getattr(wo, "wip_value", 0) or 0)
    if wip <= 0:
        return {"ok": True, "wip": 0, "journal": None}
    unit = round(wip / max(float(wo.qty or qty or 1), 0.0001), 4)
    fg_value = round(unit * float(qty or 0), 2) if qty else wip
    # Clear proportional WIP
    remain = round(max(0.0, wip - fg_value), 2)
    wo.wip_value = remain

    accounts = _coa(db, wo.company_id)
    wip_acc = accounts.get("1450") or accounts.get("5100")
    inv_acc = accounts.get("1400")
    jn = None
    if fg_value > 0 and wip_acc and inv_acc:
        jn = next_number(db, wo.company_id, JournalEntry, "FG")
        db.add(
            JournalEntry(
                company_id=wo.company_id,
                number=jn,
                entry_date=date.today(),
                narration=f"WIP → FG {ref}",
                lines=[
                    {"account_id": inv_acc.id, "account_code": "1400", "debit": fg_value, "credit": 0},
                    {"account_id": wip_acc.id, "account_code": wip_acc.code, "debit": 0, "credit": fg_value},
                ],
                status="posted",
                voucher_type="journal",
                party_name="",
            )
        )
    # bump FG avg_cost
    bal = (
        db.query(StockBalance)
        .filter(
            StockBalance.company_id == wo.company_id,
            StockBalance.warehouse_id == warehouse_id,
            StockBalance.product_id == product_id,
        )
        .first()
    )
    if bal and float(qty or 0) > 0:
        old_qty = float(bal.qty or 0) - float(qty)  # qty already added by caller? handle carefully
        # Caller adds qty first — so current bal.qty includes new qty
        cur = float(bal.qty or 0)
        prev = max(0.0, cur - float(qty))
        bal.avg_cost = ((prev * float(bal.avg_cost or 0)) + fg_value) / cur if cur else unit

    return {"ok": True, "fg_value": fg_value, "wip_remaining": remain, "journal": jn, "unit_cost": unit}


def issue_fefo(
    db: Session,
    *,
    company_id: int,
    warehouse_id: int,
    product_id: int,
    qty: float,
    ref: str,
) -> list[dict[str, Any]]:
    """Issue from StockBatch earliest expiry first; fall back to plain balance if no batches."""
    from app.models import StockBatch

    need = abs(float(qty or 0))
    if need <= 0:
        return []
    splits: list[dict[str, Any]] = []
    batches = (
        db.query(StockBatch)
        .filter(
            StockBatch.company_id == company_id,
            StockBatch.warehouse_id == warehouse_id,
            StockBatch.product_id == product_id,
            StockBatch.qty > 0,
        )
        .all()
    )
    # FEFO: expiry ascending, nulls last
    batches = sorted(
        batches,
        key=lambda b: (b.expiry_date is None, b.expiry_date or date.max),
    )
    for b in batches:
        if need <= 0:
            break
        take = min(float(b.qty or 0), need)
        if take <= 0:
            continue
        b.qty = float(b.qty or 0) - take
        db.add(
            StockMove(
                company_id=company_id,
                product_id=product_id,
                warehouse_id=warehouse_id,
                qty=-take,
                move_type="issue",
                ref=ref,
                notes=f"FEFO batch {b.batch_no}",
                batch_id=b.id,
            )
        )
        splits.append({"batch_id": b.id, "batch_no": b.batch_no, "qty": take, "expiry": b.expiry_date.isoformat() if b.expiry_date else None})
        need = round(need - take, 4)

    # Warehouse qty always mirrors
    bal = (
        db.query(StockBalance)
        .filter(
            StockBalance.company_id == company_id,
            StockBalance.warehouse_id == warehouse_id,
            StockBalance.product_id == product_id,
        )
        .first()
    )
    issued = abs(float(qty)) - need
    if bal:
        bal.qty = max(0.0, float(bal.qty or 0) - issued)

    if need > 0.0001:
        # No/partial batches — issue remainder from balance only
        if bal:
            bal.qty = max(0.0, float(bal.qty or 0) - need)
        db.add(
            StockMove(
                company_id=company_id,
                product_id=product_id,
                warehouse_id=warehouse_id,
                qty=-need,
                move_type="issue",
                ref=ref,
                notes="Issue (no batch / FEFO remainder)",
            )
        )
        splits.append({"batch_id": None, "batch_no": None, "qty": need, "expiry": None})

    return splits


def bill_wise_ar(db: Session, company_id: int, customer_id: int | None = None) -> list[dict[str, Any]]:
    q = db.query(Invoice).filter(Invoice.company_id == company_id)
    if customer_id:
        q = q.filter(Invoice.customer_id == customer_id)
    rows = []
    for inv in q.order_by(Invoice.invoice_date, Invoice.id).all():
        if (inv.invoice_type or "sales") == "credit":
            continue
        bal = round(float(inv.total or 0) - float(inv.paid or 0), 2)
        if bal <= 0.01:
            continue
        cust = db.get(Customer, inv.customer_id)
        rows.append(
            {
                "invoice_id": inv.id,
                "number": inv.number,
                "date": inv.invoice_date.isoformat() if inv.invoice_date else None,
                "due_date": inv.due_date.isoformat() if inv.due_date else None,
                "party": cust.name if cust else "",
                "customer_id": inv.customer_id,
                "total": inv.total,
                "paid": inv.paid,
                "balance": bal,
            }
        )
    return rows


def bill_wise_ap(db: Session, company_id: int, vendor_id: int | None = None) -> list[dict[str, Any]]:
    q = db.query(PurchaseInvoice).filter(PurchaseInvoice.company_id == company_id)
    if vendor_id:
        q = q.filter(PurchaseInvoice.vendor_id == vendor_id)
    rows = []
    for inv in q.order_by(PurchaseInvoice.id).all():
        bal = round(float(inv.total or 0) - float(inv.paid or 0), 2)
        if bal <= 0.01:
            continue
        v = db.get(Vendor, inv.vendor_id)
        rows.append(
            {
                "purchase_invoice_id": inv.id,
                "number": inv.number,
                "party": v.name if v else "",
                "vendor_id": inv.vendor_id,
                "total": inv.total,
                "paid": inv.paid,
                "balance": bal,
            }
        )
    return rows


def company_gstin(db: Session, company_id: int) -> str | None:
    co = db.get(Company, company_id)
    return co.gstin if co else None


def books_based_pnl(db: Session, company_id: int) -> dict[str, Any]:
    income = 0.0
    cogs = 0.0
    expenses = 0.0
    for j in db.query(JournalEntry).filter(JournalEntry.company_id == company_id, JournalEntry.status == "posted").all():
        for ln in j.lines or []:
            code = str(ln.get("account_code") or "")
            dr = float(ln.get("debit") or 0)
            cr = float(ln.get("credit") or 0)
            if code.startswith("4"):
                income += cr - dr
            elif code == "5100":
                cogs += dr - cr
            elif code.startswith("5"):
                expenses += dr - cr
    income = round(income, 2)
    cogs = round(cogs, 2)
    expenses = round(expenses, 2)
    gross = round(income - cogs, 2)
    net = round(gross - expenses, 2)
    return {
        "income": income,
        "cogs": cogs,
        "gross_profit": gross,
        "expenses": expenses,
        "net_profit": net,
        "source": "books_journals",
    }


def vendor_pi_outstanding(db: Session, company_id: int) -> list[dict[str, Any]]:
    rows = []
    for inv in db.query(PurchaseInvoice).filter(PurchaseInvoice.company_id == company_id).all():
        bal = max(0.0, float(inv.total or 0) - float(inv.paid or 0))
        if bal <= 0.01:
            continue
        v = db.get(Vendor, inv.vendor_id)
        rows.append(
            {
                "party": v.name if v else f"Vendor#{inv.vendor_id}",
                "ref": inv.number,
                "total": inv.total,
                "paid": inv.paid,
                "balance": round(bal, 2),
            }
        )
    return rows
