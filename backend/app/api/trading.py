from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func

from app.core.deps import CurrentUser, DbDep, audit, next_number
from app.core.modules import gst_split
from app.models import (
    Account,
    Customer,
    Delivery,
    GodownTransfer,
    GoodsReceipt,
    Invoice,
    JournalEntry,
    Lead,
    MaterialIndent,
    MaterialIssue,
    Opportunity,
    Payment,
    PhysicalStock,
    Product,
    PurchaseInvoice,
    PurchaseOrder,
    Quotation,
    SalesOrder,
    StockBalance,
    StockMove,
    StoreReceive,
    Vendor,
    Warehouse,
)

router = APIRouter(prefix="/api", tags=["trading"])


def _line_totals(lines: list[dict]) -> tuple[float, float, float]:
    subtotal = 0.0
    tax = 0.0
    for ln in lines:
        qty = float(ln.get("qty", 0))
        rate = float(ln.get("rate", 0))
        disc = float(ln.get("discount_pct", 0) or 0)
        amt = qty * rate * (1.0 - disc / 100.0)
        ln["amount"] = round(amt, 2)
        gst = float(ln.get("gst_rate", 18))
        tax += amt * gst / 100.0
        subtotal += amt
    return round(subtotal, 2), round(tax, 2), round(subtotal + tax, 2)


def _normalize_so_lines(lines: list[dict] | None) -> list[dict]:
    """Ensure ordered_qty / delivered_qty / bal_qty for SBAC pending-challan logic."""
    out: list[dict] = []
    for raw in lines or []:
        ln = dict(raw)
        ordered = float(ln.get("ordered_qty", ln.get("qty", 0)) or 0)
        delivered = float(ln.get("delivered_qty", 0) or 0)
        ln["ordered_qty"] = ordered
        ln["delivered_qty"] = delivered
        ln["qty"] = ordered  # display/order qty
        ln["bal_qty"] = round(max(0.0, ordered - delivered), 4)
        out.append(ln)
    return out


def _so_qty_summary(lines: list[dict]) -> dict:
    total_qty = sum(float(l.get("ordered_qty", l.get("qty", 0)) or 0) for l in lines)
    bal_qty = sum(float(l.get("bal_qty", 0) or 0) for l in lines)
    delivered_qty = sum(float(l.get("delivered_qty", 0) or 0) for l in lines)
    return {
        "total_qty": round(total_qty, 4),
        "bal_qty": round(bal_qty, 4),
        "delivered_qty": round(delivered_qty, 4),
    }


def _post_sales_journal(
    db: Any,
    *,
    company_id: int,
    inv: Invoice,
    party_name: str = "",
) -> None:
    sales_acc = db.query(Account).filter(Account.company_id == company_id, Account.code == "4100").first()
    ar_acc = db.query(Account).filter(Account.company_id == company_id, Account.code == "1300").first()
    gst_acc = db.query(Account).filter(Account.company_id == company_id, Account.code == "2200").first()
    if not (sales_acc and ar_acc):
        return
    db.add(
        JournalEntry(
            company_id=company_id,
            number=next_number(db, company_id, JournalEntry, "SV"),
            entry_date=date.today(),
            narration=f"Sales invoice {inv.number}",
            lines=[
                {"account_id": ar_acc.id, "account_code": "1300", "debit": inv.total, "credit": 0},
                {"account_id": sales_acc.id, "account_code": "4100", "debit": 0, "credit": inv.subtotal},
                {
                    "account_id": gst_acc.id if gst_acc else sales_acc.id,
                    "account_code": "2200",
                    "debit": 0,
                    "credit": inv.tax,
                },
            ],
            status="posted",
            voucher_type="sales",
            party_name=party_name,
        )
    )


# ── CRM ──────────────────────────────────────────────────────────────────────


class LeadIn(BaseModel):
    name: str
    company_name: str | None = None
    email: str | None = None
    phone: str | None = None
    source: str = "web"
    stage: str = "new"
    value: float = 0
    notes: str = ""
    custom: dict[str, Any] = Field(default_factory=dict)


@router.get("/crm/leads")
def list_leads(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(Lead).filter(Lead.company_id == user.company_id).order_by(Lead.id.desc()).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "company_name": r.company_name,
            "email": r.email,
            "phone": r.phone,
            "source": r.source,
            "stage": r.stage,
            "value": r.value,
            "notes": r.notes,
            "custom": r.custom,
        }
        for r in rows
    ]


@router.post("/crm/leads")
def create_lead(body: LeadIn, user: CurrentUser, db: DbDep) -> dict:
    row = Lead(company_id=user.company_id, owner_id=user.id, **body.model_dump())
    db.add(row)
    audit(db, company_id=user.company_id, user_id=user.id, action="create", entity="lead")
    db.commit()
    db.refresh(row)
    return {"id": row.id, **body.model_dump()}


