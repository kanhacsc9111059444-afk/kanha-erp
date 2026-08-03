"""Lookup masters + shared FileService — foundation for SBAC parity & V2 SaaS."""
from __future__ import annotations

import re
import uuid
from datetime import datetime

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.core.config import DATA, settings
from app.core.deps import CurrentUser, DbDep, assert_perm, audit
from app.models import Document, LookupMaster

router = APIRouter(prefix="/api", tags=["masters-files"])

MASTER_TYPES = {
    "brand",
    "main_group",
    "sub_group",
    "category",
    "unit",
    "transport",
    "agent",
    "country",
}

IMAGE_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/svg+xml"}
DOC_MIME = IMAGE_MIME | {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
    "text/csv",
}


@router.post("/files/upload")
async def files_upload(
    user: CurrentUser,
    db: DbDep,
    file: UploadFile = File(...),
    entity: str = Form("general"),
    entity_id: str = Form(""),
    kind: str = Form("any"),
) -> dict:
    content = await file.read()
    max_bytes = int(getattr(settings, "upload_max_mb", 15) or 15) * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(400, f"Max {settings.upload_max_mb}MB")
    mime = (file.content_type or "application/octet-stream").lower()
    if kind == "image" and mime not in IMAGE_MIME:
        raise HTTPException(400, "Only image files allowed (jpg/png/webp/gif/svg)")
    if kind == "document" and mime not in DOC_MIME:
        raise HTTPException(400, "File type not allowed")
    uploads = DATA / "uploads" / str(user.company_id)
    uploads.mkdir(parents=True, exist_ok=True)
    raw_name = file.filename or "file.bin"
    safe = "".join(c for c in raw_name if c.isalnum() or c in "._- ")[:100] or "file.bin"
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    dest = uploads / f"{stamp}_{uuid.uuid4().hex[:8]}_{safe}"
    dest.write_bytes(content)
    rel = f"/uploads/{user.company_id}/{dest.name}"
    row = Document(
        company_id=user.company_id,
        name=safe,
        entity=entity or "general",
        entity_id=entity_id or None,
        mime=mime,
        path=rel,
        version=1,
    )
    db.add(row)
    audit(db, company_id=user.company_id, user_id=user.id, action="upload", entity="file", entity_id=safe)
    db.commit()
    db.refresh(row)
    return {
        "ok": True,
        "id": row.id,
        "name": row.name,
        "url": row.path,
        "path": row.path,
        "mime": row.mime,
        "size": len(content),
    }


class MasterIn(BaseModel):
    code: str | None = None
    name: str = Field(min_length=1, max_length=200)
    parent_id: int | None = None
    parent_code: str | None = None
    active: bool = True
    custom: dict | None = None
    sort_order: int = 0


def _code_from_name(name: str) -> str:
    base = re.sub(r"[^A-Za-z0-9]+", "-", (name or "").strip().upper()).strip("-")[:24]
    return base or uuid.uuid4().hex[:8].upper()


def _serialize(row: LookupMaster) -> dict:
    return {
        "id": row.id,
        "type": row.master_type,
        "code": row.code,
        "name": row.name,
        "parent_id": row.parent_id,
        "active": row.active,
        "sort_order": row.sort_order or 0,
        "custom": row.custom or {},
    }


@router.get("/masters/types")
def master_types(_user: CurrentUser) -> dict:
    return {"types": sorted(MASTER_TYPES)}


@router.get("/masters/{master_type}")
def masters_list(master_type: str, user: CurrentUser, db: DbDep, active_only: bool = True) -> list:
    mt = master_type.strip().lower()
    if mt not in MASTER_TYPES:
        raise HTTPException(400, f"Unknown master type: {master_type}")
    q = db.query(LookupMaster).filter(
        LookupMaster.company_id == user.company_id,
        LookupMaster.master_type == mt,
    )
    if active_only:
        q = q.filter(LookupMaster.active.is_(True))
    rows = q.order_by(LookupMaster.sort_order, LookupMaster.name).all()
    return [_serialize(r) for r in rows]


