"""Kanha field & ops excellence: pending board, visits, tasks, followups, PR, payments, MIS."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func

from app.core.deps import CurrentUser, DbDep, audit, next_number
from app.models import (
    ApprovalRequest,
    Customer,
    Delivery,
    Employee,
    FieldTask,
    FieldVisit,
    FollowUp,
    Invoice,
    Lead,
    LeaveRequest,
    MaterialIndent,
    PaymentRequest,
    PurchaseOrder,
    PurchaseRequisition,
    SalesOrder,
    Vendor,
    WorkOrder,
)

router = APIRouter(prefix="/api", tags=["ops-board"])


def _today() -> date:
    return date.today()


@router.get("/ops-board/pending")
def ops_board_pending(user: CurrentUser, db: DbDep) -> dict:
    """Live pending tiles for command-center home — repair-only, never deletes data."""
    cid = user.company_id
    today = _today()
    tomorrow = today + timedelta(days=1)

    pending_po = (
        db.query(PurchaseOrder)
        .filter(PurchaseOrder.company_id == cid, PurchaseOrder.status.in_(["draft", "pending", "ordered"]))
        .count()
    )
    pending_lead = (
        db.query(Lead).filter(Lead.company_id == cid, Lead.stage.in_(["new", "qualified"])).count()
    )
    pending_so = (
        db.query(SalesOrder)
        .filter(
            SalesOrder.company_id == cid,
            SalesOrder.status.in_(["confirmed", "draft"]),
        )
        .count()
    )
    so_approval = (
        db.query(SalesOrder)
        .filter(SalesOrder.company_id == cid, SalesOrder.approval_status == "pending")
        .count()
    )
    pending_challan = (
        db.query(Delivery)
        .filter(Delivery.company_id == cid, Delivery.status.in_(["draft", "packed", "dispatched"]))
        .count()
    )
    pending_pr = (
        db.query(PurchaseRequisition)
        .filter(PurchaseRequisition.company_id == cid, PurchaseRequisition.status == "pending")
        .count()
    )
    pending_visit = (
        db.query(FieldVisit)
        .filter(FieldVisit.company_id == cid, FieldVisit.status == "planned")
        .count()
    )
    pending_followup = (
        db.query(FollowUp).filter(FollowUp.company_id == cid, FollowUp.status == "open").count()
    )
    today_fu = (
        db.query(FollowUp)
        .filter(
            FollowUp.company_id == cid,
            FollowUp.next_followup_date == today,
            FollowUp.status == "open",
        )
        .count()
    )
    tom_fu = (
        db.query(FollowUp)
        .filter(
            FollowUp.company_id == cid,
            FollowUp.next_followup_date == tomorrow,
            FollowUp.status == "open",
        )
        .count()
    )
    pending_indent = (
        db.query(MaterialIndent)
        .filter(MaterialIndent.company_id == cid, MaterialIndent.status == "pending")
        .count()
    )
    pending_pay_req = (
        db.query(PaymentRequest)
        .filter(PaymentRequest.company_id == cid, PaymentRequest.status == "pending")
        .count()
    )
    pending_tasks = (
        db.query(FieldTask).filter(FieldTask.company_id == cid, FieldTask.status.in_(["open", "doing"])).count()
    )
    hier_appr = (
        db.query(ApprovalRequest)
        .filter(ApprovalRequest.company_id == cid, ApprovalRequest.status == "pending")
        .count()
    )
    leaves = (
        db.query(LeaveRequest).filter(LeaveRequest.company_id == cid, LeaveRequest.status == "pending").count()
    )
    todo = pending_tasks + today_fu + pending_pay_req

    tiles = [
        {"key": "pending_po", "label": "Pending PO", "count": pending_po, "href": "#/purchase", "tone": "blue"},
        {"key": "pending_lead", "label": "Pending Lead", "count": pending_lead, "href": "#/crm", "tone": "green"},
        {"key": "so_approval", "label": "SO Approval", "count": so_approval, "href": "#/approvals", "tone": "amber"},
        {"key": "todo", "label": "TO DO", "count": todo, "href": "#/tasks", "tone": "rose"},
        {"key": "pending_visit", "label": "Pending Visit", "count": pending_visit, "href": "#/visit", "tone": "cyan"},
        {"key": "pending_pr", "label": "Pending PR", "count": pending_pr, "href": "#/purchase", "tone": "violet"},
        {"key": "pending_so", "label": "Pending SO", "count": pending_so, "href": "#/sales", "tone": "blue"},
        {"key": "pending_challan", "label": "Pending Challan", "count": pending_challan, "href": "#/sales", "tone": "green"},
        {"key": "hier_appr", "label": "In Approval", "count": hier_appr, "href": "#/approvals", "tone": "amber"},
        {"key": "pending_followup", "label": "Pending Followup", "count": pending_followup, "href": "#/followup", "tone": "rose"},
        {"key": "today_reminder", "label": "Today Reminder", "count": today_fu, "href": "#/followup", "tone": "cyan"},
        {"key": "tomorrow_reminder", "label": "Tomorrow Reminder", "count": tom_fu, "href": "#/followup", "tone": "violet"},
        {"key": "pending_indent", "label": "Pending Indent", "count": pending_indent, "href": "#/indents", "tone": "blue"},
        {"key": "finance_scheduler", "label": "Payment Requests", "count": pending_pay_req, "href": "#/payments-ops", "tone": "green"},
        {"key": "leaves", "label": "Leave Approvals", "count": leaves, "href": "#/hrms", "tone": "amber"},
    ]
    return {
        "ok": True,
        "date": today.isoformat(),
        "tiles": tiles,
        "total_pending": sum(t["count"] for t in tiles),
        "kanha_value": [
            "Pending Ops board + action hubs",
            "Visit / Task / Followup field desk",
            "PR -> RFQ -> PO purchase path",
            "Payment requests + outstanding",
            "Indents + MIS analytics",
            "Tally handoff JSON pack",
            "Kanha Books (own vouchers + day book)",
            "Cash/Bank books + bank recon + cost centres",
            "GSTR-3B desk + multi-godown stock",
            "Production challan → godown receive",
            "Smart alerts + health score",
            "AR/AP ageing + WhatsApp chase drafts",
            "Party ledger + voucher reverse (no delete)",
            "MIS month-compare + stock ageing",
            "WhatsApp-first chase + Agents",
            "HA / blackout portable packs",
            "Owner Core Control (never delete)",
            "Hierarchy approvals + emergency bypass",
            "Modern SPA + Live Flow tours",
        ],
    }


@router.get("/ops-board/actions")
def ops_board_actions(user: CurrentUser) -> dict:
    """Command-center action hubs — one clear path per job."""
    return {
        "order": [
            {"label": "Pending Lead → SO", "href": "#/crm"},
            {"label": "Create Sales Order", "href": "#/sales"},
            {"label": "SO → Delivery Challan", "href": "#/sales"},
            {"label": "Update Order / Invoice", "href": "#/sales"},
            {"label": "Sales Order Report", "href": "#/reports"},
            {"label": "Start Live Flow", "href": "#/flow"},
        ],
        "sales": [
            {"label": "Direct / Cash Invoice", "href": "#/pos"},
            {"label": "Sale Return / Credit Note", "href": "#/sales"},
            {"label": "Payment Followup", "href": "#/followup"},
            {"label": "Order Followup", "href": "#/followup"},
            {"label": "E-invoice / Compliance", "href": "#/compliance"},
            {"label": "WhatsApp Chase", "href": "#/whatsapp"},
        ],
        "purchase": [
            {"label": "Create PR", "href": "#/indents"},
            {"label": "Create PO", "href": "#/purchase"},
            {"label": "RFQ / Vendor Rate", "href": "#/rfq"},
            {"label": "GRN / MRN", "href": "#/purchase"},
            {"label": "Purchase Invoice", "href": "#/purchase"},
            {"label": "PO Report", "href": "#/reports"},
        ],
    }


# ----- Visits -----


class VisitIn(BaseModel):
    executive_name: str = ""
    client_name: str = ""
    customer_id: int | None = None
    contact_person: str = ""
    purpose: str = ""
    visit_date: date | None = None
    visit_time: str = ""
    notes: str = ""


@router.get("/visits")
def list_visits(
    user: CurrentUser,
    db: DbDep,
    status: str | None = None,
    executive: str | None = None,
) -> list[dict]:
    q = db.query(FieldVisit).filter(FieldVisit.company_id == user.company_id)
    if status:
        q = q.filter(FieldVisit.status == status)
    if executive:
        q = q.filter(FieldVisit.executive_name.ilike(f"%{executive}%"))
    rows = q.order_by(FieldVisit.id.desc()).limit(200).all()
    return [
        {
            "id": r.id,
            "plan_no": r.plan_no,
            "executive_name": r.executive_name,
            "client_name": r.client_name,
            "contact_person": r.contact_person,
            "purpose": r.purpose,
            "visit_date": r.visit_date.isoformat() if r.visit_date else None,
            "visit_time": r.visit_time,
            "status": r.status,
            "notes": r.notes,
        }
        for r in rows
    ]


@router.post("/visits")
def create_visit(body: VisitIn, user: CurrentUser, db: DbDep) -> dict:
    num = next_number(db, user.company_id, FieldVisit, "VIS")
    row = FieldVisit(
        company_id=user.company_id,
        plan_no=num,
        executive_name=body.executive_name or (user.full_name or user.email),
        client_name=body.client_name,
        customer_id=body.customer_id,
        contact_person=body.contact_person,
        purpose=body.purpose,
        visit_date=body.visit_date or _today(),
        visit_time=body.visit_time,
        notes=body.notes,
        status="planned",
        created_by=user.id,
    )
    db.add(row)
    audit(db, company_id=user.company_id, user_id=user.id, action="visit_create", entity="field_visit")
    db.commit()
    db.refresh(row)
    return {"ok": True, "id": row.id, "plan_no": row.plan_no}


@router.post("/visits/{visit_id}/status")
def visit_status(visit_id: int, user: CurrentUser, db: DbDep, status: str = "done") -> dict:
    row = db.get(FieldVisit, visit_id)
    if not row or row.company_id != user.company_id:
        raise HTTPException(404, "Visit not found")
    if status not in ("planned", "done", "cancelled"):
        raise HTTPException(400, "Invalid status")
    row.status = status
    db.commit()
    return {"ok": True, "id": row.id, "status": row.status}


# ----- Field tasks -----


class FieldTaskIn(BaseModel):
    title: str
    assignee_name: str = ""
    given_by: str = ""
    client_name: str = ""
    priority: str = "Medium"
    due_date: date | None = None
    task_type: str = "general"


@router.get("/field-tasks")
def list_field_tasks(user: CurrentUser, db: DbDep, status: str | None = None) -> list[dict]:
    q = db.query(FieldTask).filter(FieldTask.company_id == user.company_id)
    if status:
        q = q.filter(FieldTask.status == status)
    rows = q.order_by(FieldTask.id.desc()).limit(200).all()
    return [
        {
            "id": r.id,
            "title": r.title,
            "assignee_name": r.assignee_name,
            "given_by": r.given_by,
            "client_name": r.client_name,
            "priority": r.priority,
            "status": r.status,
            "due_date": r.due_date.isoformat() if r.due_date else None,
            "last_remark": r.last_remark,
            "task_type": r.task_type,
        }
        for r in rows
    ]


@router.post("/field-tasks")
def create_field_task(body: FieldTaskIn, user: CurrentUser, db: DbDep) -> dict:
    row = FieldTask(
        company_id=user.company_id,
        title=body.title,
        assignee_name=body.assignee_name,
        given_by=body.given_by or (user.full_name or user.email),
        client_name=body.client_name,
        priority=body.priority or "Medium",
        due_date=body.due_date,
        task_type=body.task_type,
        status="open",
        created_by=user.id,
    )
    db.add(row)
    audit(db, company_id=user.company_id, user_id=user.id, action="field_task_create", entity="field_task")
    db.commit()
    db.refresh(row)
    return {"ok": True, "id": row.id}


class TaskUpdateIn(BaseModel):
    status: str | None = None
    last_remark: str = ""


@router.post("/field-tasks/{task_id}/update")
def update_field_task(task_id: int, body: TaskUpdateIn, user: CurrentUser, db: DbDep) -> dict:
    row = db.get(FieldTask, task_id)
    if not row or row.company_id != user.company_id:
        raise HTTPException(404, "Task not found")
    if body.status:
        if body.status not in ("open", "doing", "done"):
            raise HTTPException(400, "Invalid status")
        row.status = body.status
        if body.status == "done":
            row.close_date = _today()
    if body.last_remark:
        row.last_remark = body.last_remark
    db.commit()
    return {"ok": True, "id": row.id, "status": row.status}


# ----- Followups -----


class FollowUpIn(BaseModel):
    followup_type: str = "order"
    party_name: str
    contact_person: str = ""
    contact_no: str = ""
    remarks: str = ""
    executive_name: str = ""
    followup_date: date | None = None
    next_followup_date: date | None = None


@router.get("/followups")
def list_followups(user: CurrentUser, db: DbDep, followup_type: str | None = None) -> list[dict]:
    q = db.query(FollowUp).filter(FollowUp.company_id == user.company_id)
    if followup_type:
        q = q.filter(FollowUp.followup_type == followup_type)
    rows = q.order_by(FollowUp.id.desc()).limit(200).all()
    return [
        {
            "id": r.id,
            "followup_type": r.followup_type,
            "party_name": r.party_name,
            "contact_person": r.contact_person,
            "contact_no": r.contact_no,
            "followup_date": r.followup_date.isoformat() if r.followup_date else None,
            "next_followup_date": r.next_followup_date.isoformat() if r.next_followup_date else None,
            "remarks": r.remarks,
            "executive_name": r.executive_name,
            "status": r.status,
        }
        for r in rows
    ]


@router.post("/followups")
def create_followup(body: FollowUpIn, user: CurrentUser, db: DbDep) -> dict:
    row = FollowUp(
        company_id=user.company_id,
        followup_type=body.followup_type or "order",
        party_name=body.party_name,
        contact_person=body.contact_person,
        contact_no=body.contact_no,
        remarks=body.remarks,
        executive_name=body.executive_name or (user.full_name or user.email),
        followup_date=body.followup_date or _today(),
        next_followup_date=body.next_followup_date or (_today() + timedelta(days=3)),
        status="open",
        created_by=user.id,
    )
    db.add(row)
    audit(db, company_id=user.company_id, user_id=user.id, action="followup_create", entity="follow_up")
    db.commit()
    db.refresh(row)
    return {"ok": True, "id": row.id}


@router.post("/followups/{fid}/close")
def close_followup(fid: int, user: CurrentUser, db: DbDep) -> dict:
    row = db.get(FollowUp, fid)
    if not row or row.company_id != user.company_id:
        raise HTTPException(404, "Not found")
    row.status = "closed"
    db.commit()
    return {"ok": True}


# ----- Purchase requisition -----


class PRIn(BaseModel):
    requested_by: str = ""
    department: str = ""
    notes: str = ""
    lines: list[dict[str, Any]] = Field(default_factory=list)


@router.get("/purchase/requisitions")
def list_prs(user: CurrentUser, db: DbDep) -> list[dict]:
    rows = (
        db.query(PurchaseRequisition)
        .filter(PurchaseRequisition.company_id == user.company_id)
        .order_by(PurchaseRequisition.id.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": r.id,
            "number": r.number,
            "requested_by": r.requested_by,
            "department": r.department,
            "status": r.status,
            "lines": r.lines or [],
            "notes": r.notes,
        }
        for r in rows
    ]


@router.post("/purchase/requisitions")
def create_pr(body: PRIn, user: CurrentUser, db: DbDep) -> dict:
    num = next_number(db, user.company_id, PurchaseRequisition, "PR")
    row = PurchaseRequisition(
        company_id=user.company_id,
        number=num,
        requested_by=body.requested_by or (user.full_name or user.email),
        department=body.department,
        notes=body.notes,
        lines=body.lines or [{"item": "Demo electrode", "qty": 10, "uom": "kg"}],
        status="pending",
        created_by=user.id,
    )
    db.add(row)
    audit(db, company_id=user.company_id, user_id=user.id, action="pr_create", entity="purchase_requisition")
    db.commit()
    db.refresh(row)
    return {"ok": True, "id": row.id, "number": row.number}


@router.post("/purchase/requisitions/{pr_id}/approve")
def approve_pr(pr_id: int, user: CurrentUser, db: DbDep) -> dict:
    row = db.get(PurchaseRequisition, pr_id)
    if not row or row.company_id != user.company_id:
        raise HTTPException(404, "PR not found")
    row.status = "approved"
    db.commit()
    return {"ok": True, "status": row.status}


@router.post("/purchase/requisitions/{pr_id}/convert-po")
def convert_pr_to_po(pr_id: int, user: CurrentUser, db: DbDep) -> dict:
    """Approved PR → draft Purchase Order (full PR→PO path)."""
    row = db.get(PurchaseRequisition, pr_id)
    if not row or row.company_id != user.company_id:
        raise HTTPException(404, "PR not found")
    if row.status not in ("approved", "pending"):
        raise HTTPException(400, f"Cannot convert PR in status {row.status}")
    vendor = db.query(Vendor).filter(Vendor.company_id == user.company_id).first()
    if not vendor:
        raise HTTPException(400, "Add a vendor in Purchase first")
    lines = []
    subtotal = 0.0
    for ln in row.lines or []:
        qty = float(ln.get("qty") or 1)
        rate = float(ln.get("rate") or ln.get("approx_rate") or 100)
        amt = qty * rate
        subtotal += amt
        lines.append(
            {
                "item": ln.get("item") or ln.get("name") or "Item",
                "qty": qty,
                "uom": ln.get("uom") or "kg",
                "rate": rate,
                "amount": amt,
            }
        )
    if not lines:
        lines = [{"item": "From PR", "qty": 1, "uom": "nos", "rate": 100, "amount": 100}]
        subtotal = 100.0
    tax = round(subtotal * 0.18, 2)
    po = PurchaseOrder(
        company_id=user.company_id,
        number=next_number(db, user.company_id, PurchaseOrder, "PO"),
        vendor_id=vendor.id,
        status="draft",
        subtotal=subtotal,
        tax=tax,
        total=subtotal + tax,
        lines=lines,
    )
    db.add(po)
    row.status = "converted"
    audit(db, company_id=user.company_id, user_id=user.id, action="pr_to_po", entity="purchase_order")
    db.commit()
    db.refresh(po)
    return {"ok": True, "po_id": po.id, "po_number": po.number, "pr_status": row.status}


@router.post("/indents/{iid}/to-pr")
def indent_to_pr(iid: int, user: CurrentUser, db: DbDep) -> dict:
    """Approved indent → Purchase Requisition."""
    ind = db.get(MaterialIndent, iid)
    if not ind or ind.company_id != user.company_id:
        raise HTTPException(404, "Indent not found")
    if ind.status == "pending":
        ind.status = "approved"
    num = next_number(db, user.company_id, PurchaseRequisition, "PR")
    pr = PurchaseRequisition(
        company_id=user.company_id,
        number=num,
        requested_by=user.full_name or user.email,
        department="Store",
        notes=f"From indent {ind.number} · {ind.purpose}",
        lines=ind.lines or [{"item": "Store item", "qty": 1, "uom": "nos"}],
        status="pending",
        created_by=user.id,
    )
    db.add(pr)
    ind.status = "issued"
    db.commit()
    db.refresh(pr)
    return {"ok": True, "pr_id": pr.id, "pr_number": pr.number}


@router.post("/rfq/{qid}/to-po")
def rfq_to_po(qid: int, user: CurrentUser, db: DbDep) -> dict:
    """Vendor rate quote → Purchase Order draft."""
    from app.models import VendorRateQuote

    q = db.get(VendorRateQuote, qid)
    if not q or q.company_id != user.company_id:
        raise HTTPException(404, "RFQ not found")
    vendor = (
        db.query(Vendor)
        .filter(Vendor.company_id == user.company_id, Vendor.name.ilike(f"%{q.vendor_name}%"))
        .first()
    )
    if not vendor:
        vendor = db.query(Vendor).filter(Vendor.company_id == user.company_id).first()
    if not vendor:
        raise HTTPException(400, "Add a vendor in Purchase first")
    qty = float(q.qty or 1)
    rate = float(q.rate or 0)
    subtotal = qty * rate
    tax = round(subtotal * 0.18, 2)
    po = PurchaseOrder(
        company_id=user.company_id,
        number=next_number(db, user.company_id, PurchaseOrder, "PO"),
        vendor_id=vendor.id,
        status="draft",
        subtotal=subtotal,
        tax=tax,
        total=subtotal + tax,
        lines=[{"item": q.item_name, "qty": qty, "uom": q.uom, "rate": rate, "amount": subtotal}],
    )
    db.add(po)
    q.status = "ordered"
    db.commit()
    db.refresh(po)
    return {"ok": True, "po_id": po.id, "po_number": po.number}


@router.get("/production/challans")
def list_prod_challans(user: CurrentUser, db: DbDep) -> list[dict]:
    from app.models import ProductionChallan

    rows = (
        db.query(ProductionChallan)
        .filter(ProductionChallan.company_id == user.company_id)
        .order_by(ProductionChallan.id.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": r.id,
            "number": r.number,
            "work_order_id": r.work_order_id,
            "product_id": r.product_id,
            "warehouse_id": r.warehouse_id,
            "product_name": r.product_name,
            "qty": r.qty,
            "status": r.status,
            "notes": r.notes,
        }
        for r in rows
    ]


@router.post("/production/challans/from-wo/{wo_id}")
def challan_from_wo(wo_id: int, user: CurrentUser, db: DbDep) -> dict:
    """Issue production challan from work order (shop-floor handoff)."""
    from app.models import ProductionChallan, Product

    wo = db.get(WorkOrder, wo_id)
    if not wo or wo.company_id != user.company_id:
        raise HTTPException(404, "Work order not found")
    if (wo.status or "").lower() not in ("completed", "in_progress", "released"):
        raise HTTPException(400, "Advance WO to in_progress/completed first")
    prod = db.get(Product, wo.product_id)
    from app.models import Warehouse

    wh = db.query(Warehouse).filter(Warehouse.company_id == user.company_id).first()
    row = ProductionChallan(
        company_id=user.company_id,
        number=next_number(db, user.company_id, ProductionChallan, "PC"),
        work_order_id=wo.id,
        product_id=wo.product_id,
        warehouse_id=wh.id if wh else None,
        product_name=(prod.name if prod else f"Product#{wo.product_id}"),
        qty=float(wo.qty or 0),
        status="issued",
        notes=f"From WO {wo.number}",
        created_by=user.id,
    )
    db.add(row)
    if (wo.status or "").lower() != "completed":
        wo.status = "completed"
    db.commit()
    db.refresh(row)
    return {"ok": True, "id": row.id, "number": row.number, "qty": row.qty}


@router.post("/production/challans/{cid}/receive-stock")
def challan_receive_stock(cid: int, user: CurrentUser, db: DbDep) -> dict:
    """Receive finished goods from production challan into godown stock."""
    from app.models import ProductionChallan, Product, StockBalance, StockMove, Warehouse

    row = db.get(ProductionChallan, cid)
    if not row or row.company_id != user.company_id:
        raise HTTPException(404, "Challan not found")
    if row.status == "received":
        raise HTTPException(400, "Already received to stock")
    wh = None
    if row.warehouse_id:
        wh = db.get(Warehouse, row.warehouse_id)
    if not wh:
        wh = db.query(Warehouse).filter(Warehouse.company_id == user.company_id).first()
    if not wh:
        raise HTTPException(400, "No warehouse/godown — create one in Inventory")
    pid = row.product_id
    if not pid:
        prod = (
            db.query(Product)
            .filter(Product.company_id == user.company_id, Product.name == row.product_name)
            .first()
        )
        pid = prod.id if prod else None
    if not pid:
        raise HTTPException(400, "Challan has no product link — recreate from WO")
    bal = (
        db.query(StockBalance)
        .filter(
            StockBalance.company_id == user.company_id,
            StockBalance.warehouse_id == wh.id,
            StockBalance.product_id == pid,
        )
        .first()
    )
    qty = float(row.qty or 0)
    if not bal:
        bal = StockBalance(company_id=user.company_id, warehouse_id=wh.id, product_id=pid, qty=0, avg_cost=0)
        db.add(bal)
    bal.qty = float(bal.qty or 0) + qty
    db.add(
        StockMove(
            company_id=user.company_id,
            product_id=pid,
            warehouse_id=wh.id,
            qty=qty,
            move_type="receipt",
            ref=row.number,
            notes="Production challan receive",
        )
    )
    row.status = "received"
    row.warehouse_id = wh.id
    row.product_id = pid

    wip_info = {}
    try:
        from app.models import WorkOrder
        from app.services.ops_intelligence import release_wip_to_fg

        wo = db.get(WorkOrder, row.work_order_id) if row.work_order_id else None
        wip_info = release_wip_to_fg(db, wo, qty=qty, warehouse_id=wh.id, product_id=pid, ref=row.number)
        if wo and wo.status != "completed":
            wo.status = "completed"
    except Exception:
        wip_info = {}

    db.commit()
    return {
        "ok": True,
        "challan": row.number,
        "qty": qty,
        "warehouse": wh.code,
        "stock_qty": bal.qty,
        "wip": wip_info,
        "message": f"FG +{qty} → {wh.code}" + (f" · WIP→FG ₹{wip_info.get('fg_value', 0)}" if wip_info.get("fg_value") else ""),
    }


@router.get("/inventory/godown-stock")
def godown_stock(user: CurrentUser, db: DbDep) -> dict:
    """Multi-godown stock snapshot for market-ready inventory desk."""
    from app.models import Product, StockBalance, Warehouse

    whs = db.query(Warehouse).filter(Warehouse.company_id == user.company_id).all()
    bals = db.query(StockBalance).filter(StockBalance.company_id == user.company_id).all()
    prods = {p.id: p for p in db.query(Product).filter(Product.company_id == user.company_id).all()}
    by_wh = []
    for w in whs:
        lines = []
        for b in bals:
            if b.warehouse_id != w.id:
                continue
            p = prods.get(b.product_id)
            lines.append(
                {
                    "product_id": b.product_id,
                    "sku": p.sku if p else "",
                    "name": p.name if p else str(b.product_id),
                    "qty": b.qty,
                    "avg_cost": b.avg_cost,
                }
            )
        by_wh.append({"warehouse_id": w.id, "code": w.code, "name": w.name, "lines": lines, "skus": len(lines)})
    return {"ok": True, "godowns": by_wh, "godown_count": len(whs)}


# ----- Payment requests + outstanding -----


class PayReqIn(BaseModel):
    party_name: str
    party_type: str = "vendor"
    amount: float
    purpose: str = ""


@router.get("/payment-requests")
def list_pay_reqs(user: CurrentUser, db: DbDep) -> list[dict]:
    rows = (
        db.query(PaymentRequest)
        .filter(PaymentRequest.company_id == user.company_id)
        .order_by(PaymentRequest.id.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": r.id,
            "number": r.number,
            "party_name": r.party_name,
            "party_type": r.party_type,
            "amount": r.amount,
            "purpose": r.purpose,
            "status": r.status,
        }
        for r in rows
    ]


@router.post("/payment-requests")
def create_pay_req(body: PayReqIn, user: CurrentUser, db: DbDep) -> dict:
    num = next_number(db, user.company_id, PaymentRequest, "PREQ")
    row = PaymentRequest(
        company_id=user.company_id,
        number=num,
        party_name=body.party_name,
        party_type=body.party_type,
        amount=float(body.amount),
        purpose=body.purpose,
        status="pending",
        created_by=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"ok": True, "id": row.id, "number": row.number}


@router.post("/payment-requests/{rid}/process")
def process_pay_req(rid: int, user: CurrentUser, db: DbDep, status: str = "approved") -> dict:
    row = db.get(PaymentRequest, rid)
    if not row or row.company_id != user.company_id:
        raise HTTPException(404, "Not found")
    if status not in ("approved", "paid", "rejected"):
        raise HTTPException(400, "Invalid status")
    row.status = status
    db.commit()
    return {"ok": True, "status": row.status}


@router.get("/outstanding/summary")
def outstanding_summary(user: CurrentUser, db: DbDep) -> dict:
    from app.services.ops_intelligence import vendor_pi_outstanding

    cid = user.company_id
    buyer = []
    for inv in db.query(Invoice).filter(Invoice.company_id == cid).all():
        if (inv.invoice_type or "sales") == "credit":
            continue
        bal = max(0.0, float(inv.total) - float(inv.paid or 0))
        if bal <= 0:
            continue
        cust = db.get(Customer, inv.customer_id) if inv.customer_id else None
        buyer.append(
            {
                "party": cust.name if cust else f"Customer#{inv.customer_id}",
                "ref": inv.number,
                "total": inv.total,
                "paid": inv.paid,
                "balance": round(bal, 2),
            }
        )
    vendor = vendor_pi_outstanding(db, cid)
    return {
        "buyer_outstanding": buyer[:50],
        "vendor_outstanding": vendor[:50],
        "buyer_total": round(sum(x["balance"] for x in buyer), 2),
        "vendor_total": round(sum(x["balance"] for x in vendor), 2),
        "note": "AR = unpaid sales invoices · AP = unpaid purchase invoices (not PO proxy)",
    }


# ----- Indents -----


class IndentIn(BaseModel):
    purpose: str = "production"
    notes: str = ""
    lines: list[dict[str, Any]] = Field(default_factory=list)


@router.get("/indents")
def list_indents(user: CurrentUser, db: DbDep) -> list[dict]:
    rows = (
        db.query(MaterialIndent)
        .filter(MaterialIndent.company_id == user.company_id)
        .order_by(MaterialIndent.id.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": r.id,
            "number": r.number,
            "purpose": r.purpose,
            "status": r.status,
            "lines": r.lines or [],
            "notes": r.notes,
        }
        for r in rows
    ]


@router.post("/indents")
def create_indent(body: IndentIn, user: CurrentUser, db: DbDep) -> dict:
    num = next_number(db, user.company_id, MaterialIndent, "IND")
    row = MaterialIndent(
        company_id=user.company_id,
        number=num,
        purpose=body.purpose,
        notes=body.notes,
        lines=body.lines or [{"item": "Raw electrode mix", "qty": 50, "uom": "kg"}],
        status="pending",
        created_by=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"ok": True, "id": row.id, "number": row.number}


@router.post("/indents/{iid}/approve")
def approve_indent(iid: int, user: CurrentUser, db: DbDep) -> dict:
    row = db.get(MaterialIndent, iid)
    if not row or row.company_id != user.company_id:
        raise HTTPException(404, "Not found")
    row.status = "approved"
    db.commit()
    return {"ok": True}


# ----- MIS (marketing / sales intelligence) -----


@router.get("/mis/sales-summary")
def mis_sales_summary(user: CurrentUser, db: DbDep) -> dict:
    cid = user.company_id
    invs = db.query(Invoice).filter(Invoice.company_id == cid).all()
    by_month: dict[str, float] = {}
    for i in invs:
        if getattr(i, "invoice_date", None) and i.invoice_date:
            key = i.invoice_date.strftime("%Y-%m")
        else:
            key = datetime.utcnow().strftime("%Y-%m")
        by_month[key] = by_month.get(key, 0) + float(i.total or 0)

    pos = db.query(PurchaseOrder).filter(PurchaseOrder.company_id == cid).all()
    purchase_month: dict[str, float] = {}
    for p in pos:
        key = datetime.utcnow().strftime("%Y-%m")
        purchase_month[key] = purchase_month.get(key, 0) + float(p.total or 0)

    client: dict[str, float] = {}
    for i in invs:
        cust = db.get(Customer, i.customer_id) if i.customer_id else None
        name = cust.name if cust else "Unknown"
        client[name] = client.get(name, 0) + float(i.total or 0)

    category: dict[str, float] = {}
    for i in invs:
        for line in i.lines or []:
            cat = (line.get("name") or line.get("sku") or "Other")[:40]
            category[cat] = category.get(cat, 0) + float(
                line.get("amount") or line.get("qty", 0) * line.get("rate", 0) or 0
            )

    emps = db.query(Employee).filter(Employee.company_id == cid).all()
    salesman = {e.full_name: float(e.basic_salary or 0) for e in emps[:8]}

    return {
        "monthly_sales": [{"month": k, "amount": round(v, 2)} for k, v in sorted(by_month.items())[-6:]],
        "monthly_purchase": [{"month": k, "amount": round(v, 2)} for k, v in sorted(purchase_month.items())[-6:]],
        "by_client": [{"name": k, "amount": round(v, 2)} for k, v in sorted(client.items(), key=lambda x: -x[1])[:12]],
        "by_category": [{"name": k, "amount": round(v, 2)} for k, v in sorted(category.items(), key=lambda x: -x[1])[:12]],
        "by_salesman": [{"name": k, "amount": round(v, 2)} for k, v in list(salesman.items())],
        "kanha_extras": [
            "WhatsApp chase from same login",
            "Cash / stock / compliance agents",
            "Pending board + Core Control health",
            "Portable HA / blackout resilience",
        ],
    }


# ----- RFQ (vendor rate) -----


class RfqIn(BaseModel):
    vendor_name: str = ""
    item_name: str
    rate: float
    qty: float = 1
    uom: str = "kg"
    notes: str = ""


@router.get("/rfq")
def list_rfq(user: CurrentUser, db: DbDep) -> list[dict]:
    from app.models import VendorRateQuote

    rows = (
        db.query(VendorRateQuote)
        .filter(VendorRateQuote.company_id == user.company_id)
        .order_by(VendorRateQuote.id.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": r.id,
            "vendor_name": r.vendor_name,
            "item_name": r.item_name,
            "rate": r.rate,
            "qty": r.qty,
            "uom": r.uom,
            "status": r.status,
            "notes": r.notes,
        }
        for r in rows
    ]


@router.post("/rfq")
def create_rfq(body: RfqIn, user: CurrentUser, db: DbDep) -> dict:
    from app.models import VendorRateQuote

    row = VendorRateQuote(
        company_id=user.company_id,
        vendor_name=body.vendor_name,
        item_name=body.item_name,
        rate=float(body.rate),
        qty=float(body.qty),
        uom=body.uom,
        notes=body.notes,
        status="active",
        created_by=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "ok": True,
        "id": row.id,
        "vendor_name": row.vendor_name,
        "item_name": row.item_name,
        "rate": row.rate,
        "qty": row.qty,
        "uom": row.uom,
        "status": row.status,
    }


# ----- Tally-ready export (ledgers + vouchers snapshot) -----


@router.get("/tally/export-pack")
def tally_export_pack(user: CurrentUser, db: DbDep) -> dict:
    """JSON pack for Tally / accountant handoff — no auto-push until keys configured."""
    cid = user.company_id
    customers = db.query(Customer).filter(Customer.company_id == cid).limit(200).all()
    vendors = db.query(Vendor).filter(Vendor.company_id == cid).limit(200).all()
    invs = db.query(Invoice).filter(Invoice.company_id == cid).order_by(Invoice.id.desc()).limit(100).all()
    return {
        "ok": True,
        "format": "kanha_tally_pack_v1",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "ledgers": {
            "customers": [{"name": c.name, "gstin": getattr(c, "gstin", "") or "", "code": c.code} for c in customers],
            "vendors": [{"name": v.name, "gstin": getattr(v, "gstin", "") or "", "code": v.code} for v in vendors],
        },
        "vouchers": [
            {
                "number": i.number,
                "date": i.invoice_date.isoformat() if i.invoice_date else None,
                "total": i.total,
                "tax": i.tax,
                "status": i.status,
                "type": "sales",
            }
            for i in invs
        ],
        "inactive_flags": {"ledgers": [], "items": []},
        "note": "Import into Tally via your bridge / CSV mapper. Live GSP/Tally sync is go-live keyed.",
    }