@router.get("/crm/customers")
def list_customers(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(Customer).filter(Customer.company_id == user.company_id).all()
    return [
        {
            "id": c.id,
            "code": c.code,
            "name": c.name,
            "email": c.email,
            "phone": c.phone,
            "gstin": c.gstin,
            "billing_address": c.billing_address,
            "custom": c.custom,
            "party_type": getattr(c, "party_type", "customer") or "customer",
            "is_dealer": bool(getattr(c, "is_dealer", False)),
            "credit_limit": float(getattr(c, "credit_limit", 0) or 0),
            "price_list_code": getattr(c, "price_list_code", "STANDARD") or "STANDARD",
            "region": getattr(c, "region", "") or "",
        }
        for c in rows
    ]


class CustomerIn(BaseModel):
    name: str
    code: str | None = None
    email: str | None = None
    phone: str | None = None
    gstin: str | None = None
    billing_address: str = ""
    party_type: str = "customer"  # customer/dealer/vendor + SBAC Domestic/Export via custom.party_nature
    region: str = ""
    credit_limit: float = 0
    custom: dict[str, Any] = Field(default_factory=dict)


def _customer_out(row: Customer) -> dict:
    return {
        "id": row.id,
        "code": row.code,
        "name": row.name,
        "email": row.email,
        "phone": row.phone,
        "gstin": row.gstin,
        "billing_address": row.billing_address,
        "party_type": row.party_type,
        "is_dealer": bool(getattr(row, "is_dealer", False)),
        "region": row.region,
        "credit_limit": float(row.credit_limit or 0),
        "price_list_code": getattr(row, "price_list_code", "STANDARD") or "STANDARD",
        "custom": row.custom or {},
        "active": bool(row.active),
    }


@router.post("/crm/customers")
def create_customer(body: CustomerIn, user: CurrentUser, db: DbDep) -> dict:
    code = body.code or next_number(db, user.company_id, Customer, "CUST")
    data = body.model_dump(exclude={"code"})
    custom = dict(data.pop("custom") or {})
    custom["source"] = custom.get("source") or "kanha_party_master"
    # credit_limit may also live in custom from form
    if custom.get("credit_limit") and not data.get("credit_limit"):
        try:
            data["credit_limit"] = float(custom.get("credit_limit") or 0)
        except Exception:
            pass
    if custom.get("price_list"):
        data["price_list_code"] = str(custom.get("price_list") or "STANDARD")[:64]
    row = Customer(
        company_id=user.company_id,
        code=code,
        is_dealer=str(data.get("party_type") or "").lower() in ("dealer", "distributor"),
        custom=custom,
        **{k: v for k, v in data.items() if k != "custom"},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    out = _customer_out(row)
    out["message"] = f"Party {row.code} saved"
    return out


@router.put("/crm/customers/{customer_id}")
def update_customer(customer_id: int, body: CustomerIn, user: CurrentUser, db: DbDep) -> dict:
    row = db.query(Customer).filter(Customer.id == customer_id, Customer.company_id == user.company_id).first()
    if not row:
        raise HTTPException(404, "Party not found")
    data = body.model_dump(exclude={"code"})
    custom_extra = dict(data.pop("custom") or {})
    for k, v in data.items():
        if k in ("name", "email", "phone", "gstin", "billing_address", "party_type", "region", "credit_limit"):
            setattr(row, k, v)
    prev = dict(row.custom or {})
    prev.update(custom_extra)
    prev["source"] = prev.get("source") or "kanha_party_master"
    row.custom = prev
    row.is_dealer = str(row.party_type or "").lower() in ("dealer", "distributor")
    if custom_extra.get("price_list"):
        row.price_list_code = str(custom_extra.get("price_list") or row.price_list_code or "STANDARD")[:64]
    try:
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(row, "custom")
    except Exception:
        pass
    db.commit()
    db.refresh(row)
    out = _customer_out(row)
    out["message"] = f"Party {row.code} updated"
    return out


class GstLookupIn(BaseModel):
    gstin: str


@router.post("/crm/gst-lookup")
def gst_lookup(body: GstLookupIn, user: CurrentUser, db: DbDep) -> dict:
    """SBAC-style GST Search — demo fill from GSTIN pattern (live GSP later)."""
    gstin = (body.gstin or "").strip().upper()
    if len(gstin) < 10:
        raise HTTPException(400, "Enter valid GSTIN")
    # State code from first 2 digits (common IN pattern)
    state_map = {
        "07": "Delhi",
        "09": "Uttar Pradesh",
        "22": "Chhattisgarh",
        "23": "Madhya Pradesh",
        "24": "Gujarat",
        "27": "Maharashtra",
        "29": "Karnataka",
        "33": "Tamil Nadu",
        "36": "Telangana",
        "08": "Rajasthan",
    }
    st = state_map.get(gstin[:2], "Chhattisgarh")
    trade = f"Party {gstin[2:7] or 'DEMO'}"
    return {
        "ok": True,
        "gstin": gstin,
        "legal_name": trade,
        "trade_name": trade,
        "party_nature": "Domestic",
        "billing_address": f"GST registered address · {st}",
        "state": st,
        "city": "",
        "pincode": "",
        "demo": True,
        "message": f"GST Search · {gstin} (demo fill — live GSP when keyed)",
    }


@router.get("/crm/opportunities")
def list_opps(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(Opportunity).filter(Opportunity.company_id == user.company_id).all()
    out = []
    for o in rows:
        cust = db.get(Customer, o.customer_id) if o.customer_id else None
        lead = db.get(Lead, o.lead_id) if o.lead_id else None
        out.append(
            {
                "id": o.id,
                "title": o.title,
                "stage": o.stage,
                "amount": o.amount,
                "probability": o.probability,
                "lead_id": o.lead_id,
                "lead_name": lead.name if lead else "",
                "customer_id": o.customer_id,
                "customer_name": cust.name if cust else "",
                "close_date": o.close_date.isoformat() if o.close_date else None,
            }
        )
    return out


class OppIn(BaseModel):
    title: str
    stage: str = "prospect"
    amount: float = 0
    probability: int = 20
    lead_id: int | None = None
    customer_id: int | None = None


@router.post("/crm/opportunities")
def create_opp(body: OppIn, user: CurrentUser, db: DbDep) -> dict:
    row = Opportunity(
        company_id=user.company_id,
        title=body.title,
        stage=body.stage,
        amount=body.amount,
        probability=body.probability,
        lead_id=body.lead_id,
        customer_id=body.customer_id,
        close_date=date.today(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "title": row.title, "stage": row.stage, "amount": row.amount}


@router.get("/crm/quotations")
def list_quotes(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(Quotation).filter(Quotation.company_id == user.company_id).order_by(Quotation.id.desc()).all()
    out = []
    for q in rows:
        cust = db.get(Customer, q.customer_id) if q.customer_id else None
        lead = db.get(Lead, q.lead_id) if q.lead_id else None
        out.append(
            {
                "id": q.id,
                "number": q.number,
                "customer_id": q.customer_id,
                "customer_name": cust.name if cust else "",
                "lead_id": q.lead_id,
                "lead_name": lead.name if lead else "",
                "status": q.status,
                "subtotal": q.subtotal,
                "tax": q.tax,
                "total": q.total,
                "lines": q.lines,
            }
        )
    return out


class QuoteIn(BaseModel):
    customer_id: int | None = None
    lead_id: int | None = None
    lines: list[dict[str, Any]]
    status: str = "draft"


@router.post("/crm/quotations")
def create_quote(body: QuoteIn, user: CurrentUser, db: DbDep) -> dict:
    sub, tax, total = _line_totals(body.lines)
    row = Quotation(
        company_id=user.company_id,
        number=next_number(db, user.company_id, Quotation, "QT"),
        customer_id=body.customer_id,
        lead_id=body.lead_id,
        status=body.status,
        subtotal=sub,
        tax=tax,
        total=total,
        lines=body.lines,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "number": row.number, "subtotal": sub, "tax": tax, "total": total}


@router.post("/crm/flow/lead-to-quote/{lead_id}")
def flow_lead_to_quote(lead_id: int, user: CurrentUser, db: DbDep) -> dict:
    """Live Flow step: convert lead → customer (if needed) → quotation."""
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.company_id == user.company_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")
    cust = (
        db.query(Customer)
        .filter(Customer.company_id == user.company_id, Customer.name == (lead.company_name or lead.name))
        .first()
    )
    if not cust:
        cust = Customer(
            company_id=user.company_id,
            code=next_number(db, user.company_id, Customer, "CUST"),
            name=lead.company_name or lead.name,
            email=lead.email,
            phone=lead.phone,
        )
        db.add(cust)
        db.flush()
    products = db.query(Product).filter(Product.company_id == user.company_id, Product.sale_price > 0).limit(2).all()
    if not products:
        raise HTTPException(400, "No sellable products")
    lines = [
        {
            "product_id": p.id,
            "sku": p.sku,
            "name": p.name,
            "qty": 5,
            "rate": p.sale_price,
            "gst_rate": p.gst_rate,
            "amount": 5 * p.sale_price,
        }
        for p in products
    ]
    sub, tax, total = _line_totals(lines)
    quote = Quotation(
        company_id=user.company_id,
        number=next_number(db, user.company_id, Quotation, "QT"),
        customer_id=cust.id,
        lead_id=lead.id,
        status="sent",
        subtotal=sub,
        tax=tax,
        total=total,
        lines=lines,
    )
    lead.stage = "won"
    db.add(quote)
    db.commit()
    db.refresh(quote)
    return {
        "customer_id": cust.id,
        "quotation": {"id": quote.id, "number": quote.number, "total": quote.total},
        "message": "Lead converted to quotation",
    }


# ── Sales ────────────────────────────────────────────────────────────────────


@router.get("/sales/orders")
def list_orders(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(SalesOrder).filter(SalesOrder.company_id == user.company_id).order_by(SalesOrder.id.desc()).all()
    out = []
    for o in rows:
        cust = db.get(Customer, o.customer_id) if o.customer_id else None
        lines = _normalize_so_lines(list(o.lines or []))
        qty = _so_qty_summary(lines)
        out.append(
            {
                "id": o.id,
                "number": o.number,
                "customer_id": o.customer_id,
                "customer_name": cust.name if cust else "",
                "status": o.status,
                "approval_status": o.approval_status,
                "subtotal": o.subtotal,
                "tax": o.tax,
                "total": o.total,
                "lines": lines,
                "quotation_id": o.quotation_id,
                "warehouse_id": o.warehouse_id,
                "custom": getattr(o, "custom", None) or {},
                **qty,
            }
        )
    return out


class SOLineIn(BaseModel):
    product_id: int | None = None
    sku: str = ""
    name: str = ""
    qty: float = 1
    rate: float = 0  # sale rate used for billing
    gst_rate: float = 18
    mrp: float = 0
    discount_pct: float = 0
    billing_unit: str = ""
    convert_value: float = 0
    special_rate: float = 0
    item_description: str = ""


class SOChargeIn(BaseModel):
    nature: str = "Add"  # Less / Add
    other_type: str = ""
    tax_percent: float = 0
    amount: float = 0


class SalesOrderIn(BaseModel):
    customer_id: int
    warehouse_id: int | None = None
    lines: list[SOLineIn]
    remarks: str = ""
    customer_order_no: str = ""
    delivery_type: str = ""
    transport: str = ""
    bill_to: str = ""
    ship_to: str = ""
    mobile: str = ""
    gstin: str = ""
    order_date: str = ""
    delivery_date: str = ""
    entry_type: str = "Direct Entry Type"
    series_type: str = "Main"
    quotation_ref: str = ""
    terms: str = "100% Payment Against Proforma Invoice."
    executive: str = ""
    cc: str = ""
    exemption: str = "No"
    amc_status: str = ""
    attachment_note: str = ""
    other_tax: float = 0
    charges: list[SOChargeIn] = Field(default_factory=list)


@router.post("/sales/orders")
def create_sales_order(body: SalesOrderIn, user: CurrentUser, db: DbDep) -> dict:
    """Create Sales Order with lines (SBAC Create Sales Order — fresh entry)."""
    from app.services.ops_intelligence import OpsBlock, assert_credit_ok

    cust = db.query(Customer).filter(Customer.id == body.customer_id, Customer.company_id == user.company_id).first()
    if not cust:
        raise HTTPException(404, "Party not found")
    if not body.lines:
        raise HTTPException(400, "Add at least one item line")
    wh = None
    if body.warehouse_id:
        wh = db.query(Warehouse).filter(Warehouse.id == body.warehouse_id, Warehouse.company_id == user.company_id).first()
    if not wh:
        wh = db.query(Warehouse).filter(Warehouse.company_id == user.company_id).first()

    lines: list[dict] = []
    for raw in body.lines:
        ln = raw.model_dump()
        if raw.product_id:
            p = db.query(Product).filter(Product.id == raw.product_id, Product.company_id == user.company_id).first()
            if p:
                ln["sku"] = ln["sku"] or p.sku
                ln["name"] = ln["name"] or p.name
                if not ln.get("rate"):
                    ln["rate"] = float(p.sale_price or 0)
                if not ln.get("gst_rate"):
                    ln["gst_rate"] = float(p.gst_rate or 18)
                if not ln.get("billing_unit"):
                    ln["billing_unit"] = getattr(p, "uom", None) or "NOS"
        if float(ln.get("qty") or 0) <= 0:
            raise HTTPException(400, "Line qty must be > 0")
        lines.append(ln)

    lines = _normalize_so_lines(lines)
    sub, tax, total = _line_totals(lines)
    charges = [c.model_dump() for c in (body.charges or [])]
    charge_net = 0.0
    for ch in charges:
        amt = float(ch.get("amount") or 0)
        pct = float(ch.get("tax_percent") or 0)
        with_tax = amt + (amt * pct / 100.0)
        if str(ch.get("nature") or "Add").lower().startswith("less"):
            charge_net -= with_tax
        else:
            charge_net += with_tax
    other_tax = float(body.other_tax or 0)
    total = round(total + charge_net + other_tax, 2)
    try:
        credit = assert_credit_ok(db, user.company_id, cust.id, float(total))
    except OpsBlock as e:
        raise HTTPException(400, e.message) from e

    so = SalesOrder(
        company_id=user.company_id,
        number=next_number(db, user.company_id, SalesOrder, "SO"),
        customer_id=cust.id,
        status="confirmed",
        approval_status="approved" if total < 500000 else "pending",
        subtotal=sub,
        tax=tax,
        total=total,
        lines=lines,
        warehouse_id=wh.id if wh else None,
        custom={
            "remarks": body.remarks,
            "customer_order_no": body.customer_order_no,
            "delivery_type": body.delivery_type,
            "transport": body.transport,
            "bill_to": body.bill_to or (cust.billing_address or ""),
            "ship_to": body.ship_to or (cust.billing_address or ""),
            "mobile": body.mobile or (cust.phone or ""),
            "gstin": body.gstin or (cust.gstin or ""),
            "order_date": body.order_date or str(date.today()),
            "delivery_date": body.delivery_date,
            "entry_type": body.entry_type,
            "series_type": body.series_type,
            "quotation_ref": body.quotation_ref,
            "terms": body.terms,
            "executive": body.executive,
            "cc": body.cc,
            "exemption": body.exemption,
            "amc_status": body.amc_status,
            "attachment_note": body.attachment_note,
            "other_tax": other_tax,
            "charges": charges,
            "charge_net": round(charge_net, 2),
            "source": "kanha_sales_order",
            "sbac_parity": "2026-08-02-live",
        },
    )
    db.add(so)
    db.flush()
    approval_note = None
    try:
        from app.services.hierarchy_approvals import submit_approval

        if so.approval_status == "pending":
            submit_approval(
                db,
                company_id=user.company_id,
                requester=user,
                module="sales",
                entity_type="sales_order",
                entity_id=str(so.id),
                title=f"SO {so.number} needs approval",
                amount=float(so.total or 0),
                payload={"number": so.number},
            )
            approval_note = "queued"
    except Exception as exc:  # noqa: BLE001
        approval_note = f"approval_queue_error: {exc}"[:180]
    audit(db, company_id=user.company_id, user_id=user.id, action="create", entity="sales_order", entity_id=so.number)
    db.commit()
    db.refresh(so)
    qty = _so_qty_summary(lines)
    return {
        "id": so.id,
        "number": so.number,
        "status": so.status,
        "approval_status": so.approval_status,
        "subtotal": so.subtotal,
        "tax": so.tax,
        "total": so.total,
        "lines": lines,
        "custom": so.custom or {},
        "credit": credit,
        "approval_note": approval_note,
        **qty,
    }


@router.get("/sales/orders/pending-challan")
def pending_so_for_challan(user: CurrentUser, db: DbDep) -> list:
    """SBAC: Pending Sales Order for Delivery Challan (bal qty > 0)."""
    rows = (
        db.query(SalesOrder)
        .filter(
            SalesOrder.company_id == user.company_id,
            SalesOrder.status.in_(("confirmed", "partial", "draft")),
            SalesOrder.approval_status.in_(("approved", "none")),
        )
        .order_by(SalesOrder.id.desc())
        .all()
    )
    out = []
    for o in rows:
        lines = _normalize_so_lines(list(o.lines or []))
        qty = _so_qty_summary(lines)
        if qty["bal_qty"] <= 0:
            continue
        cust = db.get(Customer, o.customer_id) if o.customer_id else None
        out.append(
            {
                "id": o.id,
                "number": o.number,
                "order_date": (getattr(o, "custom", None) or {}).get("order_date") or "",
                "customer_id": o.customer_id,
                "customer_name": cust.name if cust else "",
                "status": o.status,
                "total": o.total,
                "lines": lines,
                "custom": getattr(o, "custom", None) or {},
                "warehouse_id": o.warehouse_id,
                **qty,
            }
        )
    return out


class ChallanFromSOIn(BaseModel):
    """Create Delivery Challan from SO — SBAC CreateNewDeliveryChallan fields."""

    lines: list[dict[str, Any]] = Field(default_factory=list)  # [{product_id|sku, qty, godown, no_of_packing}]
    series_type: str = "Main"
    challan_date: str = ""
    transport: str = ""
    godown: str = ""
    warehouse_id: int | None = None
    remarks: str = ""
    delivery_boy: str = ""
    destination: str = ""
    no_of_cart: str = ""
    delivery_type: str = ""
    terms: str = ""
    # Export block (same labels as Party/SO export)
    packing_charge: str = ""
    carriage_by: str = ""
    receipt_by: str = ""
    port_discharge: str = ""
    port_loading: str = ""
    lut_bond: str = ""
    final_dest: str = ""


@router.post("/sales/flow/order-to-challan/{order_id}")
def flow_order_to_challan(order_id: int, body: ChallanFromSOIn, user: CurrentUser, db: DbDep) -> dict:
    """Create Delivery Challan from SO balance qty (stock out, invoice later)."""
    from app.services.ops_intelligence import issue_fefo
    from app.services.period_lock import assert_period_open

    assert_period_open(db, user.company_id, date.today())
    so = db.query(SalesOrder).filter(SalesOrder.id == order_id, SalesOrder.company_id == user.company_id).first()
    if not so:
        raise HTTPException(404, "Order not found")
    if so.approval_status == "pending":
        raise HTTPException(423, f"SO {so.number} pending approval — cannot create challan")
    if so.approval_status == "rejected":
        raise HTTPException(400, f"SO {so.number} rejected")
    so_lines = _normalize_so_lines(list(so.lines or []))
    # Build challan lines from balance (or requested partial)
    want: dict[str, float] = {}
    for raw in body.lines or []:
        key = str(raw.get("product_id") or raw.get("sku") or "")
        if key:
            want[key] = float(raw.get("qty") or 0)

    challan_lines: list[dict] = []
    updated: list[dict] = []
    # optional per-line extras from form
    line_extra: dict[str, dict] = {}
    for raw in body.lines or []:
        key = str(raw.get("product_id") or raw.get("sku") or "")
        if key:
            line_extra[key] = raw

    for ln in so_lines:
        bal = float(ln.get("bal_qty") or 0)
        key_id = str(ln.get("product_id") or "")
        key_sku = str(ln.get("sku") or "")
        take = bal
        extra = line_extra.get(key_id) or line_extra.get(key_sku) or {}
        if body.lines:
            # If lines sent: only include those with qty; empty list means full balance (legacy)
            if not want and not line_extra:
                take = bal
            else:
                take = float(extra.get("qty") if extra else (want.get(key_id) or want.get(key_sku) or 0))
                take = min(float(take), bal)
        if take <= 0:
            updated.append(ln)
            continue
        cl = dict(ln)
        cl["qty"] = take
        cl["ordered_qty"] = float(ln.get("ordered_qty") or ln.get("qty") or 0)
        cl["no_of_packing"] = extra.get("no_of_packing") or ""
        cl["line_godown"] = extra.get("godown") or body.godown or ""
        disc = float(cl.get("discount_pct", 0) or 0)
        amt = take * float(cl.get("rate") or 0) * (1.0 - disc / 100.0)
        cl["amount"] = round(amt, 2)
        challan_lines.append(cl)
        ln["delivered_qty"] = round(float(ln.get("delivered_qty") or 0) + take, 4)
        ln["bal_qty"] = round(max(0.0, float(ln.get("ordered_qty") or 0) - float(ln["delivered_qty"])), 4)
        updated.append(ln)

    if not challan_lines:
        raise HTTPException(400, "No balance qty to challan")

    sub, tax, total = _line_totals(challan_lines)
    # Stock issue on challan (goods leave godown)
    fefo_splits: list = []
    wh_id = body.warehouse_id or so.warehouse_id
    if wh_id:
        for ln in challan_lines:
            pid = ln.get("product_id")
            qty = float(ln.get("qty") or 0)
            if not pid or qty <= 0:
                continue
            splits = issue_fefo(
                db,
                company_id=user.company_id,
                warehouse_id=int(wh_id),
                product_id=int(pid),
                qty=qty,
                ref=so.number,
            )
            fefo_splits.extend(splits)

    so_custom = getattr(so, "custom", None) or {}
    cust_row = db.get(Customer, so.customer_id) if so.customer_id else None
    delivery = Delivery(
        company_id=user.company_id,
        number=next_number(db, user.company_id, Delivery, "DC"),
        sales_order_id=so.id,
        status="dispatched",
        lines=challan_lines,
        custom={
            "series_type": body.series_type or "Main",
            "challan_date": body.challan_date or str(date.today()),
            "transport": body.transport or so_custom.get("transport", ""),
            "godown": body.godown or "",
            "warehouse_id": wh_id,
            "remarks": body.remarks,
            "delivery_boy": body.delivery_boy,
            "destination": body.destination,
            "no_of_cart": body.no_of_cart,
            "delivery_type": body.delivery_type or so_custom.get("delivery_type", ""),
            "terms": body.terms,
            "export": {
                "packing_charge": body.packing_charge,
                "carriage_by": body.carriage_by,
                "receipt_by": body.receipt_by,
                "port_discharge": body.port_discharge,
                "port_loading": body.port_loading,
                "lut_bond": body.lut_bond,
                "final_dest": body.final_dest,
            },
            "party_name": cust_row.name if cust_row else "",
            "bill_to": so_custom.get("bill_to", ""),
            "ship_to": so_custom.get("ship_to", ""),
            "stock_issued": True,
            "source": "kanha_delivery_challan",
            "sbac_parity": "2026-08-02-live",
            "subtotal": sub,
            "tax": tax,
            "total": total,
        },
    )
    so.lines = updated
    qty = _so_qty_summary(updated)
    so.status = "delivered" if qty["bal_qty"] <= 0 else "partial"
    try:
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(so, "lines")
    except Exception:
        pass
    db.add(delivery)
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="create",
        entity="delivery_challan",
        entity_id=delivery.number,
        detail={"so": so.number, "bal_qty": qty["bal_qty"]},
    )
    db.commit()
    db.refresh(delivery)
    cust = db.get(Customer, so.customer_id)
    return {
        "id": delivery.id,
        "number": delivery.number,
        "sales_order": so.number,
        "sales_order_id": so.id,
        "customer_name": cust.name if cust else "",
        "status": delivery.status,
        "subtotal": sub,
        "tax": tax,
        "total": total,
        "lines": challan_lines,
        "fefo": fefo_splits,
        "so_status": so.status,
        "so_bal_qty": qty["bal_qty"],
        "message": f"Challan {delivery.number} from {so.number}",
    }


@router.get("/sales/challans/pending-invoice")
def pending_challan_for_invoice(user: CurrentUser, db: DbDep) -> list:
    """SBAC: Pending Challan for Sales Invoice."""
    rows = (
        db.query(Delivery)
        .filter(
            Delivery.company_id == user.company_id,
            Delivery.status.in_(("dispatched", "draft", "packed", "delivered")),
        )
        .order_by(Delivery.id.desc())
        .all()
    )
    out = []
    for d in rows:
        if getattr(d, "invoice_id", None):
            continue
        if str(d.status or "").lower() == "invoiced":
            continue
        so = db.get(SalesOrder, d.sales_order_id) if d.sales_order_id else None
        cust = db.get(Customer, so.customer_id) if so else None
        lines = list(d.lines or [])
        sub, tax, total = _line_totals([dict(x) for x in lines])
        total_qty = sum(float(x.get("qty") or 0) for x in lines)
        out.append(
            {
                "id": d.id,
                "number": d.number,
                "challan_date": str(getattr(d, "created_at", "") or "")[:10],
                "sales_order": so.number if so else "",
                "sales_order_id": d.sales_order_id,
                "customer_id": so.customer_id if so else None,
                "customer_name": cust.name if cust else "—",
                "status": d.status,
                "total_qty": round(total_qty, 4),
                "total": total,
                "subtotal": sub,
                "tax": tax,
                "lines": lines,
                "custom": getattr(d, "custom", None) or {},
            }
        )
    return out


class InvoiceFromChallanIn(BaseModel):
    """Optional extras when converting Delivery Challan → Invoice."""

    invoice_date: str = ""
    series_type: str = "Main"
    remarks: str = ""
    terms: str = ""
    transport: str = ""
    delivery_type: str = ""
    eway_bill_no: str = ""
    truck_no: str = ""
    freight_mode: str = ""
    pay_mode: str = ""
    charges: list[SOChargeIn] = Field(default_factory=list)
    other_tax: float = 0
    payment_mode: str = ""
    payment_amount: float = 0
    transaction_no: str = ""
    transaction_date: str = ""
    payment_narration: str = ""


@router.post("/sales/flow/delivery-to-invoice/{delivery_id}")
def flow_delivery_to_invoice(
    delivery_id: int,
    user: CurrentUser,
    db: DbDep,
    body: InvoiceFromChallanIn | None = None,
) -> dict:
    """Create Sales Invoice from Delivery Challan (no second stock issue)."""
    from app.services.ops_intelligence import OpsBlock, assert_credit_ok, company_gstin, gst_for_party, post_cogs_issue
    from app.services.period_lock import assert_period_open

    body = body or InvoiceFromChallanIn()
    assert_period_open(db, user.company_id, date.today())
    d = db.query(Delivery).filter(Delivery.id == delivery_id, Delivery.company_id == user.company_id).first()
    if not d:
        raise HTTPException(404, "Challan not found")
    if getattr(d, "invoice_id", None) or str(d.status or "").lower() == "invoiced":
        raise HTTPException(400, f"Challan {d.number} already invoiced")
    so = db.get(SalesOrder, d.sales_order_id) if d.sales_order_id else None
    if not so:
        raise HTTPException(400, "Challan has no sales order")
    cust = db.get(Customer, so.customer_id)
    lines = [dict(x) for x in (d.lines or [])]
    if not lines:
        raise HTTPException(400, "Challan has no lines")
    sub, tax, total = _line_totals(lines)
    charges = [c.model_dump() for c in (body.charges or [])]
    charge_net = 0.0
    for ch in charges:
        amt = float(ch.get("amount") or 0)
        pct = float(ch.get("tax_percent") or 0)
        with_tax = amt + (amt * pct / 100.0)
        if str(ch.get("nature") or "Add").lower().startswith("less"):
            charge_net -= with_tax
        else:
            charge_net += with_tax
    other_tax = float(body.other_tax or 0)
    total = round(total + charge_net + other_tax, 2)
    try:
        credit = assert_credit_ok(db, user.company_id, so.customer_id, float(total))
    except OpsBlock as e:
        raise HTTPException(400, e.message) from e

    wh_id = so.warehouse_id or (getattr(d, "custom", None) or {}).get("warehouse_id")
    cogs = post_cogs_issue(
        db,
        company_id=user.company_id,
        warehouse_id=wh_id,
        lines=lines,
        ref=d.number,
        party_name=cust.name if cust else "",
    )
    d_custom = getattr(d, "custom", None) or {}
    so_custom = getattr(so, "custom", None) or {}
    inv_date = body.invoice_date or str(date.today())
    try:
        inv_d = date.fromisoformat(inv_date[:10])
    except Exception:
        inv_d = date.today()
    paid = float(body.payment_amount or 0)
    inv = Invoice(
        company_id=user.company_id,
        number=next_number(db, user.company_id, Invoice, "INV"),
        customer_id=so.customer_id,
        sales_order_id=so.id,
        status="posted",
        invoice_date=inv_d,
        due_date=inv_d,
        subtotal=sub,
        tax=tax,
        total=total,
        paid=paid,
        lines=lines,
        invoice_type="sales",
        custom={
            "entry_type": "DeliveryChallan",
            "series_type": body.series_type or "Main",
            "challan_no": d.number,
            "remarks": body.remarks or d_custom.get("remarks", ""),
            "terms": body.terms or so_custom.get("terms", ""),
            "transport": body.transport or d_custom.get("transport", ""),
            "delivery_type": body.delivery_type or d_custom.get("delivery_type", ""),
            "eway_bill_no": body.eway_bill_no,
            "truck_no": body.truck_no,
            "freight_mode": body.freight_mode,
            "pay_mode": body.pay_mode,
            "charges": charges,
            "other_tax": other_tax,
            "charge_net": round(charge_net, 2),
            "bill_to": so_custom.get("bill_to", ""),
            "ship_to": so_custom.get("ship_to", ""),
            "payment": {
                "mode": body.payment_mode,
                "amount": paid,
                "transaction_no": body.transaction_no,
                "transaction_date": body.transaction_date,
                "narration": body.payment_narration,
            },
            "source": "kanha_challan_invoice",
            "sbac_parity": "2026-08-02-live",
        },
    )
    db.add(inv)
    db.flush()
    if paid > 0 and cust:
        db.add(
            Payment(
                company_id=user.company_id,
                invoice_id=inv.id,
                party_type="customer",
                party_id=cust.id,
                amount=paid,
                method=body.payment_mode or body.pay_mode or "bank",
                reference=body.transaction_no or "",
                payment_date=inv_d,
                allocations=[{"invoice_id": inv.id, "amount": paid}],
            )
        )
    d.status = "invoiced"
    d.invoice_id = inv.id
    # If SO fully challaned and all DCs invoiced → SO invoiced
    so_lines = _normalize_so_lines(list(so.lines or []))
    qty = _so_qty_summary(so_lines)
    open_dc = (
        db.query(Delivery)
        .filter(
            Delivery.company_id == user.company_id,
            Delivery.sales_order_id == so.id,
            Delivery.id != d.id,
            Delivery.status.in_(("dispatched", "draft", "packed", "delivered")),
        )
        .count()
    )
    if qty["bal_qty"] <= 0 and open_dc == 0:
        so.status = "invoiced"
    _post_sales_journal(db, company_id=user.company_id, inv=inv, party_name=cust.name if cust else "")
    gst = gst_for_party(
        inv.subtotal,
        18,
        company_gstin=company_gstin(db, user.company_id),
        party_gstin=cust.gstin if cust else None,
    )
    db.commit()
    db.refresh(inv)
    return {
        "delivery_number": d.number,
        "invoice": {"id": inv.id, "number": inv.number, "total": inv.total, "tax": inv.tax},
        "gst": gst,
        "cogs": cogs,
        "credit": credit,
        "message": f"Invoice {inv.number} from challan {d.number}",
    }


class DirectInvoiceIn(BaseModel):
    customer_id: int
    warehouse_id: int | None = None
    lines: list[SOLineIn]
    bill_to: str = ""
    ship_to: str = ""
    remarks: str = ""
    terms: str = "100% Payment Against Proforma Invoice."
    entry_type: str = "Direct"  # Direct / DeliveryChallan
    series_type: str = "Main"
    invoice_date: str = ""
    mobile: str = ""
    gstin: str = ""
    agent: str = ""
    transport: str = ""
    no_of_cartoon: str = ""
    delivery_type: str = ""
    freight_mode: str = ""
    eway_bill_no: str = ""
    invoice_nature: str = "Domestic"  # Domestic / Export
    gr_no: str = ""
    gr_date: str = ""
    truck_no: str = ""
    pay_mode: str = ""
    transaction_type: str = ""
    transport_mode: str = ""
    eway_bill_type: str = ""
    dispatch_place: str = ""
    other_tax: float = 0
    charges: list[SOChargeIn] = Field(default_factory=list)
    # Optional on-invoice payment
    payment_mode: str = ""
    payment_amount: float = 0
    transaction_no: str = ""
    transaction_date: str = ""
    payment_narration: str = ""
    advance_adjust: float = 0
    jv_account: str = ""
    jv_type: str = ""  # Debit / Credit
    jv_amount: float = 0
    jv_trans_no: str = ""
    jv_date: str = ""
    jv_narration: str = ""


@router.post("/sales/invoices/direct")
def create_direct_invoice(body: DirectInvoiceIn, user: CurrentUser, db: DbDep) -> dict:
    """SBAC Direct Sales Invoice — skip SO/challan; stock + books in one step."""
    from app.services.ops_intelligence import OpsBlock, assert_credit_ok, company_gstin, gst_for_party, issue_fefo, post_cogs_issue
    from app.services.period_lock import assert_period_open

    assert_period_open(db, user.company_id, date.today())
    cust = db.query(Customer).filter(Customer.id == body.customer_id, Customer.company_id == user.company_id).first()
    if not cust:
        raise HTTPException(404, "Party not found")
    if not body.lines:
        raise HTTPException(400, "Add at least one item line")
    wh = None
    if body.warehouse_id:
        wh = db.query(Warehouse).filter(Warehouse.id == body.warehouse_id, Warehouse.company_id == user.company_id).first()
    if not wh:
        wh = db.query(Warehouse).filter(Warehouse.company_id == user.company_id).first()
    if not wh:
        raise HTTPException(400, "No godown / warehouse")

    lines: list[dict] = []
    for raw in body.lines:
        ln = raw.model_dump()
        if raw.product_id:
            p = db.query(Product).filter(Product.id == raw.product_id, Product.company_id == user.company_id).first()
            if p:
                ln["sku"] = ln["sku"] or p.sku
                ln["name"] = ln["name"] or p.name
                if not ln.get("rate"):
                    ln["rate"] = float(p.sale_price or 0)
                if not ln.get("gst_rate"):
                    ln["gst_rate"] = float(p.gst_rate or 18)
                if not ln.get("billing_unit"):
                    ln["billing_unit"] = getattr(p, "uom", None) or "NOS"
                ln["godown"] = wh.code
        if float(ln.get("qty") or 0) <= 0:
            raise HTTPException(400, "Line qty must be > 0")
        lines.append(ln)

    sub, tax, total = _line_totals(lines)
    charges = [c.model_dump() for c in (body.charges or [])]
    charge_net = 0.0
    for ch in charges:
        amt = float(ch.get("amount") or 0)
        pct = float(ch.get("tax_percent") or 0)
        with_tax = amt + (amt * pct / 100.0)
        if str(ch.get("nature") or "Add").lower().startswith("less"):
            charge_net -= with_tax
        else:
            charge_net += with_tax
    other_tax = float(body.other_tax or 0)
    total = round(total + charge_net + other_tax, 2)
    try:
        credit = assert_credit_ok(db, user.company_id, cust.id, float(total))
    except OpsBlock as e:
        raise HTTPException(400, e.message) from e

    fefo_splits: list = []
    for ln in lines:
        pid = ln.get("product_id")
        qty = float(ln.get("qty") or 0)
        if not pid or qty <= 0:
            continue
        splits = issue_fefo(
            db,
            company_id=user.company_id,
            warehouse_id=wh.id,
            product_id=int(pid),
            qty=qty,
            ref="DIR-INV",
        )
        fefo_splits.extend(splits)

    cogs = post_cogs_issue(
        db,
        company_id=user.company_id,
        warehouse_id=wh.id,
        lines=lines,
        ref="DIR-INV",
        party_name=cust.name,
    )
    inv_date = body.invoice_date or str(date.today())
    try:
        inv_d = date.fromisoformat(inv_date[:10])
    except Exception:
        inv_d = date.today()
    paid = float(body.payment_amount or 0)
    custom = {
        "entry_type": body.entry_type or "Direct",
        "series_type": body.series_type or "Main",
        "bill_to": body.bill_to or (cust.billing_address or ""),
        "ship_to": body.ship_to or (cust.billing_address or ""),
        "remarks": body.remarks,
        "terms": body.terms,
        "mobile": body.mobile or (cust.phone or ""),
        "gstin": body.gstin or (cust.gstin or ""),
        "agent": body.agent,
        "transport": body.transport,
        "no_of_cartoon": body.no_of_cartoon,
        "delivery_type": body.delivery_type,
        "freight_mode": body.freight_mode,
        "eway_bill_no": body.eway_bill_no,
        "invoice_nature": body.invoice_nature or "Domestic",
        "gr_no": body.gr_no,
        "gr_date": body.gr_date,
        "truck_no": body.truck_no,
        "pay_mode": body.pay_mode,
        "transaction_type": body.transaction_type,
        "transport_mode": body.transport_mode,
        "eway_bill_type": body.eway_bill_type,
        "dispatch_place": body.dispatch_place,
        "charges": charges,
        "other_tax": other_tax,
        "charge_net": round(charge_net, 2),
        "payment": {
            "mode": body.payment_mode,
            "amount": paid,
            "transaction_no": body.transaction_no,
            "transaction_date": body.transaction_date,
            "narration": body.payment_narration,
        },
        "advance_adjust": body.advance_adjust,
        "jv": {
            "account": body.jv_account,
            "type": body.jv_type,
            "amount": body.jv_amount,
            "trans_no": body.jv_trans_no,
            "date": body.jv_date,
            "narration": body.jv_narration,
        },
        "source": "kanha_direct_invoice",
        "sbac_parity": "2026-08-02-live",
    }
    inv = Invoice(
        company_id=user.company_id,
        number=next_number(db, user.company_id, Invoice, "INV"),
        customer_id=cust.id,
        sales_order_id=None,
        status="posted",
        invoice_date=inv_d,
        due_date=inv_d,
        subtotal=sub,
        tax=tax,
        total=total,
        paid=paid,
        lines=lines,
        invoice_type="sales",
        custom=custom,
    )
    db.add(inv)
    db.flush()
    if paid > 0:
        db.add(
            Payment(
                company_id=user.company_id,
                invoice_id=inv.id,
                party_type="customer",
                party_id=cust.id,
                amount=paid,
                method=body.payment_mode or body.pay_mode or "bank",
                reference=body.transaction_no or "",
                payment_date=inv_d,
                allocations=[{"invoice_id": inv.id, "amount": paid}],
            )
        )
    _post_sales_journal(db, company_id=user.company_id, inv=inv, party_name=cust.name)
    gst = gst_for_party(
        inv.subtotal,
        18,
        company_gstin=company_gstin(db, user.company_id),
        party_gstin=cust.gstin,
    )
    audit(db, company_id=user.company_id, user_id=user.id, action="create", entity="invoice", entity_id=inv.number)
    db.commit()
    db.refresh(inv)
    return {
        "id": inv.id,
        "number": inv.number,
        "total": inv.total,
        "tax": inv.tax,
        "subtotal": inv.subtotal,
        "paid": inv.paid,
        "lines": lines,
        "gst": gst,
        "cogs": cogs,
        "credit": credit,
        "fefo": fefo_splits,
        "message": f"Direct invoice {inv.number}",
        "custom": custom,
    }


@router.post("/sales/flow/quote-to-order/{quote_id}")
def flow_quote_to_order(quote_id: int, user: CurrentUser, db: DbDep) -> dict:
    from app.services.ops_intelligence import OpsBlock, assert_credit_ok

    q = db.query(Quotation).filter(Quotation.id == quote_id, Quotation.company_id == user.company_id).first()
    if not q or not q.customer_id:
        raise HTTPException(404, "Quotation not found")
    try:
        credit = assert_credit_ok(db, user.company_id, q.customer_id, float(q.total or 0))
    except OpsBlock as e:
        raise HTTPException(400, e.message) from e
    wh = db.query(Warehouse).filter(Warehouse.company_id == user.company_id).first()
    lines = _normalize_so_lines(list(q.lines or []))
    so = SalesOrder(
        company_id=user.company_id,
        number=next_number(db, user.company_id, SalesOrder, "SO"),
        customer_id=q.customer_id,
        quotation_id=q.id,
        status="confirmed",
        approval_status="approved" if q.total < 500000 else "pending",
        subtotal=q.subtotal,
        tax=q.tax,
        total=q.total,
        lines=lines,
        warehouse_id=wh.id if wh else None,
        custom={"source": "quote_to_order"},
    )
    q.status = "accepted"
    db.add(so)
    db.flush()
    # Hierarchy approval inbox (high-value SO)
    approval_note = None
    try:
        from app.services.hierarchy_approvals import submit_approval

        if so.approval_status == "pending":
            submit_approval(
                db,
                company_id=user.company_id,
                requester=user,
                module="sales",
                entity_type="sales_order",
                entity_id=str(so.id),
                title=f"SO {so.number} needs approval",
                amount=float(so.total or 0),
                payload={"number": so.number},
            )
            approval_note = "queued"
    except Exception as exc:  # noqa: BLE001
        approval_note = f"approval_queue_error: {exc}"[:180]
    db.commit()
    db.refresh(so)
    return {
        "id": so.id,
        "number": so.number,
        "total": so.total,
        "approval_status": so.approval_status,
        "credit": credit,
        "approval_note": approval_note,
    }


class SOApprovalIn(BaseModel):
    note: str = ""


@router.post("/sales/orders/{order_id}/approve")
def approve_sales_order(order_id: int, body: SOApprovalIn, user: CurrentUser, db: DbDep) -> dict:
    so = db.query(SalesOrder).filter(SalesOrder.id == order_id, SalesOrder.company_id == user.company_id).first()
    if not so:
        raise HTTPException(404, "Order not found")
    if so.approval_status == "approved":
        raise HTTPException(400, "Order already approved")
    if so.approval_status == "rejected":
        raise HTTPException(400, "Order was rejected — create a new SO")
    so.approval_status = "approved"
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="approve",
        entity="sales_order",
        entity_id=so.number,
        detail={"note": body.note or "Approved"},
    )
    db.commit()
    return {"id": so.id, "number": so.number, "approval_status": so.approval_status, "message": f"{so.number} approved"}


@router.post("/sales/orders/{order_id}/reject")
def reject_sales_order(order_id: int, body: SOApprovalIn, user: CurrentUser, db: DbDep) -> dict:
    so = db.query(SalesOrder).filter(SalesOrder.id == order_id, SalesOrder.company_id == user.company_id).first()
    if not so:
        raise HTTPException(404, "Order not found")
    if so.approval_status == "rejected":
        raise HTTPException(400, "Order already rejected")
    if so.status == "invoiced":
        raise HTTPException(400, "Invoiced order cannot be rejected")
    so.approval_status = "rejected"
    so.status = "cancelled"
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="reject",
        entity="sales_order",
        entity_id=so.number,
        detail={"note": body.note or "Rejected"},
    )
    db.commit()
    return {"id": so.id, "number": so.number, "approval_status": so.approval_status, "message": f"{so.number} rejected"}


@router.post("/sales/flow/order-to-invoice/{order_id}")
def flow_order_to_invoice(order_id: int, user: CurrentUser, db: DbDep) -> dict:
    from app.services.ops_intelligence import OpsBlock, assert_credit_ok, company_gstin, gst_for_party, issue_fefo, post_cogs_issue
    from app.services.period_lock import assert_period_open

    assert_period_open(db, user.company_id, date.today())
    so = db.query(SalesOrder).filter(SalesOrder.id == order_id, SalesOrder.company_id == user.company_id).first()
    if not so:
        raise HTTPException(404, "Order not found")
    if so.approval_status == "pending":
        raise HTTPException(
            423,
            f"Sales order {so.number} pending approval (≥ ₹5L threshold). Approve before invoicing.",
        )
    if so.approval_status == "rejected":
        raise HTTPException(400, f"Sales order {so.number} was rejected — cannot invoice")
    try:
        credit = assert_credit_ok(db, user.company_id, so.customer_id, float(so.total or 0))
    except OpsBlock as e:
        raise HTTPException(400, e.message) from e
    # Delivery + FEFO stock issue
    delivery = Delivery(
        company_id=user.company_id,
        number=next_number(db, user.company_id, Delivery, "DN"),
        sales_order_id=so.id,
        status="delivered",
        lines=so.lines,
    )
    db.add(delivery)
    fefo_splits = []
    if so.warehouse_id:
        for ln in so.lines or []:
            pid = ln.get("product_id")
            qty = float(ln.get("qty", 0))
            if not pid or qty <= 0:
                continue
            splits = issue_fefo(
                db,
                company_id=user.company_id,
                warehouse_id=so.warehouse_id,
                product_id=pid,
                qty=qty,
                ref=so.number,
            )
            fefo_splits.extend(splits)
    cust = db.get(Customer, so.customer_id)
    cogs = post_cogs_issue(
        db,
        company_id=user.company_id,
        warehouse_id=so.warehouse_id,
        lines=list(so.lines or []),
        ref=so.number,
        party_name=cust.name if cust else "",
    )
    inv = Invoice(
        company_id=user.company_id,
        number=next_number(db, user.company_id, Invoice, "INV"),
        customer_id=so.customer_id,
        sales_order_id=so.id,
        status="posted",
        invoice_date=date.today(),
        due_date=date.today(),
        subtotal=so.subtotal,
        tax=so.tax,
        total=so.total,
        paid=0,
        lines=so.lines,
    )
    so.status = "invoiced"
    # Auto journal
    sales_acc = db.query(Account).filter(Account.company_id == user.company_id, Account.code == "4100").first()
    ar_acc = db.query(Account).filter(Account.company_id == user.company_id, Account.code == "1300").first()
    gst_acc = db.query(Account).filter(Account.company_id == user.company_id, Account.code == "2200").first()
    if sales_acc and ar_acc:
        db.add(
            JournalEntry(
                company_id=user.company_id,
                number=next_number(db, user.company_id, JournalEntry, "SV"),
                entry_date=date.today(),
                narration=f"Sales invoice {inv.number}",
                lines=[
                    {"account_id": ar_acc.id, "account_code": "1300", "debit": inv.total, "credit": 0},
                    {"account_id": sales_acc.id, "account_code": "4100", "debit": 0, "credit": inv.subtotal},
                    {"account_id": gst_acc.id if gst_acc else sales_acc.id, "account_code": "2200", "debit": 0, "credit": inv.tax},
                ],
                status="posted",
                voucher_type="sales",
                party_name=cust.name if cust else "",
            )
        )
    db.add(inv)
    gst = gst_for_party(
        inv.subtotal,
        18,
        company_gstin=company_gstin(db, user.company_id),
        party_gstin=cust.gstin if cust else None,
    )
    db.commit()
    db.refresh(inv)
    tally_job = None
    try:
        from app.services.bridges import maybe_queue_tally_sales

        tally_job = maybe_queue_tally_sales(db, user.company_id, inv)
    except Exception:
        tally_job = None
    hook_push = None
    try:
        from app.services.connectors import push_event

        cust = db.get(Customer, inv.customer_id) if inv.customer_id else None
        hook_push = push_event(
            db,
            user.company_id,
            event="invoice.created",
            payload={
                "number": inv.number,
                "total": inv.total,
                "tax": inv.tax,
                "party": cust.name if cust else "",
                "gstin": cust.gstin if cust else "",
            },
        )
    except Exception:
        hook_push = None
    return {
        "delivery_number": delivery.number,
        "invoice": {"id": inv.id, "number": inv.number, "total": inv.total, "tax": inv.tax},
        "gst": gst,
        "cogs": cogs,
        "credit": credit,
        "fefo": fefo_splits,
        "bridge": {"tally": tally_job, "hooks": hook_push},
    }


# ── Scan Billing / POS (barcode-first) ───────────────────────────────────────


def _find_product_by_code(db, company_id: int, code: str) -> Product | None:
    raw = (code or "").strip()
    if not raw:
        return None
    p = (
        db.query(Product)
        .filter(Product.company_id == company_id, Product.barcode == raw, Product.active.is_(True))
        .first()
    )
    if p:
        return p
    return (
        db.query(Product)
        .filter(Product.company_id == company_id, Product.sku == raw, Product.active.is_(True))
        .first()
    )


@router.get("/inventory/products/lookup")
def product_lookup(code: str, user: CurrentUser, db: DbDep, warehouse_id: int | None = None) -> dict:
    p = _find_product_by_code(db, user.company_id, code)
    if not p:
        raise HTTPException(404, f"No product for barcode/SKU: {code}")
    q = db.query(func.coalesce(func.sum(StockBalance.qty), 0)).filter(
        StockBalance.company_id == user.company_id, StockBalance.product_id == p.id
    )
    if warehouse_id:
        q = q.filter(StockBalance.warehouse_id == warehouse_id)
    bal = float(q.scalar() or 0)
    return {
        "id": p.id,
        "sku": p.sku,
        "name": p.name,
        "barcode": p.barcode,
        "sale_price": p.sale_price,
        "gst_rate": p.gst_rate,
        "qty_on_hand": bal,
        "category": p.category,
        "custom": p.custom or {},
    }


class PosLineIn(BaseModel):
    barcode: str | None = None
    product_id: int | None = None
    qty: float = 1


class PosCheckoutIn(BaseModel):
    lines: list[PosLineIn]
    customer_id: int | None = None
    warehouse_id: int | None = None
    pay_now: bool = True
    method: str = "cash"
    reference: str = "POS"


@router.post("/sales/pos/checkout")
def pos_checkout(body: PosCheckoutIn, user: CurrentUser, db: DbDep) -> dict:
    from app.core.deps import assert_perm

    assert_perm(user, db, "pos.*", "sales.*")
    if not body.lines:
        raise HTTPException(400, "Scan at least one product")
    wh = None
    if body.warehouse_id:
        wh = db.query(Warehouse).filter(Warehouse.id == body.warehouse_id, Warehouse.company_id == user.company_id).first()
    if not wh:
        wh = db.query(Warehouse).filter(Warehouse.company_id == user.company_id).first()
    if not wh:
        raise HTTPException(400, "No warehouse")

    cust = None
    if body.customer_id:
        cust = db.query(Customer).filter(Customer.id == body.customer_id, Customer.company_id == user.company_id).first()
    if not cust:
        cust = (
            db.query(Customer)
            .filter(Customer.company_id == user.company_id, Customer.code == "WALKIN")
            .first()
        )
    if not cust:
        cust = db.query(Customer).filter(Customer.company_id == user.company_id).first()
    if not cust:
        raise HTTPException(400, "No customer — create Walk-in first")

    merged: dict[int, dict] = {}
    for raw in body.lines:
        p = None
        if raw.product_id:
            p = db.query(Product).filter(Product.id == raw.product_id, Product.company_id == user.company_id).first()
        elif raw.barcode:
            p = _find_product_by_code(db, user.company_id, raw.barcode)
        if not p:
            raise HTTPException(404, f"Product not found: {raw.barcode or raw.product_id}")
        qty = float(raw.qty or 1)
        if qty <= 0:
            raise HTTPException(400, "Qty must be > 0")
        if p.id in merged:
            merged[p.id]["qty"] += qty
        else:
            merged[p.id] = {
                "product_id": p.id,
                "sku": p.sku,
                "barcode": p.barcode,
                "name": p.name,
                "qty": qty,
                "rate": float(p.sale_price),
                "gst_rate": float(p.gst_rate or 18),
            }

    lines = list(merged.values())
    for ln in lines:
        bal = (
            db.query(StockBalance)
            .filter(
                StockBalance.company_id == user.company_id,
                StockBalance.warehouse_id == wh.id,
                StockBalance.product_id == ln["product_id"],
            )
            .first()
        )
        on_hand = float(bal.qty if bal else 0)
        if on_hand < ln["qty"]:
            raise HTTPException(400, f"Insufficient stock for {ln['sku']} (have {on_hand}, need {ln['qty']})")

    sub0, tax0, _total0 = _line_totals(lines)
    sub, tax, total = sub0, tax0, round(sub0 + tax0, 2)
    rule_meta: dict = {}
    try:
        from app.services.rules_engine import evaluate

        ev = evaluate(db, user.company_id, "pos_offer", {"order_total": sub0, "channel": "pos"})
        ev2 = evaluate(db, user.company_id, "discount", {"order_total": sub0, "channel": "pos"})
        actions = {**(ev2.get("actions") or {}), **(ev.get("actions") or {})}
        pct = float(actions.get("discount_pct") or 0)
        if pct > 0:
            factor = max(0.0, 1.0 - pct / 100.0)
            sub = round(sub0 * factor, 2)
            tax = round(tax0 * factor, 2)
            total = round(sub + tax, 2)
            rule_meta = {
                "discount_pct": pct,
                "label": actions.get("label") or "Rule offer",
                "rules_matched": (ev.get("count") or 0) + (ev2.get("count") or 0),
            }
    except Exception:
        rule_meta = {}
    inv = Invoice(
        company_id=user.company_id,
        number=next_number(db, user.company_id, Invoice, "POS"),
        customer_id=cust.id,
        sales_order_id=None,
        invoice_type="pos",
        status="posted",
        invoice_date=date.today(),
        due_date=date.today(),
        subtotal=sub,
        tax=tax,
        total=total,
        paid=0,
        lines=lines,
    )
    db.add(inv)
    db.flush()

    from app.services.ops_intelligence import issue_fefo, post_cogs_issue

    for ln in lines:
        issue_fefo(
            db,
            company_id=user.company_id,
            warehouse_id=wh.id,
            product_id=ln["product_id"],
            qty=float(ln["qty"]),
            ref=inv.number,
        )

    cogs = post_cogs_issue(
        db,
        company_id=user.company_id,
        warehouse_id=wh.id,
        lines=lines,
        ref=inv.number,
        party_name=cust.name if cust else "",
    )

    payment = None
    if body.pay_now:
        payment = Payment(
            company_id=user.company_id,
            invoice_id=inv.id,
            party_type="customer",
            party_id=cust.id,
            amount=total,
            method=body.method or "cash",
            reference=body.reference or "POS",
            payment_date=date.today(),
        )
        db.add(payment)
        inv.paid = total
        inv.status = "paid"

    sales_acc = db.query(Account).filter(Account.company_id == user.company_id, Account.code == "4100").first()
    ar_acc = db.query(Account).filter(Account.company_id == user.company_id, Account.code == "1300").first()
    gst_acc = db.query(Account).filter(Account.company_id == user.company_id, Account.code == "2200").first()
    cash_acc = db.query(Account).filter(Account.company_id == user.company_id, Account.code == "1100").first()
    if sales_acc and ar_acc:
        jlines = [
            {"account_id": ar_acc.id, "debit": inv.total, "credit": 0},
            {"account_id": sales_acc.id, "debit": 0, "credit": inv.subtotal},
            {"account_id": gst_acc.id if gst_acc else sales_acc.id, "debit": 0, "credit": inv.tax},
        ]
        if body.pay_now and cash_acc:
            jlines.append({"account_id": cash_acc.id, "debit": inv.total, "credit": 0})
            jlines.append({"account_id": ar_acc.id, "debit": 0, "credit": inv.total})
        db.add(
            JournalEntry(
                company_id=user.company_id,
                number=next_number(db, user.company_id, JournalEntry, "SV"),
                entry_date=date.today(),
                narration=f"POS invoice {inv.number}",
                lines=jlines,
                status="posted",
                voucher_type="sales",
                party_name="POS Walk-in",
            )
        )

    audit(db, company_id=user.company_id, user_id=user.id, action="pos_checkout", entity="invoice", entity_id=str(inv.id))
    db.commit()
    db.refresh(inv)
    return {
        "invoice": {
            "id": inv.id,
            "number": inv.number,
            "subtotal": inv.subtotal,
            "tax": inv.tax,
            "total": inv.total,
            "paid": inv.paid,
            "status": inv.status,
            "lines": inv.lines,
            "customer_id": cust.id,
            "customer": cust.name,
        },
        "payment": {"method": body.method, "amount": inv.paid} if body.pay_now else None,
        "gst": gst_split(inv.subtotal, 18),
        "cogs": cogs,
        "warehouse": wh.name,
        "rule_offer": rule_meta or None,
    }


@router.get("/sales/invoices")
def list_invoices(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(Invoice).filter(Invoice.company_id == user.company_id).order_by(Invoice.id.desc()).all()
    out = []
    for i in rows:
        cust = db.get(Customer, i.customer_id) if i.customer_id else None
        out.append(
            {
                "id": i.id,
                "number": i.number,
                "customer_id": i.customer_id,
                "customer_name": cust.name if cust else "",
                "customer_gstin": cust.gstin if cust else "",
                "customer_phone": cust.phone if cust else "",
                "customer_email": cust.email if cust else "",
                "customer_address": cust.billing_address if cust else "",
                "status": i.status,
                "invoice_date": i.invoice_date.isoformat() if i.invoice_date else None,
                "subtotal": i.subtotal,
                "tax": i.tax,
                "total": i.total,
                "paid": i.paid,
                "balance": round(i.total - i.paid, 2),
                "lines": i.lines or [],
                "invoice_type": i.invoice_type,
                "recurring": i.recurring,
                "against_invoice": next(
                    (ln.get("against_invoice") for ln in (i.lines or []) if isinstance(ln, dict) and ln.get("against_invoice")),
                    None,
                ),
            }
        )
    return out


class PaymentIn(BaseModel):
    invoice_id: int
    amount: float
    method: str = "bank"
    reference: str = ""
    gateway: str | None = None
    # Optional multi-bill: [{invoice_id, amount}] — if set, amount should match sum
    allocations: list[dict] | None = None


@router.post("/sales/payments")
def record_payment(body: PaymentIn, user: CurrentUser, db: DbDep) -> dict:
    from app.models import PaymentAllocation
    from app.services.period_lock import assert_period_open

    assert_period_open(db, user.company_id, date.today())
    inv = db.query(Invoice).filter(Invoice.id == body.invoice_id, Invoice.company_id == user.company_id).first()
    if not inv:
        raise HTTPException(404, "Invoice not found")
    if (inv.invoice_type or "sales") == "credit":
        raise HTTPException(400, "Cannot record payment against a credit note — use credit to settle invoice")
    amt = float(body.amount or 0)
    if amt <= 0:
        raise HTTPException(400, "amount must be > 0")

    allocs = list(body.allocations or [])
    if not allocs:
        # FIFO across open invoices for this customer if amount > this bill
        bal0 = max(0.0, float(inv.total) - float(inv.paid or 0))
        if amt <= bal0 + 0.01:
            allocs = [{"invoice_id": inv.id, "amount": amt}]
        else:
            remain = amt
            open_invs = (
                db.query(Invoice)
                .filter(
                    Invoice.company_id == user.company_id,
                    Invoice.customer_id == inv.customer_id,
                    Invoice.total > Invoice.paid,
                )
                .order_by(Invoice.invoice_date, Invoice.id)
                .all()
            )
            ordered = [inv] + [x for x in open_invs if x.id != inv.id and (x.invoice_type or "sales") != "credit"]
            for row in ordered:
                if remain <= 0.01:
                    break
                if (row.invoice_type or "sales") == "credit":
                    continue
                bal = max(0.0, float(row.total) - float(row.paid or 0))
                use = min(bal, remain)
                if use > 0:
                    allocs.append({"invoice_id": row.id, "amount": round(use, 2)})
                    remain = round(remain - use, 2)
            if remain > 0.01:
                raise HTTPException(400, f"Amount exceeds open customer bills by ₹{remain:,.2f}")
    alloc_sum = round(sum(float(a.get("amount") or 0) for a in allocs), 2)
    if abs(alloc_sum - amt) > 0.05:
        raise HTTPException(400, f"Allocations sum ₹{alloc_sum} must match payment ₹{amt}")

    pay = Payment(
        company_id=user.company_id,
        invoice_id=inv.id,
        party_type="customer",
        party_id=inv.customer_id,
        amount=amt,
        method=body.method,
        reference=body.reference,
        gateway=body.gateway,
        payment_date=date.today(),
        allocations=allocs,
    )
    db.add(pay)
    db.flush()

    applied = []
    for a in allocs:
        iid = int(a.get("invoice_id") or 0)
        aamt = float(a.get("amount") or 0)
        if aamt <= 0 or not iid:
            continue
        target = db.query(Invoice).filter(Invoice.id == iid, Invoice.company_id == user.company_id).first()
        if not target:
            raise HTTPException(404, f"Invoice {iid} not found for allocation")
        bal = max(0.0, float(target.total) - float(target.paid or 0))
        use = min(aamt, bal + 0.01)
        target.paid = min(target.total, float(target.paid or 0) + use)
        if target.paid >= target.total - 0.01:
            target.status = "paid"
            target.paid = target.total
        else:
            target.status = "partial"
        db.add(
            PaymentAllocation(
                company_id=user.company_id,
                payment_id=pay.id,
                invoice_id=target.id,
                amount=use,
            )
        )
        applied.append({"invoice": target.number, "amount": use, "balance": round(target.total - target.paid, 2)})

    # Receipt voucher: Dr Cash/Bank, Cr AR
    accounts = {
        a.code: a
        for a in db.query(Account).filter(Account.company_id == user.company_id, Account.is_group == False).all()  # noqa: E712
    }
    ar = accounts.get("1300")
    cash_bank = accounts.get("1200") if (body.method or "").lower() in ("bank", "upi", "card", "neft", "rtgs") else accounts.get("1100")
    cash_bank = cash_bank or accounts.get("1200") or accounts.get("1100")
    receipt_no = None
    if ar and cash_bank:
        cust = db.get(Customer, inv.customer_id) if inv.customer_id else None
        receipt_no = next_number(db, user.company_id, JournalEntry, "RCT")
        db.add(
            JournalEntry(
                company_id=user.company_id,
                number=receipt_no,
                entry_date=date.today(),
                narration=f"Receipt bill-wise · {body.method} · {', '.join(x['invoice'] for x in applied)}",
                lines=[
                    {"account_id": cash_bank.id, "account_code": cash_bank.code, "debit": amt, "credit": 0},
                    {"account_id": ar.id, "account_code": ar.code, "debit": 0, "credit": amt},
                ],
                status="posted",
                voucher_type="receipt",
                party_name=cust.name if cust else "",
            )
        )

    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="payment",
        entity="invoice",
        entity_id=str(inv.id),
        detail=f"amount={amt} bills={len(applied)}",
    )
    db.commit()
    bridge_job = None
    try:
        from app.services.bridges import enqueue, uses_bridge

        if uses_bridge(db, user.company_id, "accounting"):
            bridge_job = enqueue(
                db,
                user.company_id,
                channel="accounting",
                action="tally_receipt",
                title=f"Tally ← receipt {receipt_no or inv.number}",
                payload={"invoice": inv.number, "amount": amt, "journal": receipt_no, "allocations": applied},
            )
    except Exception:
        bridge_job = None
    return {
        "ok": True,
        "invoice_paid": inv.paid,
        "status": inv.status,
        "balance": round(inv.total - inv.paid, 2),
        "journal": receipt_no,
        "allocations": applied,
        "bridge": {"tally": bridge_job},
        "message": f"Paid ₹{amt:,.0f} across {len(applied)} bill(s)" + (f" · Books {receipt_no}" if receipt_no else ""),
    }


class CreditNoteIn(BaseModel):
    invoice_id: int
    reason: str = "Sales return / credit"
    return_stock: bool = True
    warehouse_id: int | None = None
    # Optional partial: if empty, full remaining balance / full invoice lines
    amount: float | None = None


@router.post("/sales/credit-notes")
def create_credit_note(body: CreditNoteIn, user: CurrentUser, db: DbDep) -> dict:
    """Credit note / sales return — protects collections honesty (top-ERP basic)."""
    from app.core.deps import assert_perm
    from app.services.period_lock import assert_period_open

    assert_perm(user, db, "sales.*", "accounting.*")
    assert_period_open(db, user.company_id, date.today())
    inv = db.query(Invoice).filter(Invoice.id == body.invoice_id, Invoice.company_id == user.company_id).first()
    if not inv:
        raise HTTPException(404, "Invoice not found")
    if (inv.invoice_type or "sales") == "credit":
        raise HTTPException(400, "Cannot credit a credit note")
    if inv.status in ("cancelled", "void"):
        raise HTTPException(400, "Invoice cancelled")

    # Amount: default = unpaid balance, else min(requested, total)
    balance = max(0.0, float(inv.total) - float(inv.paid or 0))
    credit_amt = float(body.amount) if body.amount is not None else (balance or float(inv.total))
    if credit_amt <= 0:
        raise HTTPException(400, "Nothing to credit")
    if credit_amt > float(inv.total) + 0.01:
        raise HTTPException(400, "Credit cannot exceed invoice total")

    ratio = credit_amt / float(inv.total) if inv.total else 1.0
    cn_lines = []
    for ln in inv.lines or []:
        row = dict(ln)
        qty = float(row.get("qty") or 0) * ratio
        rate = float(row.get("rate") or 0)
        row["qty"] = round(qty, 3)
        row["amount"] = round(qty * rate, 2)
        row["against_invoice_id"] = inv.id
        row["against_invoice"] = inv.number
        cn_lines.append(row)
    if not cn_lines:
        cn_lines = [
            {
                "sku": "CREDIT",
                "name": body.reason,
                "qty": 1,
                "rate": credit_amt,
                "amount": credit_amt,
                "gst_rate": 0,
                "against_invoice_id": inv.id,
                "against_invoice": inv.number,
            }
        ]

    sub = round(sum(float(x.get("amount") or 0) for x in cn_lines), 2)
    # Preserve tax proportion from original
    tax = round(float(inv.tax) * ratio, 2) if inv.total else 0
    total = round(credit_amt, 2)
    if abs(sub + tax - total) > 1:
        # force totals to credit_amt
        sub = round(total / 1.18, 2) if tax else total
        tax = round(total - sub, 2)

    cn = Invoice(
        company_id=user.company_id,
        number=next_number(db, user.company_id, Invoice, "CN"),
        customer_id=inv.customer_id,
        sales_order_id=inv.sales_order_id,
        invoice_type="credit",
        status="posted",
        invoice_date=date.today(),
        due_date=date.today(),
        subtotal=sub,
        tax=tax,
        total=total,
        paid=total,  # credit fully applied
        lines=cn_lines,
    )
    db.add(cn)
    db.flush()

    # Apply credit to original invoice outstanding
    apply = min(balance if balance > 0 else total, total)
    inv.paid = min(inv.total, float(inv.paid or 0) + apply)
    if inv.paid >= inv.total - 0.01:
        inv.status = "paid"
        inv.paid = inv.total

    # Stock return
    stock_back = []
    wh_id = body.warehouse_id
    if body.return_stock:
        if not wh_id:
            so = db.get(SalesOrder, inv.sales_order_id) if inv.sales_order_id else None
            wh_id = so.warehouse_id if so else None
            if not wh_id:
                wh = db.query(Warehouse).filter(Warehouse.company_id == user.company_id).first()
                wh_id = wh.id if wh else None
        if wh_id:
            for ln in cn_lines:
                pid = ln.get("product_id")
                qty = float(ln.get("qty") or 0)
                if not pid or qty <= 0:
                    continue
                bal = (
                    db.query(StockBalance)
                    .filter(
                        StockBalance.company_id == user.company_id,
                        StockBalance.warehouse_id == wh_id,
                        StockBalance.product_id == pid,
                    )
                    .first()
                )
                if not bal:
                    bal = StockBalance(
                        company_id=user.company_id,
                        warehouse_id=wh_id,
                        product_id=pid,
                        qty=0,
                        avg_cost=float(ln.get("rate") or 0),
                    )
                    db.add(bal)
                    db.flush()
                bal.qty += qty
                db.add(
                    StockMove(
                        company_id=user.company_id,
                        product_id=pid,
                        warehouse_id=wh_id,
                        qty=qty,
                        move_type="return",
                        ref=cn.number,
                        notes=f"Credit {cn.number} vs {inv.number}",
                    )
                )
                stock_back.append({"product_id": pid, "qty": qty})

    # GL reverse (simplified): Dr Sales / Cr AR
    accounts = {
        a.code: a
        for a in db.query(Account).filter(Account.company_id == user.company_id, Account.is_group == False).all()  # noqa: E712
    }
    ar = accounts.get("1300")
    sales = accounts.get("4100")
    gst = accounts.get("2200") or sales
    if ar and sales:
        jlines = [
            {"account_id": sales.id, "account_code": sales.code, "debit": sub, "credit": 0},
            {"account_id": ar.id, "account_code": ar.code, "debit": 0, "credit": total},
        ]
        if tax and gst:
            jlines.insert(1, {"account_id": gst.id, "account_code": gst.code, "debit": tax, "credit": 0})
            # rebalance AR credit already = total
        db.add(
            JournalEntry(
                company_id=user.company_id,
                number=next_number(db, user.company_id, JournalEntry, "JV"),
                entry_date=date.today(),
                narration=f"Credit note {cn.number} against {inv.number}: {body.reason}",
                lines=jlines,
                status="posted",
            )
        )

    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="credit_note",
        entity="invoice",
        entity_id=str(cn.id),
        detail=f"against={inv.number} amount={total}",
    )
    db.commit()
    db.refresh(cn)
    return {
        "ok": True,
        "credit_note": cn.number,
        "id": cn.id,
        "against": inv.number,
        "amount": total,
        "invoice_status": inv.status,
        "invoice_paid": inv.paid,
        "invoice_balance": round(inv.total - inv.paid, 2),
        "stock_returned": stock_back,
        "reason": body.reason,
        "message": f"Credit note {cn.number} · ₹{total:,.0f} against {inv.number}",
    }


# ── Inventory ────────────────────────────────────────────────────────────────


@router.get("/inventory/products")
def products(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(Product).filter(Product.company_id == user.company_id).all()
    out = []
    for p in rows:
        bal = (
            db.query(func.coalesce(func.sum(StockBalance.qty), 0))
            .filter(StockBalance.company_id == user.company_id, StockBalance.product_id == p.id)
            .scalar()
        )
        out.append(
            {
                "id": p.id,
                "sku": p.sku,
                "name": p.name,
                "category": p.category,
                "brand": p.brand,
                "sale_price": p.sale_price,
                "cost_price": p.cost_price,
                "gst_rate": p.gst_rate,
                "barcode": p.barcode,
                "uom": getattr(p, "uom", "NOS") or "NOS",
                "qty_on_hand": float(bal or 0),
                "custom": p.custom,
            }
        )
    return out


class ProductIn(BaseModel):
    sku: str
    name: str
    category: str = "General"
    brand: str = ""
    uom: str = "NOS"
    sale_price: float = 0
    cost_price: float = 0
    gst_rate: float = 18
    barcode: str | None = None
    custom: dict[str, Any] = Field(default_factory=dict)


@router.post("/inventory/products")
def create_product(body: ProductIn, user: CurrentUser, db: DbDep) -> dict:
    from app.core.deps import assert_perm
    assert_perm(user, db, "inventory.*", "settings.*")
    p = Product(company_id=user.company_id, **body.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return {"id": p.id, **body.model_dump()}


@router.get("/inventory/stock")
def stock(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(StockBalance).filter(StockBalance.company_id == user.company_id).all()
    out = []
    for s in rows:
        p = db.get(Product, s.product_id)
        w = db.get(Warehouse, s.warehouse_id)
        out.append(
            {
                "product_id": s.product_id,
                "sku": p.sku if p else "",
                "name": p.name if p else "",
                "warehouse": w.name if w else "",
                "qty": s.qty,
                "avg_cost": s.avg_cost,
                "value": round(s.qty * s.avg_cost, 2),
            }
        )
    return out


@router.get("/inventory/warehouses")
def warehouses(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(Warehouse).filter(Warehouse.company_id == user.company_id).all()
    return [{"id": w.id, "code": w.code, "name": w.name} for w in rows]


class AdjustIn(BaseModel):
    product_id: int
    warehouse_id: int
    qty: float
    notes: str = ""


@router.post("/inventory/adjust")
def adjust_stock(body: AdjustIn, user: CurrentUser, db: DbDep) -> dict:
    from app.core.deps import assert_perm
    assert_perm(user, db, "inventory.*", "settings.*")
    bal = (
        db.query(StockBalance)
        .filter(
            StockBalance.company_id == user.company_id,
            StockBalance.warehouse_id == body.warehouse_id,
            StockBalance.product_id == body.product_id,
        )
        .first()
    )
    if not bal:
        bal = StockBalance(
            company_id=user.company_id,
            warehouse_id=body.warehouse_id,
            product_id=body.product_id,
            qty=0,
            avg_cost=0,
        )
        db.add(bal)
        db.flush()
    bal.qty += body.qty
    db.add(
        StockMove(
            company_id=user.company_id,
            product_id=body.product_id,
            warehouse_id=body.warehouse_id,
            qty=body.qty,
            move_type="adjust",
            notes=body.notes,
        )
    )
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="adjust",
        entity="stock",
        entity_id=f"{body.product_id}@{body.warehouse_id}",
        detail=f"qty_delta={body.qty}",
    )
    db.commit()
    return {"qty": bal.qty}


class TransferIn(BaseModel):
    product_id: int
    from_warehouse_id: int
    to_warehouse_id: int
    qty: float
    notes: str = ""


@router.post("/inventory/transfer")
def transfer_stock(body: TransferIn, user: CurrentUser, db: DbDep) -> dict:
    """Inter-warehouse transfer — top-ERP basic that was missing."""
    from app.core.deps import assert_perm

    assert_perm(user, db, "inventory.*", "settings.*")
    qty = float(body.qty or 0)
    if qty <= 0:
        raise HTTPException(400, "qty must be > 0")
    if body.from_warehouse_id == body.to_warehouse_id:
        raise HTTPException(400, "from and to warehouse must differ")
    src_wh = db.get(Warehouse, body.from_warehouse_id)
    dst_wh = db.get(Warehouse, body.to_warehouse_id)
    prod = db.get(Product, body.product_id)
    if not prod or prod.company_id != user.company_id:
        raise HTTPException(404, "Product not found")
    if not src_wh or src_wh.company_id != user.company_id or not dst_wh or dst_wh.company_id != user.company_id:
        raise HTTPException(404, "Warehouse not found")

    src = (
        db.query(StockBalance)
        .filter(
            StockBalance.company_id == user.company_id,
            StockBalance.warehouse_id == body.from_warehouse_id,
            StockBalance.product_id == body.product_id,
        )
        .first()
    )
    if not src or src.qty < qty:
        raise HTTPException(400, f"Insufficient stock at {src_wh.code} (have {src.qty if src else 0})")

    dst = (
        db.query(StockBalance)
        .filter(
            StockBalance.company_id == user.company_id,
            StockBalance.warehouse_id == body.to_warehouse_id,
            StockBalance.product_id == body.product_id,
        )
        .first()
    )
    if not dst:
        dst = StockBalance(
            company_id=user.company_id,
            warehouse_id=body.to_warehouse_id,
            product_id=body.product_id,
            qty=0,
            avg_cost=src.avg_cost or 0,
        )
        db.add(dst)
        db.flush()

    src.qty -= qty
    dst.qty += qty
    if not dst.avg_cost and src.avg_cost:
        dst.avg_cost = src.avg_cost
    note = body.notes or f"Transfer {src_wh.code} → {dst_wh.code}"
    db.add(
        StockMove(
            company_id=user.company_id,
            product_id=body.product_id,
            warehouse_id=body.from_warehouse_id,
            qty=-qty,
            move_type="transfer_out",
            notes=note,
        )
    )
    db.add(
        StockMove(
            company_id=user.company_id,
            product_id=body.product_id,
            warehouse_id=body.to_warehouse_id,
            qty=qty,
            move_type="transfer_in",
            notes=note,
        )
    )
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="transfer",
        entity="stock",
        entity_id=str(body.product_id),
        detail=f"{qty} {src_wh.code}->{dst_wh.code}",
    )
    db.commit()
    return {
        "ok": True,
        "sku": prod.sku,
        "qty": qty,
        "from": {"id": src_wh.id, "code": src_wh.code, "qty": src.qty},
        "to": {"id": dst_wh.id, "code": dst_wh.code, "qty": dst.qty},
        "message": f"Transferred {qty} {prod.sku}: {src_wh.code} → {dst_wh.code}",
    }


@router.get("/inventory/moves")
def list_stock_moves(user: CurrentUser, db: DbDep, limit: int = 50) -> list:
    rows = (
        db.query(StockMove)
        .filter(StockMove.company_id == user.company_id)
        .order_by(StockMove.id.desc())
        .limit(min(limit, 200))
        .all()
    )
    out = []
    for m in rows:
        p = db.get(Product, m.product_id)
        w = db.get(Warehouse, m.warehouse_id)
        out.append(
            {
                "id": m.id,
                "sku": p.sku if p else "",
                "product": p.name if p else "",
                "warehouse": w.code if w else "",
                "qty": m.qty,
                "move_type": m.move_type,
                "notes": m.notes or "",
                "created_at": m.created_at.isoformat() if getattr(m, "created_at", None) else None,
            }
        )
    return out


# ── Store (Issue / Receive / Physical / Godown transfer) ─────────────────────


def _issue_stock_lines(
    db: Any,
    *,
    company_id: int,
    warehouse_id: int | None,
    lines: list[dict],
    ref: str,
) -> None:
    if not warehouse_id:
        raise HTTPException(400, "Godown required for stock issue")
    for ln in lines or []:
        pid = ln.get("product_id")
        qty = float(ln.get("qty", 0) or 0)
        if not pid or qty <= 0:
            continue
        bal = (
            db.query(StockBalance)
            .filter(
                StockBalance.company_id == company_id,
                StockBalance.warehouse_id == warehouse_id,
                StockBalance.product_id == int(pid),
            )
            .first()
        )
        on_hand = float(bal.qty if bal else 0)
        if on_hand < qty:
            p = db.get(Product, int(pid))
            sku = p.sku if p else str(pid)
            raise HTTPException(400, f"Insufficient stock for {sku} (have {on_hand}, need {qty})")
        bal.qty = on_hand - qty
        db.add(
            StockMove(
                company_id=company_id,
                product_id=int(pid),
                warehouse_id=warehouse_id,
                qty=-qty,
                move_type="issue",
                ref=ref,
                notes=ln.get("name") or "",
            )
        )


def _resolve_store_lines(db: Any, company_id: int, raw_lines: list[dict]) -> list[dict]:
    lines: list[dict] = []
    for raw in raw_lines or []:
        ln = dict(raw)
        pid = ln.get("product_id")
        if not pid:
            sku = (ln.get("sku") or "").strip()
            name = (ln.get("name") or ln.get("item") or "").strip()
            p = None
            if sku:
                p = db.query(Product).filter(Product.company_id == company_id, Product.sku == sku).first()
            if not p and name:
                p = db.query(Product).filter(Product.company_id == company_id, Product.name == name).first()
            if p:
                pid = p.id
                ln["product_id"] = p.id
                ln["sku"] = p.sku
                ln["name"] = p.name
        elif pid:
            p = db.query(Product).filter(Product.id == int(pid), Product.company_id == company_id).first()
            if p:
                ln["sku"] = ln.get("sku") or p.sku
                ln["name"] = ln.get("name") or p.name
        qty = float(ln.get("qty") or 0)
        if qty <= 0:
            raise HTTPException(400, "Line qty must be > 0")
        if not ln.get("product_id"):
            raise HTTPException(400, f"Item not linked to catalog: {ln.get('name') or ln.get('item') or 'line'}")
        lines.append(ln)
    if not lines:
        raise HTTPException(400, "Add at least one item line")
    return lines


class StoreLineIn(BaseModel):
    product_id: int | None = None
    sku: str = ""
    name: str = ""
    qty: float = 1
    uom: str = ""


class MaterialIssueIn(BaseModel):
    warehouse_id: int | None = None
    department: str = ""
    purpose: str = ""
    remarks: str = ""
    indent_id: int | None = None
    lines: list[dict[str, Any]]
    issue_date: str = ""
    issue_type: str = ""
    bill_no: str = ""
    party_name: str = ""
    issued_by: str = ""
    item_issue_type: str = ""  # Consumable / Returnable
    advance: float = 0


class StoreReceiveIn(BaseModel):
    warehouse_id: int | None = None
    source: str = "return"
    remarks: str = ""
    lines: list[dict[str, Any]]
    receive_date: str = ""
    receive_type: str = ""
    bill_no: str = ""
    party_name: str = ""
    advance: float = 0
    gst_amount: float = 0


class PhysicalStockIn(BaseModel):
    warehouse_id: int | None = None
    notes: str = ""
    lines: list[dict[str, Any]]  # product_id, counted_qty (system_qty filled server-side)
    count_date: str = ""
    branch: str = ""
    store_keeper: str = ""
    project_manager: str = ""


@router.get("/store/issues")
def list_material_issues(user: CurrentUser, db: DbDep) -> list:
    rows = (
        db.query(MaterialIssue)
        .filter(MaterialIssue.company_id == user.company_id)
        .order_by(MaterialIssue.id.desc())
        .limit(100)
        .all()
    )
    out = []
    for r in rows:
        wh = db.get(Warehouse, r.warehouse_id) if r.warehouse_id else None
        out.append(
            {
                "id": r.id,
                "number": r.number,
                "warehouse": wh.code if wh else "",
                "department": r.department,
                "purpose": r.purpose,
                "status": r.status,
                "lines": r.lines or [],
                "indent_id": r.indent_id,
                "custom": r.custom or {},
            }
        )
    return out


@router.post("/store/issues")
def create_material_issue(body: MaterialIssueIn, user: CurrentUser, db: DbDep) -> dict:
    """SBAC Material Issue — stock out from godown to dept/production."""
    from app.core.deps import assert_perm

    assert_perm(user, db, "inventory.*", "indents.*", "store.*")
    wh = None
    if body.warehouse_id:
        wh = db.query(Warehouse).filter(Warehouse.id == body.warehouse_id, Warehouse.company_id == user.company_id).first()
    if not wh:
        wh = db.query(Warehouse).filter(Warehouse.company_id == user.company_id).first()
    if not wh:
        raise HTTPException(400, "No godown")
    lines = _resolve_store_lines(db, user.company_id, body.lines)
    number = next_number(db, user.company_id, MaterialIssue, "MI")
    _issue_stock_lines(db, company_id=user.company_id, warehouse_id=wh.id, lines=lines, ref=number)
    row = MaterialIssue(
        company_id=user.company_id,
        number=number,
        warehouse_id=wh.id,
        indent_id=body.indent_id,
        department=body.department,
        purpose=body.purpose or "production",
        status="posted",
        lines=lines,
        custom={
            "remarks": body.remarks,
            "issue_date": body.issue_date or str(date.today()),
            "issue_type": body.issue_type,
            "bill_no": body.bill_no,
            "party_name": body.party_name,
            "issued_by": body.issued_by,
            "item_issue_type": body.item_issue_type,
            "advance": body.advance,
            "source": "kanha_material_issue",
            "sbac_parity": "2026-08-02-live",
        },
    )
    db.add(row)
    if body.indent_id:
        ind = db.query(MaterialIndent).filter(MaterialIndent.id == body.indent_id, MaterialIndent.company_id == user.company_id).first()
        if ind:
            # Mark indent issued for store path (purchase path uses to-pr separately)
            ind.status = "issued"
    audit(db, company_id=user.company_id, user_id=user.id, action="create", entity="material_issue", entity_id=number)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "number": row.number, "lines": lines, "message": f"Material Issue {row.number}"}


@router.get("/store/indents/pending-issue")
def pending_indents_for_issue(user: CurrentUser, db: DbDep) -> list:
    """Approved indents awaiting Material Issue (store path)."""
    rows = (
        db.query(MaterialIndent)
        .filter(MaterialIndent.company_id == user.company_id, MaterialIndent.status == "approved")
        .order_by(MaterialIndent.id.desc())
        .all()
    )
    out = []
    for r in rows:
        lines = list(r.lines or [])
        total_qty = sum(float(x.get("qty") or 0) for x in lines)
        out.append(
            {
                "id": r.id,
                "number": r.number,
                "purpose": r.purpose,
                "status": r.status,
                "notes": r.notes,
                "lines": lines,
                "total_qty": round(total_qty, 4),
            }
        )
    return out


@router.post("/store/flow/indent-to-issue/{indent_id}")
def flow_indent_to_issue(indent_id: int, body: MaterialIssueIn, user: CurrentUser, db: DbDep) -> dict:
    ind = db.query(MaterialIndent).filter(MaterialIndent.id == indent_id, MaterialIndent.company_id == user.company_id).first()
    if not ind:
        raise HTTPException(404, "Indent not found")
    if ind.status not in ("approved", "pending"):
        raise HTTPException(400, f"Indent {ind.number} status={ind.status} — cannot issue")
    if ind.status == "pending":
        ind.status = "approved"
    lines_src = body.lines if body.lines else list(ind.lines or [])
    payload = MaterialIssueIn(
        warehouse_id=body.warehouse_id,
        department=body.department or "Production",
        purpose=body.purpose or ind.purpose or "indent",
        remarks=body.remarks or ind.notes or "",
        indent_id=ind.id,
        lines=lines_src,
        issue_date=body.issue_date,
        issue_type=body.issue_type,
        bill_no=body.bill_no,
        party_name=body.party_name,
        issued_by=body.issued_by,
        item_issue_type=body.item_issue_type,
        advance=body.advance,
    )
    return create_material_issue(payload, user, db)


@router.get("/store/receives")
def list_store_receives(user: CurrentUser, db: DbDep) -> list:
    rows = (
        db.query(StoreReceive)
        .filter(StoreReceive.company_id == user.company_id)
        .order_by(StoreReceive.id.desc())
        .limit(100)
        .all()
    )
    out = []
    for r in rows:
        wh = db.get(Warehouse, r.warehouse_id) if r.warehouse_id else None
        out.append(
            {
                "id": r.id,
                "number": r.number,
                "warehouse": wh.code if wh else "",
                "source": r.source,
                "status": r.status,
                "lines": r.lines or [],
                "custom": r.custom or {},
            }
        )
    return out


@router.post("/store/receives")
def create_store_receive(body: StoreReceiveIn, user: CurrentUser, db: DbDep) -> dict:
    """Internal Material Receive / return to store."""
    from app.core.deps import assert_perm

    assert_perm(user, db, "inventory.*", "indents.*", "store.*")
    wh = None
    if body.warehouse_id:
        wh = db.query(Warehouse).filter(Warehouse.id == body.warehouse_id, Warehouse.company_id == user.company_id).first()
    if not wh:
        wh = db.query(Warehouse).filter(Warehouse.company_id == user.company_id).first()
    if not wh:
        raise HTTPException(400, "No godown")
    lines = _resolve_store_lines(db, user.company_id, body.lines)
    number = next_number(db, user.company_id, StoreReceive, "MR")
    _receive_stock_lines(db, company_id=user.company_id, warehouse_id=wh.id, lines=lines, ref=number)
    row = StoreReceive(
        company_id=user.company_id,
        number=number,
        warehouse_id=wh.id,
        source=body.source or "return",
        status="posted",
        lines=lines,
        custom={
            "remarks": body.remarks,
            "receive_date": body.receive_date or str(date.today()),
            "receive_type": body.receive_type,
            "bill_no": body.bill_no,
            "party_name": body.party_name,
            "advance": body.advance,
            "gst_amount": body.gst_amount,
            "source": "kanha_store_receive",
            "sbac_parity": "2026-08-02-live",
        },
    )
    db.add(row)
    audit(db, company_id=user.company_id, user_id=user.id, action="create", entity="store_receive", entity_id=number)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "number": row.number, "lines": lines, "message": f"Store Receive {row.number}"}


@router.get("/store/physical")
def list_physical_stock(user: CurrentUser, db: DbDep) -> list:
    rows = (
        db.query(PhysicalStock)
        .filter(PhysicalStock.company_id == user.company_id)
        .order_by(PhysicalStock.id.desc())
        .limit(100)
        .all()
    )
    out = []
    for r in rows:
        wh = db.get(Warehouse, r.warehouse_id) if r.warehouse_id else None
        out.append(
            {
                "id": r.id,
                "number": r.number,
                "warehouse": wh.code if wh else "",
                "status": r.status,
                "notes": r.notes,
                "lines": r.lines or [],
            }
        )
    return out


@router.get("/store/physical/pending-approval")
def pending_physical_approval(user: CurrentUser, db: DbDep) -> list:
    rows = (
        db.query(PhysicalStock)
        .filter(PhysicalStock.company_id == user.company_id, PhysicalStock.status == "draft")
        .order_by(PhysicalStock.id.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "number": r.number,
            "warehouse_id": r.warehouse_id,
            "status": r.status,
            "notes": r.notes,
            "lines": r.lines or [],
            "line_count": len(r.lines or []),
        }
        for r in rows
    ]


@router.post("/store/physical")
def create_physical_stock(body: PhysicalStockIn, user: CurrentUser, db: DbDep) -> dict:
    """Create physical count sheet (draft) — approve to post variance."""
    from app.core.deps import assert_perm

    assert_perm(user, db, "inventory.*", "store.*")
    wh = None
    if body.warehouse_id:
        wh = db.query(Warehouse).filter(Warehouse.id == body.warehouse_id, Warehouse.company_id == user.company_id).first()
    if not wh:
        wh = db.query(Warehouse).filter(Warehouse.company_id == user.company_id).first()
    if not wh:
        raise HTTPException(400, "No godown")
    if not body.lines:
        raise HTTPException(400, "Add count lines")
    lines: list[dict] = []
    for raw in body.lines:
        pid = raw.get("product_id")
        if not pid:
            continue
        p = db.query(Product).filter(Product.id == int(pid), Product.company_id == user.company_id).first()
        if not p:
            continue
        bal = (
            db.query(StockBalance)
            .filter(
                StockBalance.company_id == user.company_id,
                StockBalance.warehouse_id == wh.id,
                StockBalance.product_id == p.id,
            )
            .first()
        )
        system_qty = float(bal.qty if bal else 0)
        counted = float(raw.get("counted_qty", raw.get("qty", system_qty)) or 0)
        variance = round(counted - system_qty, 4)
        lines.append(
            {
                "product_id": p.id,
                "sku": p.sku,
                "name": p.name,
                "system_qty": system_qty,
                "counted_qty": counted,
                "variance": variance,
                "uom": getattr(p, "uom", None) or "NOS",
            }
        )
    if not lines:
        raise HTTPException(400, "No valid products in count")
    number = next_number(db, user.company_id, PhysicalStock, "PS")
    row = PhysicalStock(
        company_id=user.company_id,
        number=number,
        warehouse_id=wh.id,
        status="draft",
        lines=lines,
        notes=body.notes,
        custom={
            "source": "kanha_physical_stock",
            "count_date": body.count_date or str(date.today()),
            "branch": body.branch,
            "store_keeper": body.store_keeper,
            "project_manager": body.project_manager,
            "sbac_parity": "2026-08-02-live",
        },
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "number": row.number, "status": row.status, "lines": lines, "message": f"Physical Stock {row.number} (draft)"}


@router.post("/store/physical/{ps_id}/approve")
def approve_physical_stock(ps_id: int, user: CurrentUser, db: DbDep) -> dict:
    from app.core.deps import assert_perm

    assert_perm(user, db, "inventory.*", "store.*")
    row = db.query(PhysicalStock).filter(PhysicalStock.id == ps_id, PhysicalStock.company_id == user.company_id).first()
    if not row:
        raise HTTPException(404, "Physical stock not found")
    if row.status == "approved":
        raise HTTPException(400, "Already approved")
    wh_id = row.warehouse_id
    applied = 0
    for ln in row.lines or []:
        variance = float(ln.get("variance") or 0)
        pid = ln.get("product_id")
        if not pid or abs(variance) < 1e-9:
            continue
        bal = (
            db.query(StockBalance)
            .filter(
                StockBalance.company_id == user.company_id,
                StockBalance.warehouse_id == wh_id,
                StockBalance.product_id == int(pid),
            )
            .first()
        )
        if not bal:
            bal = StockBalance(
                company_id=user.company_id,
                warehouse_id=wh_id,
                product_id=int(pid),
                qty=0,
                avg_cost=0,
            )
            db.add(bal)
            db.flush()
        bal.qty = float(bal.qty or 0) + variance
        db.add(
            StockMove(
                company_id=user.company_id,
                product_id=int(pid),
                warehouse_id=wh_id,
                qty=variance,
                move_type="adjust",
                ref=row.number,
                notes=f"Physical variance · counted {ln.get('counted_qty')}",
            )
        )
        applied += 1
    row.status = "approved"
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="approve",
        entity="physical_stock",
        entity_id=row.number,
        detail={"lines_adjusted": applied},
    )
    db.commit()
    return {"id": row.id, "number": row.number, "status": row.status, "lines_adjusted": applied, "message": f"{row.number} approved · {applied} variance(s)"}


class GodownTransferDocIn(BaseModel):
    from_warehouse_id: int
    to_warehouse_id: int
    notes: str = ""
    lines: list[dict[str, Any]]


@router.get("/store/transfers")
def list_godown_transfers(user: CurrentUser, db: DbDep) -> list:
    rows = (
        db.query(GodownTransfer)
        .filter(GodownTransfer.company_id == user.company_id)
        .order_by(GodownTransfer.id.desc())
        .limit(100)
        .all()
    )
    out = []
    for r in rows:
        fw = db.get(Warehouse, r.from_warehouse_id)
        tw = db.get(Warehouse, r.to_warehouse_id)
        out.append(
            {
                "id": r.id,
                "number": r.number,
                "from_warehouse": fw.code if fw else "",
                "to_warehouse": tw.code if tw else "",
                "status": r.status,
                "notes": r.notes,
                "lines": r.lines or [],
            }
        )
    return out


@router.post("/store/godown-transfer")
def create_godown_transfer(body: GodownTransferDocIn, user: CurrentUser, db: DbDep) -> dict:
    """Multi-line godown transfer voucher."""
    from app.core.deps import assert_perm

    assert_perm(user, db, "inventory.*", "store.*")
    if body.from_warehouse_id == body.to_warehouse_id:
        raise HTTPException(400, "From and To godown must differ")
    src = db.query(Warehouse).filter(Warehouse.id == body.from_warehouse_id, Warehouse.company_id == user.company_id).first()
    dst = db.query(Warehouse).filter(Warehouse.id == body.to_warehouse_id, Warehouse.company_id == user.company_id).first()
    if not src or not dst:
        raise HTTPException(404, "Godown not found")
    lines = _resolve_store_lines(db, user.company_id, body.lines)
    number = next_number(db, user.company_id, GodownTransfer, "GT")
    # Stock out then in
    for ln in lines:
        pid = int(ln["product_id"])
        qty = float(ln["qty"])
        sbal = (
            db.query(StockBalance)
            .filter(
                StockBalance.company_id == user.company_id,
                StockBalance.warehouse_id == src.id,
                StockBalance.product_id == pid,
            )
            .first()
        )
        have = float(sbal.qty if sbal else 0)
        if have < qty:
            raise HTTPException(400, f"Insufficient stock for {ln.get('sku')} at {src.code} (have {have})")
        avg = float(sbal.avg_cost if sbal else 0)
        sbal.qty = have - qty
        db.add(
            StockMove(
                company_id=user.company_id,
                product_id=pid,
                warehouse_id=src.id,
                qty=-qty,
                move_type="transfer_out",
                ref=number,
                notes=body.notes,
            )
        )
        dbal = (
            db.query(StockBalance)
            .filter(
                StockBalance.company_id == user.company_id,
                StockBalance.warehouse_id == dst.id,
                StockBalance.product_id == pid,
            )
            .first()
        )
        if not dbal:
            dbal = StockBalance(
                company_id=user.company_id,
                warehouse_id=dst.id,
                product_id=pid,
                qty=0,
                avg_cost=avg,
            )
            db.add(dbal)
            db.flush()
        new_qty = float(dbal.qty or 0) + qty
        dbal.avg_cost = ((float(dbal.qty or 0) * float(dbal.avg_cost or 0)) + (qty * avg)) / new_qty if new_qty else avg
        dbal.qty = new_qty
        db.add(
            StockMove(
                company_id=user.company_id,
                product_id=pid,
                warehouse_id=dst.id,
                qty=qty,
                move_type="transfer_in",
                ref=number,
                notes=body.notes,
            )
        )
    row = GodownTransfer(
        company_id=user.company_id,
        number=number,
        from_warehouse_id=src.id,
        to_warehouse_id=dst.id,
        status="posted",
        lines=lines,
        notes=body.notes,
        custom={"source": "kanha_godown_transfer"},
    )
    db.add(row)
    audit(db, company_id=user.company_id, user_id=user.id, action="create", entity="godown_transfer", entity_id=number)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "number": row.number,
        "from": src.code,
        "to": dst.code,
        "lines": lines,
        "message": f"Transfer {row.number}: {src.code} → {dst.code}",
    }