@router.post("/masters/{master_type}")
def masters_create(master_type: str, body: MasterIn, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*")
    mt = master_type.strip().lower()
    if mt not in MASTER_TYPES:
        raise HTTPException(400, f"Unknown master type: {master_type}")
    code = (body.code or "").strip().upper() or _code_from_name(body.name)
    exists = (
        db.query(LookupMaster)
        .filter(
            LookupMaster.company_id == user.company_id,
            LookupMaster.master_type == mt,
            LookupMaster.code == code,
        )
        .first()
    )
    if exists:
        raise HTTPException(400, f"Code {code} already exists for {mt}")
    parent_id = body.parent_id
    if body.parent_code and not parent_id:
        parent = (
            db.query(LookupMaster)
            .filter(
                LookupMaster.company_id == user.company_id,
                LookupMaster.code == body.parent_code.strip().upper(),
            )
            .first()
        )
        parent_id = parent.id if parent else None
    row = LookupMaster(
        company_id=user.company_id,
        master_type=mt,
        code=code,
        name=body.name.strip(),
        parent_id=parent_id,
        active=body.active,
        sort_order=body.sort_order or 0,
        custom=body.custom or {},
    )
    db.add(row)
    audit(db, company_id=user.company_id, user_id=user.id, action="create", entity=f"master:{mt}", entity_id=code)
    db.commit()
    db.refresh(row)
    return _serialize(row)


@router.put("/masters/{master_type}/{master_id}")
def masters_update(master_type: str, master_id: int, body: MasterIn, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*")
    mt = master_type.strip().lower()
    row = (
        db.query(LookupMaster)
        .filter(
            LookupMaster.id == master_id,
            LookupMaster.company_id == user.company_id,
            LookupMaster.master_type == mt,
        )
        .first()
    )
    if not row:
        raise HTTPException(404, "Master not found")
    if body.code:
        row.code = body.code.strip().upper()
    row.name = body.name.strip()
    row.parent_id = body.parent_id
    row.active = body.active
    row.sort_order = body.sort_order or 0
    if body.custom is not None:
        row.custom = body.custom
    audit(db, company_id=user.company_id, user_id=user.id, action="update", entity=f"master:{mt}", entity_id=row.code)
    db.commit()
    db.refresh(row)
    return _serialize(row)


@router.delete("/masters/{master_type}/{master_id}")
def masters_delete(master_type: str, master_id: int, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*")
    mt = master_type.strip().lower()
    row = (
        db.query(LookupMaster)
        .filter(
            LookupMaster.id == master_id,
            LookupMaster.company_id == user.company_id,
            LookupMaster.master_type == mt,
        )
        .first()
    )
    if not row:
        raise HTTPException(404, "Master not found")
    row.active = False
    audit(db, company_id=user.company_id, user_id=user.id, action="deactivate", entity=f"master:{mt}", entity_id=row.code)
    db.commit()
    return {"ok": True, "id": master_id}


@router.post("/masters-seed")
def masters_seed(user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*")
    created = 0

    def ensure(mt: str, code: str, name: str, sort_order: int = 0, custom: dict | None = None):
        nonlocal created
        row = (
            db.query(LookupMaster)
            .filter(
                LookupMaster.company_id == user.company_id,
                LookupMaster.master_type == mt,
                LookupMaster.code == code,
            )
            .first()
        )
        if row:
            return
        db.add(
            LookupMaster(
                company_id=user.company_id,
                master_type=mt,
                code=code,
                name=name,
                active=True,
                sort_order=sort_order,
                custom=custom or {},
            )
        )
        created += 1

    for i, (c, n) in enumerate(
        [
            ("NOS", "Numbers"),
            ("PCS", "Pieces"),
            ("MT", "Metric Ton"),
            ("KGS", "Kilograms"),
            ("BAG", "Bag"),
            ("BOX", "Box"),
            ("MTR", "Meter"),
            ("BUNDLE", "Bundle"),
            ("COIL", "Coil"),
            ("QTL", "Quintal"),
            ("PACKET", "Packet"),
            ("TIN", "Tin"),
            ("SQF", "Square Feet"),
            ("LTR", "Litre"),
        ]
    ):
        ensure("unit", c, n, i)

    for i, (c, n) in enumerate(
        [("GENERIC", "Generic"), ("JSW", "JSW"), ("JINDAL", "Jindal"), ("ASTRAL", "Astral"), ("MS-PIPE", "MS PIPE")]
    ):
        ensure("brand", c, n, i)

    for i, (c, n) in enumerate(
        [("GENERAL", "General"), ("CEMENT", "Cement"), ("ELECTRODES", "Electrodes"), ("PIPES", "Pipes"), ("CPVC", "CPVC")]
    ):
        ensure("main_group", c, n, i)
        ensure("category", c, n, i)
        ensure("sub_group", f"{c}-GEN", f"{n} General", i)

    for i, (c, n) in enumerate(
        [
            ("IN", "India"),
            ("AE", "United Arab Emirates"),
            ("OM", "Oman"),
            ("SA", "Saudi Arabia"),
            ("QA", "Qatar"),
            ("KW", "Kuwait"),
            ("BH", "Bahrain"),
            ("TZ", "Tanzania"),
            ("KE", "Kenya"),
            ("NG", "Nigeria"),
            ("US", "United States"),
            ("GB", "United Kingdom"),
            ("DE", "Germany"),
            ("SG", "Singapore"),
            ("MY", "Malaysia"),
            ("BD", "Bangladesh"),
            ("NP", "Nepal"),
            ("LK", "Sri Lanka"),
            ("OTHER", "Other"),
        ]
    ):
        ensure("country", c, n, i)

    ensure("transport", "LOCAL", "Local Transport", 0)
    ensure("agent", "DIRECT", "Direct / No Agent", 0)

    db.commit()
    return {"ok": True, "created": created}


@router.get("/print/{doc_type}/{doc_id}")
def print_document(doc_type: str, doc_id: int, user: CurrentUser, db: DbDep) -> dict:
    """White-label print payload for Invoice / Challan / SO / PO / MRN / Voucher."""
    from app.models import (
        Company,
        Customer,
        Delivery,
        GoodsReceipt,
        Invoice,
        JournalEntry,
        MaterialIssue,
        PurchaseOrder,
        SalesOrder,
        StoreReceive,
    )

    company = db.get(Company, user.company_id)
    wl = ((company.settings_json or {}).get("white_label") if company else None) or {}
    brand = {
        "app_name": wl.get("app_name") or settings.app_name,
        "logo_url": wl.get("logo_url") or settings.brand_logo_url,
        "company_name": company.name if company else settings.company_name,
        "gstin": company.gstin if company else settings.company_gstin,
        "primary": wl.get("primary") or settings.brand_primary,
        "tagline": wl.get("tagline") or settings.brand_tagline,
    }
    dt = doc_type.lower().strip()
    doc: dict = {"type": dt, "id": doc_id}

    if dt in ("invoice", "cash", "credit"):
        inv = db.query(Invoice).filter(Invoice.id == doc_id, Invoice.company_id == user.company_id).first()
        if not inv:
            raise HTTPException(404, "Invoice not found")
        cust = db.get(Customer, inv.customer_id)
        doc.update(
            {
                "number": inv.number,
                "date": inv.invoice_date.isoformat() if inv.invoice_date else "",
                "party": cust.name if cust else "",
                "lines": inv.lines or [],
                "subtotal": inv.subtotal,
                "tax": inv.tax,
                "total": inv.total,
                "paid": inv.paid,
                "status": inv.status,
                "invoice_type": inv.invoice_type,
                "custom": inv.custom or {},
            }
        )
    elif dt in ("challan", "delivery", "dc"):
        d = db.query(Delivery).filter(Delivery.id == doc_id, Delivery.company_id == user.company_id).first()
        if not d:
            raise HTTPException(404, "Challan not found")
        so = db.get(SalesOrder, d.sales_order_id) if d.sales_order_id else None
        cust = db.get(Customer, so.customer_id) if so else None
        doc.update(
            {
                "number": d.number,
                "party": cust.name if cust else "",
                "sales_order": so.number if so else "",
                "lines": d.lines or [],
                "custom": d.custom or {},
                "status": d.status,
            }
        )
    elif dt in ("so", "sales_order", "order"):
        so = db.query(SalesOrder).filter(SalesOrder.id == doc_id, SalesOrder.company_id == user.company_id).first()
        if not so:
            raise HTTPException(404, "SO not found")
        cust = db.get(Customer, so.customer_id)
        doc.update(
            {
                "number": so.number,
                "party": cust.name if cust else "",
                "lines": so.lines or [],
                "total": so.total,
                "custom": so.custom or {},
                "status": so.status,
            }
        )
    elif dt in ("po", "purchase_order"):
        po = db.query(PurchaseOrder).filter(PurchaseOrder.id == doc_id, PurchaseOrder.company_id == user.company_id).first()
        if not po:
            raise HTTPException(404, "PO not found")
        doc.update({"number": po.number, "lines": po.lines or [], "total": po.total, "custom": po.custom or {}, "status": po.status})
    elif dt in ("mrn", "grn"):
        g = db.query(GoodsReceipt).filter(GoodsReceipt.id == doc_id, GoodsReceipt.company_id == user.company_id).first()
        if not g:
            raise HTTPException(404, "MRN not found")
        doc.update({"number": g.number, "lines": g.lines or [], "custom": g.custom or {}, "status": g.status})
    elif dt in ("voucher", "journal", "payment", "receipt"):
        je = db.query(JournalEntry).filter(JournalEntry.id == doc_id, JournalEntry.company_id == user.company_id).first()
        if not je:
            raise HTTPException(404, "Voucher not found")
        doc.update(
            {
                "number": je.number,
                "voucher_type": getattr(je, "voucher_type", "journal"),
                "lines": je.lines or [],
                "narration": je.narration,
                "party_name": getattr(je, "party_name", "") or "",
                "date": je.entry_date.isoformat() if je.entry_date else "",
            }
        )
    elif dt in ("issue", "material_issue", "mi"):
        mi = db.query(MaterialIssue).filter(MaterialIssue.id == doc_id, MaterialIssue.company_id == user.company_id).first()
        if not mi:
            raise HTTPException(404, "Material Issue not found")
        custom = mi.custom or {}
        doc.update(
            {
                "number": mi.number,
                "party": custom.get("party_name") or mi.department or "",
                "party_name": custom.get("party_name") or "",
                "lines": mi.lines or [],
                "status": mi.status,
                "custom": custom,
                "narration": custom.get("remarks") or mi.purpose or "",
            }
        )
    elif dt in ("receive", "material_receive", "mr", "store_receive"):
        mr = db.query(StoreReceive).filter(StoreReceive.id == doc_id, StoreReceive.company_id == user.company_id).first()
        if not mr:
            raise HTTPException(404, "Material Receive not found")
        custom = mr.custom or {}
        doc.update(
            {
                "number": mr.number,
                "party": custom.get("party_name") or "",
                "lines": mr.lines or [],
                "status": mr.status,
                "custom": custom,
                "narration": custom.get("remarks") or "",
            }
        )
    else:
        raise HTTPException(400, f"Unknown print type: {doc_type}")

    return {"ok": True, "brand": brand, "document": doc, "print_ready": True}
