"""Channel, logistics, batch, MRP, e-invoice modules."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func

from app.core.deps import CurrentUser, DbDep, assert_perm, audit, next_number
from app.models import (
    BOM,
    Customer,
    DealerOrder,
    DispatchChallan,
    Einvoice,
    Invoice,
    MrpPlan,
    PackingList,
    PriceList,
    Product,
    RfidScan,
    RfidTag,
    StockBalance,
    StockBatch,
    Warehouse,
    WorkOrder,
)

router = APIRouter(prefix="/api", tags=["ops"])


def _cust_dict(c: Customer) -> dict:
    return {
        "id": c.id,
        "code": c.code,
        "name": c.name,
        "email": c.email,
        "phone": c.phone,
        "gstin": c.gstin,
        "billing_address": c.billing_address,
        "party_type": getattr(c, "party_type", "customer") or "customer",
        "is_dealer": bool(getattr(c, "is_dealer", False)),
        "credit_limit": float(getattr(c, "credit_limit", 0) or 0),
        "price_list_code": getattr(c, "price_list_code", "STANDARD") or "STANDARD",
        "region": getattr(c, "region", "") or "",
        "active": c.active,
    }


# ── Dealers / price lists / portal ───────────────────────────────────────────


@router.get("/dealers")
def list_dealers(user: CurrentUser, db: DbDep) -> list:
    rows = (
        db.query(Customer)
        .filter(
            Customer.company_id == user.company_id,
            (Customer.is_dealer == True) | (Customer.party_type.in_(["dealer", "distributor"])),  # noqa: E712
        )
        .all()
    )
    out = []
    for c in rows:
        outstanding = (
            db.query(func.coalesce(func.sum(Invoice.total - Invoice.paid), 0))
            .filter(Invoice.company_id == user.company_id, Invoice.customer_id == c.id)
            .scalar()
            or 0
        )
        d = _cust_dict(c)
        d["outstanding"] = float(outstanding)
        d["credit_available"] = max(0.0, d["credit_limit"] - float(outstanding))
        out.append(d)
    return out


class DealerIn(BaseModel):
    name: str
    code: str | None = None
    phone: str | None = None
    email: str | None = None
    gstin: str | None = None
    region: str = ""
    credit_limit: float = 500000
    price_list_code: str = "DEALER"
    party_type: str = "dealer"


@router.post("/dealers")
def create_dealer(body: DealerIn, user: CurrentUser, db: DbDep) -> dict:
    code = body.code or f"DLR-{db.query(Customer).filter(Customer.company_id == user.company_id).count() + 1:03d}"
    row = Customer(
        company_id=user.company_id,
        code=code,
        name=body.name,
        phone=body.phone,
        email=body.email,
        gstin=body.gstin,
        party_type=body.party_type,
        is_dealer=True,
        credit_limit=body.credit_limit,
        price_list_code=body.price_list_code,
        region=body.region,
    )
    db.add(row)
    audit(db, company_id=user.company_id, user_id=user.id, action="create", entity="dealer")
    db.commit()
    db.refresh(row)
    return _cust_dict(row)


@router.get("/pricing/lists")
def price_lists(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(PriceList).filter(PriceList.company_id == user.company_id).all()
    return [
        {
            "id": r.id,
            "code": r.code,
            "name": r.name,
            "party_type": r.party_type,
            "active": r.active,
            "lines": r.lines or [],
        }
        for r in rows
    ]


class PriceListIn(BaseModel):
    code: str
    name: str
    party_type: str = "dealer"
    lines: list[dict[str, Any]] = Field(default_factory=list)


@router.post("/pricing/lists")
def create_price_list(body: PriceListIn, user: CurrentUser, db: DbDep) -> dict:
    row = PriceList(
        company_id=user.company_id,
        code=body.code,
        name=body.name,
        party_type=body.party_type,
        lines=body.lines,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "code": row.code}


@router.get("/portal/dealer/{dealer_id}")
def dealer_portal(dealer_id: int, user: CurrentUser, db: DbDep) -> dict:
    c = db.query(Customer).filter(Customer.id == dealer_id, Customer.company_id == user.company_id).first()
    if not c:
        raise HTTPException(404, "Dealer not found")
    pl = (
        db.query(PriceList)
        .filter(PriceList.company_id == user.company_id, PriceList.code == (c.price_list_code or "STANDARD"))
        .first()
    )
    orders = (
        db.query(DealerOrder)
        .filter(DealerOrder.company_id == user.company_id, DealerOrder.dealer_id == dealer_id)
        .order_by(DealerOrder.id.desc())
        .limit(20)
        .all()
    )
    invoices = db.query(Invoice).filter(Invoice.company_id == user.company_id, Invoice.customer_id == dealer_id).all()
    outstanding = sum(max(0, i.total - i.paid) for i in invoices)
    return {
        "dealer": _cust_dict(c),
        "price_list": {
            "code": pl.code if pl else c.price_list_code,
            "name": pl.name if pl else "Standard",
            "lines": (pl.lines if pl else []),
        },
        "outstanding": round(outstanding, 2),
        "credit_available": round(max(0, float(c.credit_limit or 0) - outstanding), 2),
        "orders": [
            {"id": o.id, "number": o.number, "status": o.status, "total": o.total, "notes": o.notes}
            for o in orders
        ],
        "invoices": [
            {"number": i.number, "total": i.total, "paid": i.paid, "balance": round(i.total - i.paid, 2), "status": i.status}
            for i in invoices
        ],
    }


class DealerOrderIn(BaseModel):
    dealer_id: int
    lines: list[dict[str, Any]] = Field(default_factory=list)
    notes: str = ""


@router.post("/portal/dealer-orders")
def submit_dealer_order(body: DealerOrderIn, user: CurrentUser, db: DbDep) -> dict:
    c = db.query(Customer).filter(Customer.id == body.dealer_id, Customer.company_id == user.company_id).first()
    if not c:
        raise HTTPException(404, "Dealer not found")
    total = 0.0
    lines = []
    for ln in body.lines:
        qty = float(ln.get("qty", 0))
        rate = float(ln.get("rate", 0))
        amt = round(qty * rate, 2)
        total += amt
        lines.append({**ln, "amount": amt})
    outstanding = (
        db.query(func.coalesce(func.sum(Invoice.total - Invoice.paid), 0))
        .filter(Invoice.company_id == user.company_id, Invoice.customer_id == c.id)
        .scalar()
        or 0
    )
    if float(c.credit_limit or 0) and (float(outstanding) + total) > float(c.credit_limit):
        raise HTTPException(400, detail=f"Credit limit exceeded (limit ₹{c.credit_limit:,.0f})")
    row = DealerOrder(
        company_id=user.company_id,
        number=next_number(db, user.company_id, DealerOrder, "DO"),
        dealer_id=c.id,
        status="submitted",
        lines=lines,
        total=round(total, 2),
        notes=body.notes,
    )
    db.add(row)
    audit(db, company_id=user.company_id, user_id=user.id, action="create", entity="dealer_order", entity_id=row.number)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "number": row.number, "total": row.total, "status": row.status}


@router.get("/portal/dealer-orders")
def list_dealer_orders(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(DealerOrder).filter(DealerOrder.company_id == user.company_id).order_by(DealerOrder.id.desc()).all()
    out = []
    for o in rows:
        d = db.get(Customer, o.dealer_id)
        lines = []
        for ln in o.lines or []:
            row = dict(ln)
            row.setdefault("name", row.get("sku") or "Item")
            row.setdefault("gst_rate", 18)
            lines.append(row)
        out.append(
            {
                "id": o.id,
                "number": o.number,
                "dealer_id": o.dealer_id,
                "dealer_name": d.name if d else "",
                "status": o.status,
                "total": o.total,
                "lines": lines,
                "notes": o.notes or "—",
            }
        )
    return out


@router.post("/portal/dealer-orders/{order_id}/decide")
def decide_dealer_order(order_id: int, body: dict, user: CurrentUser, db: DbDep) -> dict:
    row = db.query(DealerOrder).filter(DealerOrder.id == order_id, DealerOrder.company_id == user.company_id).first()
    if not row:
        raise HTTPException(404, "Order not found")
    status = body.get("status", "approved")
    if status not in ("approved", "rejected", "fulfilled"):
        raise HTTPException(400, "Invalid status")
    row.status = status
    audit(db, company_id=user.company_id, user_id=user.id, action=status, entity="dealer_order", entity_id=str(row.id))
    db.commit()
    return {"ok": True, "status": row.status}


# ── Batch / lot stock ────────────────────────────────────────────────────────


@router.get("/inventory/batches")
def list_batches(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(StockBatch).filter(StockBatch.company_id == user.company_id).order_by(StockBatch.id.desc()).all()
    out = []
    for b in rows:
        p = db.get(Product, b.product_id)
        w = db.get(Warehouse, b.warehouse_id)
        out.append(
            {
                "id": b.id,
                "batch_no": b.batch_no,
                "sku": p.sku if p else "",
                "product": p.name if p else "",
                "warehouse": w.code if w else "",
                "qty": b.qty,
                "mfg_date": b.mfg_date.isoformat() if b.mfg_date else None,
                "expiry_date": b.expiry_date.isoformat() if b.expiry_date else None,
                "notes": b.notes,
            }
        )
    return out


class BatchIn(BaseModel):
    product_id: int
    warehouse_id: int
    batch_no: str
    qty: float
    mfg_date: date | None = None
    expiry_date: date | None = None
    notes: str = ""


@router.post("/inventory/batches")
def create_batch(body: BatchIn, user: CurrentUser, db: DbDep) -> dict:
    row = StockBatch(
        company_id=user.company_id,
        product_id=body.product_id,
        warehouse_id=body.warehouse_id,
        batch_no=body.batch_no,
        qty=body.qty,
        mfg_date=body.mfg_date,
        expiry_date=body.expiry_date,
        notes=body.notes,
    )
    db.add(row)
    bal = (
        db.query(StockBalance)
        .filter(
            StockBalance.company_id == user.company_id,
            StockBalance.product_id == body.product_id,
            StockBalance.warehouse_id == body.warehouse_id,
        )
        .first()
    )
    if bal:
        bal.qty += body.qty
    audit(db, company_id=user.company_id, user_id=user.id, action="create", entity="batch", entity_id=body.batch_no)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "batch_no": row.batch_no, "qty": row.qty}


# ── Packing / Dispatch / E-invoice ───────────────────────────────────────────


@router.get("/logistics/packing")
def packing_lists(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(PackingList).filter(PackingList.company_id == user.company_id).order_by(PackingList.id.desc()).all()
    out = []
    for r in rows:
        cust = db.get(Customer, r.customer_id) if r.customer_id else None
        inv = db.get(Invoice, r.invoice_id) if r.invoice_id else None
        out.append(
            {
                "id": r.id,
                "number": r.number,
                "invoice_id": r.invoice_id,
                "invoice_number": inv.number if inv else "",
                "customer_id": r.customer_id,
                "customer_name": cust.name if cust else "",
                "status": r.status,
                "packages": r.packages,
                "weight_kg": r.weight_kg,
                "lines": r.lines,
            }
        )
    return out


@router.post("/logistics/packing")
def create_packing(user: CurrentUser, db: DbDep) -> dict:
    inv = db.query(Invoice).filter(Invoice.company_id == user.company_id).order_by(Invoice.id.desc()).first()
    row = PackingList(
        company_id=user.company_id,
        number=next_number(db, user.company_id, PackingList, "PKL"),
        invoice_id=inv.id if inv else None,
        customer_id=inv.customer_id if inv else None,
        status="packed",
        packages=3,
        weight_kg=45.5,
        lines=(inv.lines if inv else []) or [{"sku": "DEMO", "qty": 10, "batch_no": "B-001"}],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "number": row.number, "packages": row.packages}


@router.get("/logistics/dispatch")
def dispatch_list(user: CurrentUser, db: DbDep) -> list:
    rows = (
        db.query(DispatchChallan)
        .filter(DispatchChallan.company_id == user.company_id)
        .order_by(DispatchChallan.id.desc())
        .all()
    )
    out = []
    for r in rows:
        inv = db.get(Invoice, r.invoice_id) if r.invoice_id else None
        cust = db.get(Customer, r.customer_id) if r.customer_id else (db.get(Customer, inv.customer_id) if inv else None)
        out.append(
            {
                "id": r.id,
                "number": r.number,
                "invoice_id": r.invoice_id,
                "invoice_number": inv.number if inv else "",
                "customer_name": cust.name if cust else "",
                "transporter": r.transporter or "—",
                "lr_number": r.lr_number or "—",
                "vehicle_no": r.vehicle_no or "—",
                "dispatch_date": r.dispatch_date.isoformat() if r.dispatch_date else None,
                "status": r.status,
                "notes": r.notes or "—",
            }
        )
    return out


@router.post("/logistics/dispatch")
def create_dispatch(user: CurrentUser, db: DbDep) -> dict:
    inv = db.query(Invoice).filter(Invoice.company_id == user.company_id).order_by(Invoice.id.desc()).first()
    pkl = db.query(PackingList).filter(PackingList.company_id == user.company_id).order_by(PackingList.id.desc()).first()
    row = DispatchChallan(
        company_id=user.company_id,
        number=next_number(db, user.company_id, DispatchChallan, "DC"),
        packing_list_id=pkl.id if pkl else None,
        invoice_id=inv.id if inv else None,
        customer_id=inv.customer_id if inv else None,
        transporter="Kanha Logistics",
        lr_number=f"LR{date.today().strftime('%y%m%d')}01",
        vehicle_no="RJ14AB4321",
        dispatch_date=date.today(),
        status="dispatched",
        notes="Packed & handed to transporter",
    )
    db.add(row)
    audit(db, company_id=user.company_id, user_id=user.id, action="dispatch", entity="challan", entity_id=row.number)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "number": row.number, "lr_number": row.lr_number}


@router.get("/logistics/einvoice")
def list_einvoices(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(Einvoice).filter(Einvoice.company_id == user.company_id).order_by(Einvoice.id.desc()).all()
    out = []
    for e in rows:
        inv = db.get(Invoice, e.invoice_id)
        out.append(
            {
                "id": e.id,
                "invoice_number": inv.number if inv else "",
                "irn": e.irn,
                "ack_no": e.ack_no,
                "ack_date": e.ack_date,
                "status": e.status,
                "gsp_note": e.gsp_note,
            }
        )
    return out


@router.post("/logistics/einvoice/generate")
def generate_einvoice(user: CurrentUser, db: DbDep, invoice_id: int | None = None) -> dict:
    q = db.query(Invoice).filter(Invoice.company_id == user.company_id, Invoice.invoice_type != "credit")
    if invoice_id:
        inv = q.filter(Invoice.id == invoice_id).first()
    else:
        inv = q.order_by(Invoice.id.desc()).first()
    if not inv:
        raise HTTPException(404, "No invoice")
    existing = db.query(Einvoice).filter(Einvoice.invoice_id == inv.id).first()
    if existing:
        return {"id": existing.id, "irn": existing.irn, "status": existing.status, "note": "Already generated", "live": False, "invoice_id": inv.id, "invoice_number": inv.number}
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    local_irn = f"DEMO-IRN-{inv.number}-{stamp}"[-64:]
    row = Einvoice(
        company_id=user.company_id,
        invoice_id=inv.id,
        irn=local_irn,
        ack_no=f"ACK{stamp[-8:]}",
        ack_date=datetime.utcnow().isoformat() + "Z",
        status="generated",
        qr_payload=f"IRN:{local_irn}|INV:{inv.number}|AMT:{inv.total}",
        gsp_note="Demo IRN generated locally — paste GSP keys in .env for live NIC push",
    )
    db.add(row)
    from app.core.config import settings
    from app.services.integrations_gsp import push_einvoice_irn
    from app.services.legal_compliance import assert_feature_approved

    if getattr(settings, "gsp_live", False):
        assert_feature_approved(db, user.company_id, "live_gsp_push")

    gsp = push_einvoice_irn(
        {
            "invoice_number": inv.number,
            "invoice_id": inv.id,
            "total": inv.total,
            "subtotal": inv.subtotal,
            "tax": inv.tax,
            "irn": local_irn,
            "company_id": user.company_id,
            "gstin": settings.company_gstin,
        }
    )
    if gsp.get("live") and gsp.get("status") == "ok":
        if gsp.get("irn"):
            row.irn = str(gsp["irn"])[:64]
        if gsp.get("ack_no"):
            row.ack_no = str(gsp["ack_no"])[:64]
        if gsp.get("ack_date"):
            row.ack_date = str(gsp["ack_date"])
        row.status = "generated_live"
        row.qr_payload = f"IRN:{row.irn}|INV:{inv.number}|AMT:{inv.total}"
        row.gsp_note = "Live GSP IRN OK"
    else:
        row.gsp_note = (
            "Live GSP push OK"
            if gsp.get("live") and gsp.get("status") == "ok"
            else (gsp.get("note") or gsp.get("error") or row.gsp_note)
        )
    audit(db, company_id=user.company_id, user_id=user.id, action="einvoice", entity="invoice", entity_id=str(inv.id))
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "irn": row.irn,
        "ack_no": row.ack_no,
        "status": row.status,
        "live": bool(gsp.get("live") and gsp.get("status") == "ok"),
        "gsp": gsp,
        "invoice_id": inv.id,
        "invoice_number": inv.number,
        "message": "Live IRN from GSP" if (gsp.get("live") and gsp.get("status") == "ok") else "Local demo IRN (set GSP keys for live)",
    }


# ── MRP planning ─────────────────────────────────────────────────────────────


@router.get("/manufacturing/mrp")
def list_mrp(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(MrpPlan).filter(MrpPlan.company_id == user.company_id).order_by(MrpPlan.id.desc()).all()
    return [
        {"id": r.id, "number": r.number, "period": r.period, "status": r.status, "lines": r.lines, "notes": r.notes}
        for r in rows
    ]


@router.post("/manufacturing/mrp/run")
def run_mrp(user: CurrentUser, db: DbDep) -> dict:
    """Simple MRP: stock vs BOM demand suggestion."""
    lines = []
    products = db.query(Product).filter(Product.company_id == user.company_id, Product.active == True).all()  # noqa: E712
    for p in products:
        bal = (
            db.query(func.coalesce(func.sum(StockBalance.qty), 0))
            .filter(StockBalance.company_id == user.company_id, StockBalance.product_id == p.id)
            .scalar()
            or 0
        )
        demand = 100 if p.track_batch or "electrode" in (p.name or "").lower() else 50
        shortage = max(0, demand - float(bal))
        if shortage > 0 or float(bal) < 40:
            action = "work_order" if db.query(BOM).filter(BOM.company_id == user.company_id, BOM.product_id == p.id).first() else "purchase"
            lines.append(
                {
                    "sku": p.sku,
                    "name": p.name,
                    "on_hand": float(bal),
                    "demand": demand,
                    "shortage": shortage,
                    "suggest": action,
                    "suggest_qty": shortage or 50,
                }
            )
    period = date.today().strftime("%Y-%m")
    row = MrpPlan(
        company_id=user.company_id,
        number=next_number(db, user.company_id, MrpPlan, "MRP"),
        period=period,
        status="planned",
        lines=lines,
        notes=f"Auto MRP run · {len(lines)} shortage lines · open WOs {db.query(WorkOrder).filter(WorkOrder.company_id == user.company_id).count()}",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "number": row.number, "period": period, "lines": lines, "count": len(lines)}


# ── RFID Warehouse ────────────────────────────────────────────────────────────


def _rfid_dict(t: RfidTag, db) -> dict:
    p = db.get(Product, t.product_id) if t.product_id else None
    w = db.get(Warehouse, t.warehouse_id) if t.warehouse_id else None
    return {
        "id": t.id,
        "epc": t.epc,
        "product_id": t.product_id,
        "sku": p.sku if p else "",
        "product": p.name if p else "",
        "barcode": p.barcode if p else "",
        "warehouse_id": t.warehouse_id,
        "warehouse": w.name if w else "",
        "location_code": t.location_code,
        "status": t.status,
        "last_scan_at": t.last_scan_at.isoformat() if t.last_scan_at else None,
        "notes": t.notes,
    }


@router.get("/rfid/tags")
def rfid_tags(user: CurrentUser, db: DbDep) -> list:
    assert_perm(user, db, "rfid.*", "rfid.view", "logistics.*", "inventory.*")
    rows = db.query(RfidTag).filter(RfidTag.company_id == user.company_id).order_by(RfidTag.id.desc()).all()
    return [_rfid_dict(t, db) for t in rows]


@router.get("/rfid/scans")
def rfid_scans(user: CurrentUser, db: DbDep, limit: int = 40) -> list:
    assert_perm(user, db, "rfid.*", "rfid.view", "logistics.*", "inventory.*")
    rows = (
        db.query(RfidScan)
        .filter(RfidScan.company_id == user.company_id)
        .order_by(RfidScan.id.desc())
        .limit(limit)
        .all()
    )
    out = []
    for s in rows:
        p = db.get(Product, s.product_id) if s.product_id else None
        out.append(
            {
                "id": s.id,
                "epc": s.epc,
                "action": s.action,
                "sku": p.sku if p else "",
                "product": p.name if p else "",
                "notes": s.notes,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
        )
    return out


class RfidScanIn(BaseModel):
    epc: str
    action: str = "locate"
    warehouse_id: int | None = None
    location_code: str | None = None
    notes: str = ""


@router.post("/rfid/scan")
def rfid_scan(body: RfidScanIn, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "rfid.*", "logistics.*", "inventory.*")
    epc = (body.epc or "").strip().upper()
    if not epc:
        raise HTTPException(400, "EPC required")
    tag = db.query(RfidTag).filter(RfidTag.company_id == user.company_id, RfidTag.epc == epc).first()
    if not tag:
        raise HTTPException(404, f"Unknown RFID tag: {epc}")

    action = (body.action or "locate").lower()
    if body.warehouse_id:
        tag.warehouse_id = body.warehouse_id
    if body.location_code:
        tag.location_code = body.location_code
    tag.last_scan_at = datetime.utcnow()
    tag.status = "active"

    stock_note = ""
    if tag.product_id and tag.warehouse_id and action in ("inbound", "outbound"):
        bal = (
            db.query(StockBalance)
            .filter(
                StockBalance.company_id == user.company_id,
                StockBalance.warehouse_id == tag.warehouse_id,
                StockBalance.product_id == tag.product_id,
            )
            .first()
        )
        if not bal and action == "inbound":
            bal = StockBalance(
                company_id=user.company_id,
                warehouse_id=tag.warehouse_id,
                product_id=tag.product_id,
                qty=0,
                avg_cost=0,
            )
            db.add(bal)
            db.flush()
        if bal:
            delta = 1.0 if action == "inbound" else -1.0
            bal.qty = max(0, bal.qty + delta)
            stock_note = f"stock {delta:+.0f} → {bal.qty}"

    scan = RfidScan(
        company_id=user.company_id,
        epc=epc,
        action=action,
        warehouse_id=tag.warehouse_id,
        product_id=tag.product_id,
        user_id=user.id,
        notes=body.notes or stock_note,
    )
    db.add(scan)
    audit(db, company_id=user.company_id, user_id=user.id, action="rfid_scan", entity="rfid", entity_id=epc)
    db.commit()
    return {
        "ok": True,
        "action": action,
        "tag": _rfid_dict(tag, db),
        "stock_note": stock_note,
        "message": f"RFID {action} · {epc}",
    }


class RfidBindIn(BaseModel):
    epc: str
    product_id: int
    warehouse_id: int | None = None
    location_code: str = "A-01"
    notes: str = ""


@router.post("/rfid/tags")
def rfid_bind(body: RfidBindIn, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "rfid.*", "inventory.*", "settings.*")
    epc = body.epc.strip().upper()
    p = db.query(Product).filter(Product.id == body.product_id, Product.company_id == user.company_id).first()
    if not p:
        raise HTTPException(404, "Product not found")
    existing = db.query(RfidTag).filter(RfidTag.company_id == user.company_id, RfidTag.epc == epc).first()
    if existing:
        existing.product_id = p.id
        existing.warehouse_id = body.warehouse_id
        existing.location_code = body.location_code
        existing.notes = body.notes
        existing.status = "active"
        db.commit()
        return {"ok": True, "tag": _rfid_dict(existing, db), "updated": True}
    tag = RfidTag(
        company_id=user.company_id,
        epc=epc,
        product_id=p.id,
        warehouse_id=body.warehouse_id,
        location_code=body.location_code,
        notes=body.notes,
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return {"ok": True, "tag": _rfid_dict(tag, db), "updated": False}