# ── Purchase ─────────────────────────────────────────────────────────────────


def _normalize_po_lines(lines: list[dict] | None) -> list[dict]:
    """ordered_qty / received_qty / bal_qty for pending MRN/GRN."""
    out: list[dict] = []
    for raw in lines or []:
        ln = dict(raw)
        ordered = float(ln.get("ordered_qty", ln.get("qty", 0)) or 0)
        received = float(ln.get("received_qty", 0) or 0)
        ln["ordered_qty"] = ordered
        ln["received_qty"] = received
        ln["qty"] = ordered
        ln["bal_qty"] = round(max(0.0, ordered - received), 4)
        out.append(ln)
    return out


def _po_qty_summary(lines: list[dict]) -> dict:
    total_qty = sum(float(l.get("ordered_qty", l.get("qty", 0)) or 0) for l in lines)
    bal_qty = sum(float(l.get("bal_qty", 0) or 0) for l in lines)
    received_qty = sum(float(l.get("received_qty", 0) or 0) for l in lines)
    return {
        "total_qty": round(total_qty, 4),
        "bal_qty": round(bal_qty, 4),
        "received_qty": round(received_qty, 4),
    }


def _receive_stock_lines(
    db: Any,
    *,
    company_id: int,
    warehouse_id: int | None,
    lines: list[dict],
    ref: str,
) -> None:
    if not warehouse_id:
        return
    for ln in lines or []:
        pid = ln.get("product_id")
        qty = float(ln.get("qty", 0) or 0)
        rate = float(ln.get("rate", 0) or 0)
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
        if not bal:
            bal = StockBalance(
                company_id=company_id,
                warehouse_id=warehouse_id,
                product_id=int(pid),
                qty=0,
                avg_cost=rate,
            )
            db.add(bal)
            db.flush()
        new_qty = float(bal.qty or 0) + qty
        bal.avg_cost = ((float(bal.qty or 0) * float(bal.avg_cost or 0)) + (qty * rate)) / new_qty if new_qty else rate
        bal.qty = new_qty
        db.add(
            StockMove(
                company_id=company_id,
                product_id=int(pid),
                warehouse_id=warehouse_id,
                qty=qty,
                move_type="receipt",
                ref=ref,
            )
        )


def _post_purchase_journal(
    db: Any,
    *,
    company_id: int,
    pi: PurchaseInvoice,
    party_name: str = "",
    grn_number: str = "",
    rcm: bool = False,
) -> str | None:
    accounts = {
        a.code: a
        for a in db.query(Account).filter(Account.company_id == company_id, Account.is_group == False).all()  # noqa: E712
    }
    inv_acc = accounts.get("1400") or accounts.get("5100")
    itc_acc = accounts.get("2210") or accounts.get("2200")
    gst_out = accounts.get("2200")
    ap_acc = accounts.get("2100")
    if not (inv_acc and ap_acc and float(pi.total or 0) > 0):
        return None
    sub = float(pi.subtotal or 0)
    tax = float(pi.tax or 0)
    if rcm and tax > 0 and itc_acc and gst_out:
        lines = [
            {"account_id": inv_acc.id, "account_code": inv_acc.code, "debit": sub, "credit": 0},
            {"account_id": itc_acc.id, "account_code": itc_acc.code, "debit": tax, "credit": 0},
            {"account_id": ap_acc.id, "account_code": ap_acc.code, "debit": 0, "credit": sub},
            {"account_id": gst_out.id, "account_code": "2200", "debit": 0, "credit": tax},
        ]
        nar = f"RCM Purchase {pi.number}" + (f" · MRN {grn_number}" if grn_number else "")
    else:
        lines = [
            {"account_id": inv_acc.id, "account_code": inv_acc.code, "debit": sub, "credit": 0},
            {"account_id": ap_acc.id, "account_code": ap_acc.code, "debit": 0, "credit": float(pi.total or 0)},
        ]
        if tax > 0 and itc_acc:
            lines.insert(1, {"account_id": itc_acc.id, "account_code": itc_acc.code, "debit": tax, "credit": 0})
        elif tax > 0:
            lines[0]["debit"] = float(pi.total or 0)
        nar = f"Purchase {pi.number}" + (f" · MRN {grn_number}" if grn_number else "")
    journal_number = next_number(db, company_id, JournalEntry, "PV")
    db.add(
        JournalEntry(
            company_id=company_id,
            number=journal_number,
            entry_date=date.today(),
            narration=nar,
            lines=lines,
            status="posted",
            voucher_type="purchase",
            party_name=party_name,
        )
    )
    return journal_number


@router.get("/purchase/vendors")
def vendors(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(Vendor).filter(Vendor.company_id == user.company_id).all()
    return [
        {
            "id": v.id,
            "code": v.code,
            "name": v.name,
            "email": v.email,
            "phone": getattr(v, "phone", None),
            "gstin": v.gstin,
            "custom": getattr(v, "custom", None) or {},
        }
        for v in rows
    ]


class VendorIn(BaseModel):
    name: str
    code: str | None = None
    email: str | None = None
    phone: str | None = None
    gstin: str | None = None
    billing_address: str = ""
    under_account: str = "Sundry Creditors"
    whatsapp: str = ""
    transport: str = ""
    custom: dict[str, Any] = Field(default_factory=dict)


@router.post("/purchase/vendors")
def create_vendor(body: VendorIn, user: CurrentUser, db: DbDep) -> dict:
    n = db.query(Vendor).filter(Vendor.company_id == user.company_id).count() + 1
    code = body.code or f"VND-{n:03d}"
    custom = {
        **(body.custom or {}),
        "billing_address": body.billing_address,
        "under_account": body.under_account or "Sundry Creditors",
        "whatsapp": body.whatsapp or body.phone or "",
        "transport": body.transport,
        "source": "kanha_vendor_master",
    }
    row = Vendor(
        company_id=user.company_id,
        code=code,
        name=body.name,
        email=body.email,
        gstin=body.gstin,
        custom=custom,
    )
    if hasattr(row, "phone"):
        row.phone = body.phone or body.whatsapp or None
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "code": row.code,
        "name": row.name,
        "email": row.email,
        "phone": row.phone,
        "gstin": row.gstin,
        "custom": row.custom or {},
    }


@router.get("/purchase/orders")
def purchase_orders(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(PurchaseOrder).filter(PurchaseOrder.company_id == user.company_id).order_by(PurchaseOrder.id.desc()).all()
    out = []
    for o in rows:
        v = db.get(Vendor, o.vendor_id)
        lines = _normalize_po_lines(list(o.lines or []))
        qty = _po_qty_summary(lines)
        out.append(
            {
                "id": o.id,
                "number": o.number,
                "vendor_id": o.vendor_id,
                "vendor_name": v.name if v else "",
                "status": o.status,
                "subtotal": o.subtotal,
                "tax": o.tax,
                "total": o.total,
                "lines": lines,
                "warehouse_id": o.warehouse_id,
                "custom": getattr(o, "custom", None) or {},
                **qty,
            }
        )
    return out


class POIn(BaseModel):
    vendor_id: int
    lines: list[dict[str, Any]]
    warehouse_id: int | None = None
    remarks: str = ""
    vendor_po_ref: str = ""
    transport: str = ""
    bill_to: str = ""
    order_date: str = ""
    delivery_date: str = ""
    series_type: str = "Main"  # Main / RFQ
    party_type: str = "Sundry Creditors"
    freight_mode: str = ""
    narration: str = ""
    delivery_branch: str = ""
    booked_station: str = ""
    ship_branch: str = ""
    ship_to: str = ""
    state: str = ""
    agent: str = ""
    payment_mode: str = ""
    currency: str = "Indian Rupee (INR)"
    transporter_mode: str = ""
    godown: str = ""
    supplier_contact: str = ""
    delivery_person: str = ""
    delivery_contact: str = ""
    ref_no: str = ""
    behalf_of: str = ""
    order_duration: str = ""
    declaration: str = ""
    round_off: float = 0
    terms: str = ""
    other_tax: float = 0
    charges: list[SOChargeIn] = Field(default_factory=list)


@router.post("/purchase/orders")
def create_po(body: POIn, user: CurrentUser, db: DbDep) -> dict:
    vend = db.query(Vendor).filter(Vendor.id == body.vendor_id, Vendor.company_id == user.company_id).first()
    if not vend:
        raise HTTPException(404, "Vendor not found")
    if not body.lines:
        raise HTTPException(400, "Add at least one item line")
    wh = None
    if body.warehouse_id:
        wh = db.query(Warehouse).filter(Warehouse.id == body.warehouse_id, Warehouse.company_id == user.company_id).first()
    if not wh:
        wh = db.query(Warehouse).filter(Warehouse.company_id == user.company_id).first()

    lines: list[dict] = []
    for raw in body.lines:
        ln = dict(raw)
        pid = ln.get("product_id")
        if pid:
            p = db.query(Product).filter(Product.id == int(pid), Product.company_id == user.company_id).first()
            if p:
                ln["sku"] = ln.get("sku") or p.sku
                ln["name"] = ln.get("name") or p.name
                if not ln.get("rate"):
                    ln["rate"] = float(p.cost_price or p.sale_price or 0)
                if not ln.get("gst_rate"):
                    ln["gst_rate"] = float(p.gst_rate or 18)
                if not ln.get("billing_unit"):
                    ln["billing_unit"] = getattr(p, "uom", None) or "NOS"
        if float(ln.get("qty") or 0) <= 0:
            raise HTTPException(400, "Line qty must be > 0")
        lines.append(ln)

    lines = _normalize_po_lines(lines)
    sub, tax, total = _line_totals(lines)
    charges = [c.model_dump() for c in (body.charges or [])]
    charge_net = 0.0
    for ch in charges:
        amt = float(ch.get("amount") or 0)
        pct = float(ch.get("tax_percent") or 0)
        with_tax = amt + (amt * pct / 100.0)
        if str(ch.get("nature") or "Add").lower().startswith("less"):
            charge_net -= with_tax
        else:
            charge_net += with_tax
    other_tax = float(body.other_tax or 0)
    round_off = float(body.round_off or 0)
    total = round(total + charge_net + other_tax + round_off, 2)
    row = PurchaseOrder(
        company_id=user.company_id,
        number=next_number(db, user.company_id, PurchaseOrder, "PO"),
        vendor_id=body.vendor_id,
        status="ordered",
        subtotal=sub,
        tax=tax,
        total=total,
        lines=lines,
        warehouse_id=wh.id if wh else body.warehouse_id,
        custom={
            "remarks": body.remarks,
            "vendor_po_ref": body.vendor_po_ref or body.ref_no,
            "transport": body.transport,
            "bill_to": body.bill_to,
            "ship_to": body.ship_to,
            "order_date": body.order_date or str(date.today()),
            "delivery_date": body.delivery_date,
            "series_type": body.series_type or "Main",
            "party_type": body.party_type,
            "freight_mode": body.freight_mode,
            "narration": body.narration,
            "delivery_branch": body.delivery_branch,
            "booked_station": body.booked_station,
            "ship_branch": body.ship_branch,
            "state": body.state,
            "agent": body.agent,
            "payment_mode": body.payment_mode,
            "currency": body.currency,
            "transporter_mode": body.transporter_mode,
            "godown": body.godown,
            "supplier_contact": body.supplier_contact,
            "delivery_person": body.delivery_person,
            "delivery_contact": body.delivery_contact,
            "ref_no": body.ref_no,
            "behalf_of": body.behalf_of,
            "order_duration": body.order_duration,
            "declaration": body.declaration,
            "round_off": round_off,
            "terms": body.terms,
            "charges": charges,
            "other_tax": other_tax,
            "charge_net": round(charge_net, 2),
            "source": "kanha_purchase_order",
            "sbac_parity": "2026-08-02-live",
        },
    )
    db.add(row)
    audit(db, company_id=user.company_id, user_id=user.id, action="create", entity="purchase_order", entity_id=row.number)
    db.commit()
    db.refresh(row)
    qty = _po_qty_summary(lines)
    return {"id": row.id, "number": row.number, "total": total, "lines": lines, "custom": row.custom or {}, **qty}


@router.get("/purchase/orders/pending-grn")
def pending_po_for_grn(user: CurrentUser, db: DbDep) -> list:
    """SBAC: Pending PO for MRN/GRN (bal qty > 0)."""
    rows = (
        db.query(PurchaseOrder)
        .filter(
            PurchaseOrder.company_id == user.company_id,
            PurchaseOrder.status.in_(("ordered", "partial", "draft")),
        )
        .order_by(PurchaseOrder.id.desc())
        .all()
    )
    out = []
    for o in rows:
        lines = _normalize_po_lines(list(o.lines or []))
        qty = _po_qty_summary(lines)
        if qty["bal_qty"] <= 0:
            continue
        v = db.get(Vendor, o.vendor_id)
        out.append(
            {
                "id": o.id,
                "number": o.number,
                "order_date": (getattr(o, "custom", None) or {}).get("order_date") or "",
                "vendor_id": o.vendor_id,
                "vendor_name": v.name if v else "",
                "status": o.status,
                "total": o.total,
                "lines": lines,
                **qty,
            }
        )
    return out


class GRNFromPOIn(BaseModel):
    lines: list[dict[str, Any]] = Field(default_factory=list)
    remarks: str = ""
    transport: str = ""
    series_type: str = "Main"
    receipt_date: str = ""
    bill_no: str = ""
    bill_date: str = ""
    warehouse_id: int | None = None
    freight_mode: str = ""
    qc_status: str = "No"
    received_by: str = ""
    invoice_remarks: str = ""
    lot_no: str = ""
    gr_no: str = ""
    gr_date: str = ""
    total_wt: str = ""
    description: str = ""
    order_no: str = ""
    trans_id: str = ""
    other_tax: float = 0
    charges: list[SOChargeIn] = Field(default_factory=list)
    # optional payment / JV (stored on MRN; books on PI later)
    payment_mode: str = ""
    payment_amount: float = 0
    transaction_no: str = ""
    transaction_date: str = ""
    payment_narration: str = ""
    advance_adjust: float = 0
    bill_adjusted: bool = False
    jv_account: str = ""
    jv_type: str = ""
    jv_amount: float = 0
    jv_txn_no: str = ""
    jv_txn_date: str = ""
    jv_narration: str = ""
    mrn_type: str = "PO"  # Direct / PO


@router.post("/purchase/flow/po-to-grn/{po_id}")
def flow_po_to_grn(po_id: int, body: GRNFromPOIn, user: CurrentUser, db: DbDep) -> dict:
    """Create MRN/GRN from PO balance qty (stock in, invoice later)."""
    from app.core.deps import assert_perm
    from app.services.period_lock import assert_period_open

    assert_perm(user, db, "purchase.*", "inventory.*")
    assert_period_open(db, user.company_id, date.today())
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id, PurchaseOrder.company_id == user.company_id).first()
    if not po:
        raise HTTPException(404, "PO not found")
    po_lines = _normalize_po_lines(list(po.lines or []))
    want: dict[str, float] = {}
    for raw in body.lines or []:
        key = str(raw.get("product_id") or raw.get("sku") or "")
        if key:
            want[key] = float(raw.get("qty") or 0)

    grn_lines: list[dict] = []
    updated: list[dict] = []
    for ln in po_lines:
        bal = float(ln.get("bal_qty") or 0)
        key_id = str(ln.get("product_id") or "")
        key_sku = str(ln.get("sku") or "")
        take = bal
        if want:
            take = want.get(key_id) or want.get(key_sku) or 0.0
            take = min(float(take), bal)
        if take <= 0:
            updated.append(ln)
            continue
        gl = dict(ln)
        gl["qty"] = take
        # per-line extras from receive form
        for raw in body.lines or []:
            if str(raw.get("product_id") or "") == key_id or str(raw.get("sku") or "") == key_sku:
                if raw.get("godown"):
                    gl["godown"] = raw.get("godown")
                if raw.get("batch_no"):
                    gl["batch_no"] = raw.get("batch_no")
                if raw.get("no_of_packing"):
                    gl["no_of_packing"] = raw.get("no_of_packing")
                break
        disc = float(gl.get("discount_pct", 0) or 0)
        amt = take * float(gl.get("rate") or 0) * (1.0 - disc / 100.0)
        gl["amount"] = round(amt, 2)
        grn_lines.append(gl)
        ln["received_qty"] = round(float(ln.get("received_qty") or 0) + take, 4)
        ln["bal_qty"] = round(max(0.0, float(ln.get("ordered_qty") or 0) - float(ln["received_qty"])), 4)
        updated.append(ln)

    if not grn_lines:
        raise HTTPException(400, "No balance qty to receive")

    sub, tax, total = _line_totals(grn_lines)
    charges = [c.model_dump() for c in (body.charges or [])]
    charge_net = 0.0
    for ch in charges:
        amt = float(ch.get("amount") or 0)
        pct = float(ch.get("tax_percent") or 0)
        with_tax = amt + (amt * pct / 100.0)
        if str(ch.get("nature") or "Add").lower().startswith("less"):
            charge_net -= with_tax
        else:
            charge_net += with_tax
    other_tax = float(body.other_tax or 0)
    total = round(total + charge_net + other_tax, 2)

    wh_id = body.warehouse_id or po.warehouse_id
    _receive_stock_lines(
        db,
        company_id=user.company_id,
        warehouse_id=wh_id,
        lines=grn_lines,
        ref=po.number,
    )
    grn = GoodsReceipt(
        company_id=user.company_id,
        number=next_number(db, user.company_id, GoodsReceipt, "MRN"),
        purchase_order_id=po.id,
        status="received",
        lines=grn_lines,
        custom={
            "remarks": body.remarks or body.invoice_remarks,
            "transport": body.transport or (getattr(po, "custom", None) or {}).get("transport", ""),
            "warehouse_id": wh_id,
            "stock_received": True,
            "series_type": body.series_type or "Main",
            "receipt_date": body.receipt_date or str(date.today()),
            "bill_no": body.bill_no,
            "bill_date": body.bill_date,
            "freight_mode": body.freight_mode,
            "qc_status": body.qc_status or "No",
            "received_by": body.received_by,
            "invoice_remarks": body.invoice_remarks,
            "lot_no": body.lot_no,
            "gr_no": body.gr_no,
            "gr_date": body.gr_date,
            "total_wt": body.total_wt,
            "description": body.description,
            "order_no": body.order_no or po.number,
            "trans_id": body.trans_id,
            "charges": charges,
            "other_tax": other_tax,
            "charge_net": round(charge_net, 2),
            "subtotal": sub,
            "tax": tax,
            "total": total,
            "payment": {
                "mode": body.payment_mode,
                "amount": body.payment_amount,
                "transaction_no": body.transaction_no,
                "transaction_date": body.transaction_date,
                "narration": body.payment_narration,
                "advance_adjust": body.advance_adjust,
                "bill_adjusted": body.bill_adjusted,
            },
            "jv": {
                "account": body.jv_account,
                "type": body.jv_type,
                "amount": body.jv_amount,
                "txn_no": body.jv_txn_no,
                "txn_date": body.jv_txn_date,
                "narration": body.jv_narration,
            },
            "mrn_type": body.mrn_type or "PO",
            "source": "kanha_mrn",
            "sbac_parity": "2026-08-02-live",
        },
    )
    po.lines = updated
    qty = _po_qty_summary(updated)
    po.status = "received" if qty["bal_qty"] <= 0 else "partial"
    try:
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(po, "lines")
    except Exception:
        pass
    db.add(grn)
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="create",
        entity="goods_receipt",
        entity_id=grn.number,
        detail={"po": po.number, "bal_qty": qty["bal_qty"]},
    )
    db.commit()
    db.refresh(grn)
    vend = db.get(Vendor, po.vendor_id)
    return {
        "id": grn.id,
        "number": grn.number,
        "po_number": po.number,
        "purchase_order_id": po.id,
        "vendor_name": vend.name if vend else "",
        "status": grn.status,
        "subtotal": sub,
        "tax": tax,
        "total": total,
        "lines": grn_lines,
        "custom": grn.custom or {},
        "po_status": po.status,
        "po_bal_qty": qty["bal_qty"],
        "message": f"MRN {grn.number} from {po.number}",
    }


@router.get("/purchase/grn/pending-invoice")
def pending_grn_for_invoice(user: CurrentUser, db: DbDep) -> list:
    """SBAC: Pending MRN for Purchase Invoice."""
    rows = (
        db.query(GoodsReceipt)
        .filter(
            GoodsReceipt.company_id == user.company_id,
            GoodsReceipt.status.in_(("received", "draft")),
        )
        .order_by(GoodsReceipt.id.desc())
        .all()
    )
    out = []
    for g in rows:
        if getattr(g, "purchase_invoice_id", None):
            continue
        if str(g.status or "").lower() == "invoiced":
            continue
        po = db.get(PurchaseOrder, g.purchase_order_id) if g.purchase_order_id else None
        vend = db.get(Vendor, po.vendor_id) if po else None
        lines = list(g.lines or [])
        sub, tax, total = _line_totals([dict(x) for x in lines]) if lines else (0, 0, 0)
        total_qty = sum(float(x.get("qty") or 0) for x in lines)
        out.append(
            {
                "id": g.id,
                "number": g.number,
                "grn_date": str(getattr(g, "created_at", "") or "")[:10],
                "po_number": po.number if po else "",
                "purchase_order_id": g.purchase_order_id,
                "vendor_id": po.vendor_id if po else None,
                "vendor_name": vend.name if vend else "—",
                "status": g.status,
                "total_qty": round(total_qty, 4),
                "total": total,
                "subtotal": sub,
                "tax": tax,
                "lines": lines,
                "custom": getattr(g, "custom", None) or {},
            }
        )
    return out


class GRNInvoiceIn(BaseModel):
    rcm: bool = False
    series_type: str = "Main"
    invoice_date: str = ""
    bill_no: str = ""
    bill_date: str = ""
    freight_mode: str = ""
    qc_status: str = "No"
    received_by: str = ""
    invoice_remarks: str = ""
    remarks: str = ""
    lot_no: str = ""
    gr_no: str = ""
    gr_date: str = ""
    total_wt: str = ""
    description: str = ""
    transport: str = ""
    other_tax: float = 0
    round_off: float = 0
    charges: list[SOChargeIn] = Field(default_factory=list)
    payment_mode: str = ""
    payment_amount: float = 0
    transaction_no: str = ""
    transaction_date: str = ""
    payment_narration: str = ""
    advance_adjust: float = 0
    bill_adjusted: bool = False
    jv_account: str = ""
    jv_type: str = ""
    jv_amount: float = 0
    jv_txn_no: str = ""
    jv_txn_date: str = ""
    jv_narration: str = ""


@router.post("/purchase/flow/grn-to-invoice/{grn_id}")
def flow_grn_to_invoice(grn_id: int, body: GRNInvoiceIn, user: CurrentUser, db: DbDep) -> dict:
    """Create Purchase Invoice from MRN (books only — stock already in)."""
    from app.core.deps import assert_perm
    from app.services.period_lock import assert_period_open

    assert_perm(user, db, "purchase.*", "accounting.*")
    assert_period_open(db, user.company_id, date.today())
    grn = db.query(GoodsReceipt).filter(GoodsReceipt.id == grn_id, GoodsReceipt.company_id == user.company_id).first()
    if not grn:
        raise HTTPException(404, "MRN/GRN not found")
    if getattr(grn, "purchase_invoice_id", None) or str(grn.status or "").lower() == "invoiced":
        raise HTTPException(400, f"{grn.number} already invoiced")
    po = db.get(PurchaseOrder, grn.purchase_order_id) if grn.purchase_order_id else None
    if not po:
        raise HTTPException(400, "MRN has no purchase order")
    lines = [dict(x) for x in (grn.lines or [])]
    if not lines:
        raise HTTPException(400, "MRN has no lines")
    sub, tax, total = _line_totals(lines)
    charges = [c.model_dump() for c in (body.charges or [])]
    charge_net = 0.0
    for ch in charges:
        amt = float(ch.get("amount") or 0)
        pct = float(ch.get("tax_percent") or 0)
        with_tax = amt + (amt * pct / 100.0)
        if str(ch.get("nature") or "Add").lower().startswith("less"):
            charge_net -= with_tax
        else:
            charge_net += with_tax
    other_tax = float(body.other_tax or 0)
    round_off = float(body.round_off or 0)
    total = round(total + charge_net + other_tax + round_off, 2)
    rcm = bool(body.rcm)
    tot = float(sub + charge_net + other_tax + round_off) if rcm else float(total)
    grn_custom = getattr(grn, "custom", None) or {}
    custom = {
        "series_type": body.series_type or "Main",
        "invoice_date": body.invoice_date or str(date.today()),
        "bill_no": body.bill_no or grn_custom.get("bill_no", ""),
        "bill_date": body.bill_date or grn_custom.get("bill_date", ""),
        "freight_mode": body.freight_mode or grn_custom.get("freight_mode", ""),
        "qc_status": body.qc_status or grn_custom.get("qc_status", "No"),
        "received_by": body.received_by or grn_custom.get("received_by", ""),
        "invoice_remarks": body.invoice_remarks or body.remarks or grn_custom.get("invoice_remarks", ""),
        "remarks": body.remarks or body.invoice_remarks or "",
        "lot_no": body.lot_no or grn_custom.get("lot_no", ""),
        "gr_no": body.gr_no or grn_custom.get("gr_no", ""),
        "gr_date": body.gr_date or grn_custom.get("gr_date", ""),
        "total_wt": body.total_wt or grn_custom.get("total_wt", ""),
        "description": body.description or grn_custom.get("description", ""),
        "transport": body.transport or grn_custom.get("transport", ""),
        "charges": charges,
        "other_tax": other_tax,
        "round_off": round_off,
        "charge_net": round(charge_net, 2),
        "payment": {
            "mode": body.payment_mode,
            "amount": body.payment_amount,
            "transaction_no": body.transaction_no,
            "transaction_date": body.transaction_date,
            "narration": body.payment_narration,
            "advance_adjust": body.advance_adjust,
            "bill_adjusted": body.bill_adjusted,
        },
        "jv": {
            "account": body.jv_account,
            "type": body.jv_type,
            "amount": body.jv_amount,
            "txn_no": body.jv_txn_no,
            "txn_date": body.jv_txn_date,
            "narration": body.jv_narration,
        },
        "mrn_number": grn.number,
        "po_number": po.number,
        "source": "kanha_pi_from_mrn",
        "sbac_parity": "2026-08-02-live",
    }
    pi = PurchaseInvoice(
        company_id=user.company_id,
        number=next_number(db, user.company_id, PurchaseInvoice, "PINV"),
        vendor_id=po.vendor_id,
        purchase_order_id=po.id,
        status="posted",
        subtotal=sub,
        tax=tax,
        total=tot,
        lines=lines,
        rcm=rcm,
        custom=custom,
    )
    db.add(pi)
    db.flush()
    grn.status = "invoiced"
    grn.purchase_invoice_id = pi.id
    po_lines = _normalize_po_lines(list(po.lines or []))
    qty = _po_qty_summary(po_lines)
    open_grn = (
        db.query(GoodsReceipt)
        .filter(
            GoodsReceipt.company_id == user.company_id,
            GoodsReceipt.purchase_order_id == po.id,
            GoodsReceipt.id != grn.id,
            GoodsReceipt.status.in_(("received", "draft")),
        )
        .count()
    )
    if qty["bal_qty"] <= 0 and open_grn == 0:
        po.status = "invoiced"
    vend = db.get(Vendor, po.vendor_id)
    journal_number = _post_purchase_journal(
        db,
        company_id=user.company_id,
        pi=pi,
        party_name=vend.name if vend else "",
        grn_number=grn.number,
        rcm=rcm,
    )
    db.commit()
    db.refresh(pi)
    return {
        "grn": grn.number,
        "purchase_invoice": pi.number,
        "invoice": {
            "id": pi.id,
            "number": pi.number,
            "total": pi.total,
            "tax": pi.tax,
            "rcm": rcm,
            "custom": pi.custom or {},
        },
        "journal": journal_number,
        "rcm": rcm,
        "message": f"PI {pi.number} from MRN {grn.number}" + (" · RCM" if rcm else ""),
    }


class DirectPurchaseInvoiceIn(BaseModel):
    vendor_id: int
    warehouse_id: int | None = None
    lines: list[dict[str, Any]]
    rcm: bool = False
    remarks: str = ""
    series_type: str = "Main"
    invoice_date: str = ""
    bill_no: str = ""
    bill_date: str = ""
    freight_mode: str = ""
    qc_status: str = "No"
    received_by: str = ""
    invoice_remarks: str = ""
    lot_no: str = ""
    gr_no: str = ""
    gr_date: str = ""
    total_wt: str = ""
    description: str = ""
    transport: str = ""
    other_tax: float = 0
    round_off: float = 0
    charges: list[SOChargeIn] = Field(default_factory=list)
    payment_mode: str = ""
    payment_amount: float = 0
    transaction_no: str = ""
    transaction_date: str = ""
    payment_narration: str = ""
    advance_adjust: float = 0
    jv_account: str = ""
    jv_type: str = ""
    jv_amount: float = 0
    jv_txn_no: str = ""
    jv_txn_date: str = ""
    jv_narration: str = ""
    pi_type: str = "Direct"  # Direct / PO


@router.post("/purchase/invoices/direct")
def create_direct_purchase_invoice(body: DirectPurchaseInvoiceIn, user: CurrentUser, db: DbDep) -> dict:
    """Direct Purchase Invoice (cash/MRN skip) — stock + books."""
    from app.core.deps import assert_perm
    from app.services.period_lock import assert_period_open

    assert_perm(user, db, "purchase.*", "inventory.*")
    assert_period_open(db, user.company_id, date.today())
    vend = db.query(Vendor).filter(Vendor.id == body.vendor_id, Vendor.company_id == user.company_id).first()
    if not vend:
        raise HTTPException(404, "Vendor not found")
    if not body.lines:
        raise HTTPException(400, "Add at least one item line")
    wh = None
    if body.warehouse_id:
        wh = db.query(Warehouse).filter(Warehouse.id == body.warehouse_id, Warehouse.company_id == user.company_id).first()
    if not wh:
        wh = db.query(Warehouse).filter(Warehouse.company_id == user.company_id).first()
    if not wh:
        raise HTTPException(400, "No godown / warehouse")

    lines: list[dict] = []
    for raw in body.lines:
        ln = dict(raw)
        pid = ln.get("product_id")
        if pid:
            p = db.query(Product).filter(Product.id == int(pid), Product.company_id == user.company_id).first()
            if p:
                ln["sku"] = ln.get("sku") or p.sku
                ln["name"] = ln.get("name") or p.name
                if not ln.get("rate"):
                    ln["rate"] = float(p.cost_price or p.sale_price or 0)
                if not ln.get("gst_rate"):
                    ln["gst_rate"] = float(p.gst_rate or 18)
        if float(ln.get("qty") or 0) <= 0:
            raise HTTPException(400, "Line qty must be > 0")
        lines.append(ln)

    sub, tax, total = _line_totals(lines)
    charges = [c.model_dump() for c in (body.charges or [])]
    charge_net = 0.0
    for ch in charges:
        amt = float(ch.get("amount") or 0)
        pct = float(ch.get("tax_percent") or 0)
        with_tax = amt + (amt * pct / 100.0)
        if str(ch.get("nature") or "Add").lower().startswith("less"):
            charge_net -= with_tax
        else:
            charge_net += with_tax
    other_tax = float(body.other_tax or 0)
    round_off = float(body.round_off or 0)
    total = round(total + charge_net + other_tax + round_off, 2)
    rcm = bool(body.rcm)
    tot = float(sub + charge_net + other_tax + round_off) if rcm else float(total)
    _receive_stock_lines(db, company_id=user.company_id, warehouse_id=wh.id, lines=lines, ref="DIR-PI")
    custom = {
        "series_type": body.series_type or "Main",
        "invoice_date": body.invoice_date or str(date.today()),
        "bill_no": body.bill_no,
        "bill_date": body.bill_date,
        "freight_mode": body.freight_mode,
        "qc_status": body.qc_status or "No",
        "received_by": body.received_by,
        "invoice_remarks": body.invoice_remarks or body.remarks,
        "remarks": body.remarks or body.invoice_remarks,
        "lot_no": body.lot_no,
        "gr_no": body.gr_no,
        "gr_date": body.gr_date,
        "total_wt": body.total_wt,
        "description": body.description,
        "transport": body.transport,
        "warehouse_id": wh.id,
        "charges": charges,
        "other_tax": other_tax,
        "round_off": round_off,
        "charge_net": round(charge_net, 2),
        "payment": {
            "mode": body.payment_mode,
            "amount": body.payment_amount,
            "transaction_no": body.transaction_no,
            "transaction_date": body.transaction_date,
            "narration": body.payment_narration,
            "advance_adjust": body.advance_adjust,
        },
        "jv": {
            "account": body.jv_account,
            "type": body.jv_type,
            "amount": body.jv_amount,
            "txn_no": body.jv_txn_no,
            "txn_date": body.jv_txn_date,
            "narration": body.jv_narration,
        },
        "pi_type": body.pi_type or "Direct",
        "source": "kanha_direct_pi",
        "sbac_parity": "2026-08-02-live",
    }
    pi = PurchaseInvoice(
        company_id=user.company_id,
        number=next_number(db, user.company_id, PurchaseInvoice, "PINV"),
        vendor_id=vend.id,
        purchase_order_id=None,
        status="posted",
        subtotal=sub,
        tax=tax,
        total=tot,
        lines=lines,
        rcm=rcm,
        custom=custom,
    )
    db.add(pi)
    db.flush()
    journal_number = _post_purchase_journal(
        db,
        company_id=user.company_id,
        pi=pi,
        party_name=vend.name,
        rcm=rcm,
    )
    audit(db, company_id=user.company_id, user_id=user.id, action="create", entity="purchase_invoice", entity_id=pi.number)
    db.commit()
    db.refresh(pi)
    return {
        "id": pi.id,
        "number": pi.number,
        "total": pi.total,
        "tax": pi.tax,
        "rcm": rcm,
        "custom": pi.custom or {},
        "journal": journal_number,
        "message": f"Direct PI {pi.number}" + (" · RCM" if rcm else ""),
    }


@router.post("/purchase/orders/{po_id}/receive")
def receive_po(po_id: int, user: CurrentUser, db: DbDep, rcm: bool = False) -> dict:
    """One-shot: MRN + Purchase Invoice (legacy atomic path)."""
    from app.core.deps import assert_perm
    from app.services.period_lock import assert_period_open

    assert_perm(user, db, "purchase.*", "inventory.*")
    assert_period_open(db, user.company_id, date.today())
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id, PurchaseOrder.company_id == user.company_id).first()
    if not po:
        raise HTTPException(404, "PO not found")
    po_lines = _normalize_po_lines(list(po.lines or []))
    # Take full remaining balance
    grn_lines: list[dict] = []
    updated: list[dict] = []
    for ln in po_lines:
        bal = float(ln.get("bal_qty") or 0)
        if bal <= 0:
            updated.append(ln)
            continue
        gl = dict(ln)
        gl["qty"] = bal
        disc = float(gl.get("discount_pct", 0) or 0)
        amt = bal * float(gl.get("rate") or 0) * (1.0 - disc / 100.0)
        gl["amount"] = round(amt, 2)
        grn_lines.append(gl)
        ln["received_qty"] = round(float(ln.get("received_qty") or 0) + bal, 4)
        ln["bal_qty"] = 0.0
        updated.append(ln)
    if not grn_lines:
        # Fallback: use all lines if no bal tracking yet
        grn_lines = [dict(x) for x in (po.lines or [])]
        updated = _normalize_po_lines(grn_lines)
        for ln in updated:
            ln["received_qty"] = float(ln.get("ordered_qty") or ln.get("qty") or 0)
            ln["bal_qty"] = 0.0

    _receive_stock_lines(
        db,
        company_id=user.company_id,
        warehouse_id=po.warehouse_id,
        lines=grn_lines,
        ref=po.number,
    )
    grn = GoodsReceipt(
        company_id=user.company_id,
        number=next_number(db, user.company_id, GoodsReceipt, "MRN"),
        purchase_order_id=po.id,
        status="invoiced",
        lines=grn_lines,
        custom={"source": "kanha_receive_oneshot", "stock_received": True},
    )
    db.add(grn)
    db.flush()
    sub, tax, total = _line_totals([dict(x) for x in grn_lines])
    tot = float(sub) if rcm else float(total)
    pi = PurchaseInvoice(
        company_id=user.company_id,
        number=next_number(db, user.company_id, PurchaseInvoice, "PINV"),
        vendor_id=po.vendor_id,
        purchase_order_id=po.id,
        status="posted",
        subtotal=sub,
        tax=tax,
        total=tot,
        lines=grn_lines,
        rcm=bool(rcm),
    )
    db.add(pi)
    db.flush()
    grn.purchase_invoice_id = pi.id
    po.lines = updated
    po.status = "received"
    try:
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(po, "lines")
    except Exception:
        pass
    vend = db.get(Vendor, po.vendor_id)
    journal_number = _post_purchase_journal(
        db,
        company_id=user.company_id,
        pi=pi,
        party_name=vend.name if vend else "",
        grn_number=grn.number,
        rcm=bool(rcm),
    )
    db.commit()
    return {
        "grn": grn.number,
        "purchase_invoice": pi.number,
        "journal": journal_number,
        "rcm": bool(rcm),
        "message": f"GRN {grn.number} · PI {pi.number}"
        + (" · RCM" if rcm else "")
        + (f" · Books {journal_number}" if journal_number else ""),
    }


@router.get("/purchase/invoices")
def purchase_invoices(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(PurchaseInvoice).filter(PurchaseInvoice.company_id == user.company_id).all()
    out = []
    for i in rows:
        v = db.get(Vendor, i.vendor_id)
        out.append(
            {
                "id": i.id,
                "number": i.number,
                "vendor_id": i.vendor_id,
                "vendor_name": v.name if v else "",
                "vendor_gstin": v.gstin if v else "",
                "vendor_phone": v.phone if v else "",
                "status": i.status,
                "subtotal": i.subtotal,
                "total": i.total,
                "paid": i.paid,
                "tax": i.tax,
                "rcm": bool(getattr(i, "rcm", False)),
                "balance": round(float(i.total) - float(i.paid or 0), 2),
                "lines": i.lines or [],
            }
        )
    return out


class VendorPaymentIn(BaseModel):
    purchase_invoice_id: int
    amount: float
    method: str = "bank"
    reference: str = ""
    allocations: list[dict] | None = None  # [{purchase_invoice_id, amount}]


@router.post("/purchase/payments")
def record_vendor_payment(body: VendorPaymentIn, user: CurrentUser, db: DbDep) -> dict:
    """Pay vendor bill(s) — bill-by-bill allocations supported."""
    from app.core.deps import assert_perm
    from app.models import PaymentAllocation
    from app.services.period_lock import assert_period_open

    assert_perm(user, db, "purchase.*", "accounting.*")
    assert_period_open(db, user.company_id, date.today())
    pi = (
        db.query(PurchaseInvoice)
        .filter(PurchaseInvoice.id == body.purchase_invoice_id, PurchaseInvoice.company_id == user.company_id)
        .first()
    )
    if not pi:
        raise HTTPException(404, "Purchase invoice not found")
    amt = float(body.amount or 0)
    if amt <= 0:
        raise HTTPException(400, "amount must be > 0")

    allocs = list(body.allocations or [])
    if not allocs:
        # FIFO across open PIs for this vendor if amount > this bill balance
        bal0 = max(0.0, float(pi.total) - float(pi.paid or 0))
        if amt <= bal0 + 0.01:
            allocs = [{"purchase_invoice_id": pi.id, "amount": amt}]
        else:
            remain = amt
            open_pis = (
                db.query(PurchaseInvoice)
                .filter(
                    PurchaseInvoice.company_id == user.company_id,
                    PurchaseInvoice.vendor_id == pi.vendor_id,
                    PurchaseInvoice.total > PurchaseInvoice.paid,
                )
                .order_by(PurchaseInvoice.id)
                .all()
            )
            # put primary first
            ordered = [pi] + [x for x in open_pis if x.id != pi.id]
            for row in ordered:
                if remain <= 0.01:
                    break
                bal = max(0.0, float(row.total) - float(row.paid or 0))
                use = min(bal, remain)
                if use > 0:
                    allocs.append({"purchase_invoice_id": row.id, "amount": round(use, 2)})
                    remain = round(remain - use, 2)
            if remain > 0.01:
                raise HTTPException(400, f"Amount exceeds open vendor bills by ₹{remain:,.2f}")

    alloc_sum = round(sum(float(a.get("amount") or 0) for a in allocs), 2)
    if abs(alloc_sum - amt) > 0.05:
        raise HTTPException(400, f"Allocations sum ₹{alloc_sum} must match payment ₹{amt}")

    pay = Payment(
        company_id=user.company_id,
        invoice_id=None,
        party_type="vendor",
        party_id=pi.vendor_id,
        amount=amt,
        method=body.method,
        reference=body.reference or f"PI-{pi.number}",
        payment_date=date.today(),
        allocations=allocs,
    )
    db.add(pay)
    db.flush()

    applied = []
    for a in allocs:
        pid = int(a.get("purchase_invoice_id") or 0)
        aamt = float(a.get("amount") or 0)
        target = db.query(PurchaseInvoice).filter(PurchaseInvoice.id == pid, PurchaseInvoice.company_id == user.company_id).first()
        if not target:
            raise HTTPException(404, f"PI {pid} not found")
        bal = max(0.0, float(target.total) - float(target.paid or 0))
        use = min(aamt, bal + 0.01)
        target.paid = min(target.total, float(target.paid or 0) + use)
        if target.paid >= target.total - 0.01:
            target.status = "paid"
            target.paid = target.total
        else:
            target.status = "partial"
        db.add(
            PaymentAllocation(
                company_id=user.company_id,
                payment_id=pay.id,
                purchase_invoice_id=target.id,
                amount=use,
            )
        )
        applied.append({"invoice": target.number, "amount": use, "balance": round(target.total - target.paid, 2)})

    accounts = {
        a.code: a
        for a in db.query(Account).filter(Account.company_id == user.company_id, Account.is_group == False).all()  # noqa: E712
    }
    ap = accounts.get("2100")
    bank = accounts.get("1200") or accounts.get("1100") or accounts.get("1000")
    if ap and bank:
        vend = db.get(Vendor, pi.vendor_id)
        db.add(
            JournalEntry(
                company_id=user.company_id,
                number=next_number(db, user.company_id, JournalEntry, "PMT"),
                entry_date=date.today(),
                narration=f"Vendor payment bill-wise · {body.method} · {', '.join(x['invoice'] for x in applied)}",
                lines=[
                    {"account_id": ap.id, "account_code": ap.code, "debit": amt, "credit": 0},
                    {"account_id": bank.id, "account_code": bank.code, "debit": 0, "credit": amt},
                ],
                status="posted",
                voucher_type="payment",
                party_name=vend.name if vend else "",
            )
        )

    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="vendor_payment",
        entity="purchase_invoice",
        entity_id=str(pi.id),
        detail=f"amount={amt} bills={len(applied)}",
    )
    db.commit()
    return {
        "ok": True,
        "purchase_invoice": pi.number,
        "paid": pi.paid,
        "balance": round(pi.total - pi.paid, 2),
        "status": pi.status,
        "allocations": applied,
        "message": f"Paid ₹{amt:,.0f} across {len(applied)} bill(s)",
    }


@router.get("/purchase/payments")
def list_vendor_payments(user: CurrentUser, db: DbDep) -> list:
    rows = (
        db.query(Payment)
        .filter(Payment.company_id == user.company_id, Payment.party_type == "vendor")
        .order_by(Payment.id.desc())
        .all()
    )
    out = []
    for p in rows:
        v = db.get(Vendor, p.party_id)
        out.append(
            {
                "id": p.id,
                "vendor_name": v.name if v else "",
                "amount": p.amount,
                "method": p.method,
                "reference": p.reference or "—",
                "payment_date": p.payment_date.isoformat() if p.payment_date else None,
            }
        )
    return out


# ── Accounting ───────────────────────────────────────────────────────────────


@router.get("/accounting/coa")
def chart_of_accounts(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(Account).filter(Account.company_id == user.company_id).order_by(Account.code).all()
    return [
        {
            "id": a.id,
            "code": a.code,
            "name": a.name,
            "account_type": a.account_type,
            "is_group": a.is_group,
        }
        for a in rows
    ]


@router.get("/accounting/journals")
def journals(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(JournalEntry).filter(JournalEntry.company_id == user.company_id).order_by(JournalEntry.id.desc()).all()
    return [
        {
            "id": j.id,
            "number": j.number,
            "entry_date": j.entry_date.isoformat() if j.entry_date else None,
            "narration": j.narration,
            "lines": j.lines,
            "status": j.status,
        }
        for j in rows
    ]


class JournalIn(BaseModel):
    narration: str = "Manual journal"
    lines: list[dict[str, Any]] = Field(default_factory=list)
    entry_date: date | None = None


@router.post("/accounting/journals")
def create_journal(body: JournalIn, user: CurrentUser, db: DbDep) -> dict:
    from app.services.period_lock import assert_period_open

    entry_date = body.entry_date or date.today()
    assert_period_open(db, user.company_id, entry_date)
    accounts = {
        a.code: a
        for a in db.query(Account).filter(Account.company_id == user.company_id, Account.is_group == False).all()  # noqa: E712
    }
    lines = body.lines
    if not lines:
        # Demo balanced entry: Dr AR / Cr Sales
        ar = accounts.get("1300")
        sales = accounts.get("4100")
        if not ar or not sales:
            raise HTTPException(400, "COA missing AR(1300)/Sales(4100)")
        lines = [
            {"account_id": ar.id, "account_code": ar.code, "debit": 11800, "credit": 0},
            {"account_id": sales.id, "account_code": sales.code, "debit": 0, "credit": 10000},
            {
                "account_id": (accounts.get("2200") or sales).id,
                "account_code": (accounts.get("2200") or sales).code,
                "debit": 0,
                "credit": 1800,
            },
        ]
    debit = sum(float(ln.get("debit") or 0) for ln in lines)
    credit = sum(float(ln.get("credit") or 0) for ln in lines)
    if abs(debit - credit) > 0.05:
        raise HTTPException(400, f"Journal not balanced (Dr {debit} ≠ Cr {credit})")
    row = JournalEntry(
        company_id=user.company_id,
        number=next_number(db, user.company_id, JournalEntry, "JV"),
        entry_date=body.entry_date or date.today(),
        narration=body.narration,
        lines=lines,
        status="posted",
    )
    db.add(row)
    audit(db, company_id=user.company_id, user_id=user.id, action="create", entity="journal", entity_id=row.number)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "number": row.number, "debit": debit, "credit": credit}


class PeriodLockIn(BaseModel):
    closed_through: str | None = None  # YYYY-MM or null to clear
    note: str = ""


@router.get("/accounting/period-lock")
def get_period_lock(user: CurrentUser, db: DbDep) -> dict:
    from app.services.period_lock import period_status

    return {"ok": True, **period_status(db, user.company_id)}


@router.post("/accounting/period-lock")
def post_period_lock(body: PeriodLockIn, user: CurrentUser, db: DbDep) -> dict:
    from app.core.deps import assert_perm
    from app.services.period_lock import set_period_lock

    assert_perm(user, db, "accounting.*", "settings.*")
    st = set_period_lock(
        db,
        user.company_id,
        closed_through=body.closed_through,
        note=body.note,
        updated_by=user.email,
    )
    db.commit()
    return {"ok": True, **st, "message": st["message"]}


@router.get("/accounting/budgets")
def list_budgets(user: CurrentUser, db: DbDep) -> list:
    from app.models import Budget

    rows = db.query(Budget).filter(Budget.company_id == user.company_id).all()
    return [
        {"id": b.id, "name": b.name, "fiscal_year": b.fiscal_year, "lines": b.lines}
        for b in rows
    ]


@router.get("/accounting/assets")
def list_assets(user: CurrentUser, db: DbDep) -> list:
    from app.models import FixedAsset

    rows = db.query(FixedAsset).filter(FixedAsset.company_id == user.company_id).all()
    return [
        {
            "id": a.id,
            "name": a.name,
            "purchase_date": a.purchase_date.isoformat() if a.purchase_date else None,
            "cost": a.cost,
            "method": a.depreciation_method,
            "life_years": a.useful_life_years,
            "salvage": a.salvage,
        }
        for a in rows
    ]


@router.get("/sales/payments")
def list_payments(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(Payment).filter(Payment.company_id == user.company_id).order_by(Payment.id.desc()).all()
    out = []
    for p in rows:
        inv = db.get(Invoice, p.invoice_id) if p.invoice_id else None
        cust = db.get(Customer, p.party_id) if p.party_type == "customer" else None
        out.append(
            {
                "id": p.id,
                "invoice_number": inv.number if inv else "",
                "customer_name": cust.name if cust else "",
                "amount": p.amount,
                "method": p.method,
                "reference": p.reference or "—",
                "payment_date": p.payment_date.isoformat() if p.payment_date else None,
            }
        )
    return out


@router.get("/sales/deliveries")
def list_deliveries(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(Delivery).filter(Delivery.company_id == user.company_id).order_by(Delivery.id.desc()).all()
    out = []
    for d in rows:
        so = db.get(SalesOrder, d.sales_order_id) if d.sales_order_id else None
        cust = db.get(Customer, so.customer_id) if so else None
        lines = list(d.lines or [])
        total_qty = sum(float(x.get("qty") or 0) for x in lines)
        sub, tax, total = _line_totals([dict(x) for x in lines]) if lines else (0, 0, 0)
        out.append(
            {
                "id": d.id,
                "number": d.number,
                "sales_order": so.number if so else "",
                "sales_order_id": d.sales_order_id,
                "customer_name": cust.name if cust else "—",
                "status": d.status,
                "lines": lines,
                "line_count": len(lines),
                "total_qty": round(total_qty, 4),
                "total": total,
                "subtotal": sub,
                "tax": tax,
                "invoice_id": getattr(d, "invoice_id", None),
                "custom": getattr(d, "custom", None) or {},
            }
        )
    return out


@router.get("/purchase/grn")
def list_grn(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(GoodsReceipt).filter(GoodsReceipt.company_id == user.company_id).order_by(GoodsReceipt.id.desc()).all()
    out = []
    for g in rows:
        po = db.get(PurchaseOrder, g.purchase_order_id) if g.purchase_order_id else None
        vendor = db.get(Vendor, po.vendor_id) if po else None
        lines = list(g.lines or [])
        total_qty = sum(float(x.get("qty") or 0) for x in lines)
        sub, tax, total = _line_totals([dict(x) for x in lines]) if lines else (0, 0, 0)
        out.append(
            {
                "id": g.id,
                "number": g.number,
                "po_number": po.number if po else "",
                "purchase_order_id": g.purchase_order_id,
                "vendor_name": vendor.name if vendor else "—",
                "status": g.status,
                "lines": lines,
                "line_count": len(lines),
                "total_qty": round(total_qty, 4),
                "total": total,
                "subtotal": sub,
                "tax": tax,
                "purchase_invoice_id": getattr(g, "purchase_invoice_id", None),
                "custom": getattr(g, "custom", None) or {},
            }
        )
    return out


@router.get("/accounting/reports/pnl")
def pnl(user: CurrentUser, db: DbDep) -> dict:
    from app.services.ops_intelligence import books_based_pnl

    return books_based_pnl(db, user.company_id)


@router.get("/accounting/reports/gst")
def gst_report(user: CurrentUser, db: DbDep) -> dict:
    from app.services.ops_intelligence import company_gstin, gst_for_party

    sales = db.query(Invoice).filter(Invoice.company_id == user.company_id).all()
    purchases = db.query(PurchaseInvoice).filter(PurchaseInvoice.company_id == user.company_id).all()
    co_gst = company_gstin(db, user.company_id)
    output = sum(i.tax for i in sales if (i.invoice_type or "sales") != "credit")
    # credit notes reduce output
    output -= sum(i.tax for i in sales if (i.invoice_type or "sales") == "credit")
    input_t = sum(i.tax for i in purchases)
    out_cgst = out_sgst = out_igst = 0.0
    in_cgst = in_sgst = in_igst = 0.0
    register: list[dict] = []
    for inv in sales:
        cust = db.get(Customer, inv.customer_id) if inv.customer_id else None
        split = gst_for_party(
            inv.subtotal,
            18,
            company_gstin=co_gst,
            party_gstin=cust.gstin if cust else None,
        )
        sign = -1 if (inv.invoice_type or "sales") == "credit" else 1
        out_cgst += sign * split["cgst"]
        out_sgst += sign * split["sgst"]
        out_igst += sign * split["igst"]
        register.append(
            {
                "doc_type": "credit" if sign < 0 else "sales",
                "number": inv.number,
                "date": inv.invoice_date.isoformat() if inv.invoice_date else None,
                "party": cust.name if cust else "",
                "intra_state": split["intra_state"],
                "taxable": round(sign * inv.subtotal, 2),
                "cgst": round(sign * split["cgst"], 2),
                "sgst": round(sign * split["sgst"], 2),
                "igst": round(sign * split["igst"], 2),
                "total_tax": round(sign * inv.tax, 2),
            }
        )
    for pi in purchases:
        from app.models import Vendor

        vend = db.get(Vendor, pi.vendor_id) if pi.vendor_id else None
        split = gst_for_party(
            pi.subtotal,
            18,
            company_gstin=co_gst,
            party_gstin=vend.gstin if vend else None,
        )
        in_cgst += split["cgst"]
        in_sgst += split["sgst"]
        in_igst += split["igst"]
        register.append(
            {
                "doc_type": "purchase",
                "number": pi.number,
                "date": None,
                "party": vend.name if vend else "",
                "intra_state": split["intra_state"],
                "taxable": round(pi.subtotal, 2),
                "cgst": split["cgst"],
                "sgst": split["sgst"],
                "igst": split["igst"],
                "total_tax": round(pi.tax, 2),
            }
        )
    return {
        "output_tax": round(output, 2),
        "input_tax": round(input_t, 2),
        "net_payable": round(output - input_t, 2),
        "outward": {"cgst": round(out_cgst, 2), "sgst": round(out_sgst, 2), "igst": round(out_igst, 2)},
        "inward_itc": {"cgst": round(in_cgst, 2), "sgst": round(in_sgst, 2), "igst": round(in_igst, 2)},
        "register": register[:80],
        "note": "Place-of-supply from GSTIN state codes · desk only (not GSTN filed)",
    }


@router.get("/accounting/reports/trial-balance")
def trial_balance(user: CurrentUser, db: DbDep) -> list:
    accounts = db.query(Account).filter(Account.company_id == user.company_id, Account.is_group == False).all()  # noqa: E712
    journals = db.query(JournalEntry).filter(JournalEntry.company_id == user.company_id).all()
    bal: dict[int, dict[str, float]] = {a.id: {"code": a.code, "name": a.name, "debit": 0.0, "credit": 0.0} for a in accounts}
    for j in journals:
        for ln in j.lines or []:
            aid = ln.get("account_id")
            if aid in bal:
                bal[aid]["debit"] += float(ln.get("debit") or 0)
                bal[aid]["credit"] += float(ln.get("credit") or 0)
    return list(bal.values())
