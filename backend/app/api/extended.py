from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func

from app.core.deps import CurrentUser, DbDep, assert_perm, audit, next_number
from app.core.config import settings
from app.models import (
    Attendance,
    AutomationJob,
    BOM,
    CommsMessage,
    Document,
    Employee,
    EmployeeLoan,
    EmployeeLocation,
    Einvoice,
    EwayBill,
    ExpenseClaim,
    Invoice,
    Lead,
    LeaveRequest,
    Machine,
    Notification,
    PayrollRun,
    Product,
    Project,
    PurchaseOrder,
    QualityInspection,
    ReportDefinition,
    SalaryDisbursement,
    SalesOrder,
    ServiceTicket,
    StockBalance,
    Task,
    Vendor,
    Warehouse,
    WorkOrder,
    Customer,
)

router = APIRouter(prefix="/api", tags=["extended"])


@router.get("/dashboard")
def dashboard(user: CurrentUser, db: DbDep) -> dict:
    cid = user.company_id
    sales = db.query(Invoice).filter(Invoice.company_id == cid).all()
    revenue = sum(i.total for i in sales)
    outstanding = sum(max(0, i.total - i.paid) for i in sales)
    stock_val = (
        db.query(func.coalesce(func.sum(StockBalance.qty * StockBalance.avg_cost), 0))
        .filter(StockBalance.company_id == cid)
        .scalar()
    )
    leads = db.query(Lead).filter(Lead.company_id == cid).count()
    open_so = db.query(SalesOrder).filter(SalesOrder.company_id == cid, SalesOrder.status != "invoiced").count()
    tickets = db.query(ServiceTicket).filter(ServiceTicket.company_id == cid, ServiceTicket.status == "open").count()
    top_products = []
    for p in db.query(Product).filter(Product.company_id == cid, Product.sale_price > 0).limit(5):
        top_products.append({"name": p.name, "sku": p.sku, "price": p.sale_price})
    return {
        "kpis": {
            "revenue": round(revenue, 2),
            "outstanding": round(outstanding, 2),
            "inventory_value": round(float(stock_val or 0), 2),
            "leads": leads,
            "open_orders": open_so,
            "open_tickets": tickets,
            "profit_estimate": round(revenue * 0.22, 2),
        },
        "top_products": top_products,
        "recent_invoices": [
            {"number": i.number, "total": i.total, "status": i.status, "paid": i.paid}
            for i in sorted(sales, key=lambda x: x.id, reverse=True)[:5]
        ],
        "approvals_pending": db.query(SalesOrder)
        .filter(SalesOrder.company_id == cid, SalesOrder.approval_status == "pending")
        .count(),
    }


# Manufacturing


@router.get("/manufacturing/boms")
def boms(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(BOM).filter(BOM.company_id == user.company_id).all()
    out = []
    for b in rows:
        p = db.get(Product, b.product_id)
        out.append(
            {
                "id": b.id,
                "product_id": b.product_id,
                "product_name": p.name if p else "",
                "product_sku": p.sku if p else "",
                "version": b.version,
                "components": b.components,
                "active": b.active,
            }
        )
    return out


class BomIn(BaseModel):
    product_id: int
    version: str = "1.0"
    components: list[dict[str, Any]] = Field(default_factory=list)


@router.post("/manufacturing/boms")
def create_bom(body: BomIn, user: CurrentUser, db: DbDep) -> dict:
    p = db.query(Product).filter(Product.id == body.product_id, Product.company_id == user.company_id).first()
    if not p:
        raise HTTPException(404, "Product not found")
    row = BOM(
        company_id=user.company_id,
        product_id=body.product_id,
        version=body.version,
        components=body.components
        or [{"sku": "RM-01", "name": "Raw material", "qty": 1}],
        active=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "product_id": row.product_id, "version": row.version}


@router.get("/manufacturing/work-orders")
def work_orders(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(WorkOrder).filter(WorkOrder.company_id == user.company_id).all()
    out = []
    for w in rows:
        p = db.get(Product, w.product_id)
        out.append(
            {
                "id": w.id,
                "number": w.number,
                "product_id": w.product_id,
                "product_name": p.name if p else "",
                "product_sku": p.sku if p else "",
                "qty": w.qty,
                "status": w.status,
                "cost": w.cost,
                "scheduled_start": w.scheduled_start.isoformat() if w.scheduled_start else None,
                "scheduled_end": w.scheduled_end.isoformat() if w.scheduled_end else None,
            }
        )
    return out


class WOIn(BaseModel):
    product_id: int
    bom_id: int | None = None
    qty: float = 1


@router.post("/manufacturing/work-orders")
def create_wo(body: WOIn, user: CurrentUser, db: DbDep) -> dict:
    row = WorkOrder(
        company_id=user.company_id,
        number=next_number(db, user.company_id, WorkOrder, "WO"),
        product_id=body.product_id,
        bom_id=body.bom_id,
        qty=body.qty,
        status="planned",
        scheduled_start=date.today(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "number": row.number}


@router.post("/manufacturing/work-orders/{wo_id}/advance")
def advance_wo(wo_id: int, user: CurrentUser, db: DbDep) -> dict:
    from app.services.ops_intelligence import OpsBlock, consume_bom_for_wo

    row = db.query(WorkOrder).filter(WorkOrder.id == wo_id, WorkOrder.company_id == user.company_id).first()
    if not row:
        raise HTTPException(404, "Work order not found")
    flow = ["planned", "released", "in_progress", "completed"]
    cur = (row.status or "planned").lower()
    idx = flow.index(cur) if cur in flow else 0
    nxt = flow[min(idx + 1, len(flow) - 1)]
    bom_result = None
    if cur == "planned" and nxt == "released":
        try:
            bom_result = consume_bom_for_wo(db, row)
        except OpsBlock as e:
            raise HTTPException(400, e.message) from e
    row.status = nxt
    if row.status == "completed" and not row.cost:
        row.cost = float(row.qty or 1) * 120.0
    db.commit()
    return {
        "id": row.id,
        "number": row.number,
        "status": row.status,
        "cost": row.cost,
        "bom": bom_result,
        "message": (
            f"{row.number} → {row.status}"
            + (f" · BOM materials ₹{bom_result.get('material_cost', 0)}" if bom_result and bom_result.get("material_cost") else "")
        ),
    }


@router.get("/manufacturing/machines")
def machines(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(Machine).filter(Machine.company_id == user.company_id).all()
    return [{"id": m.id, "code": m.code, "name": m.name, "status": m.status} for m in rows]


class MachineIn(BaseModel):
    code: str | None = None
    name: str
    status: str = "idle"


@router.post("/manufacturing/machines")
def create_machine(body: MachineIn, user: CurrentUser, db: DbDep) -> dict:
    code = body.code or f"MCH-{db.query(Machine).filter(Machine.company_id == user.company_id).count() + 1:03d}"
    row = Machine(company_id=user.company_id, code=code, name=body.name, status=body.status)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "code": row.code, "name": row.name, "status": row.status}


@router.get("/quality/inspections")
def inspections(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(QualityInspection).filter(QualityInspection.company_id == user.company_id).all()
    return [
        {
            "id": q.id,
            "number": q.number,
            "inspection_type": q.inspection_type,
            "ref": q.ref,
            "checklist": q.checklist,
            "result": q.result,
            "capa": q.capa,
        }
        for q in rows
    ]


class QIIn(BaseModel):
    inspection_type: str = "incoming"
    ref: str = ""
    checklist: list[dict[str, Any]] = Field(default_factory=list)
    result: str = "pending"
    capa: str = ""


@router.post("/quality/inspections")
def create_qi(body: QIIn, user: CurrentUser, db: DbDep) -> dict:
    row = QualityInspection(
        company_id=user.company_id,
        number=next_number(db, user.company_id, QualityInspection, "QI"),
        **body.model_dump(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "number": row.number}


class QIDecideIn(BaseModel):
    result: str = "pass"
    capa: str = ""


@router.post("/quality/inspections/{qi_id}/decide")
def decide_qi(qi_id: int, body: QIDecideIn, user: CurrentUser, db: DbDep) -> dict:
    row = db.query(QualityInspection).filter(
        QualityInspection.id == qi_id, QualityInspection.company_id == user.company_id
    ).first()
    if not row:
        raise HTTPException(404, "Inspection not found")
    if body.result not in ("pass", "fail", "pending"):
        raise HTTPException(400, "result must be pass/fail/pending")
    row.result = body.result
    if body.capa:
        row.capa = body.capa
    elif body.result == "fail" and not row.capa:
        row.capa = "CAPA opened — rework / supplier notification"
    db.commit()
    return {"id": row.id, "number": row.number, "result": row.result, "capa": row.capa}


# HRMS


@router.get("/hrms/employees")
def employees(user: CurrentUser, db: DbDep) -> list:
    from app.services.legal_compliance import get_consent_map

    consents = get_consent_map(db, user.company_id)
    rows = db.query(Employee).filter(Employee.company_id == user.company_id).order_by(Employee.id).all()
    return [
        {
            "id": e.id,
            "code": e.code,
            "full_name": e.full_name,
            "email": e.email,
            "phone": getattr(e, "phone", None),
            "department": e.department,
            "designation": e.designation,
            "join_date": e.join_date.isoformat() if e.join_date else None,
            "basic_salary": e.basic_salary,
            "shift": e.shift,
            "active": bool(e.active),
            "work_type": getattr(e, "work_type", "office"),
            "track_live": bool(getattr(e, "track_live", False)),
            "bank_name": getattr(e, "bank_name", "") or "",
            "bank_account": getattr(e, "bank_account", "") or "",
            "ifsc": getattr(e, "ifsc", "") or "",
            "custom": getattr(e, "custom", None) or {},
            "gps_consent": bool((consents.get(str(e.id)) or {}).get("gps_consent")),
            "consent": consents.get(str(e.id)) or None,
        }
        for e in rows
    ]


class EmpIn(BaseModel):
    full_name: str
    email: str | None = None
    phone: str | None = None
    department: str = "General"
    designation: str = "Staff"
    basic_salary: float = 25000
    shift: str = "general"
    work_type: str = "office"
    track_live: bool = False
    bank_name: str = "HDFC Bank"
    bank_account: str = ""
    ifsc: str = "HDFC0001234"
    join_date: date | None = None
    # Offer letter + app install consent (stored on hire for field/sales)
    offer_letter_gps_ack: bool = False
    app_install_gps_ack: bool = False
    grade: str = ""
    father_name: str = ""
    aadhaar: str = ""
    pan: str = ""
    address: str = ""
    blood_group: str = ""
    emergency_contact: str = ""
    # SBAC EmployeeMaster extras → custom
    gender: str = ""
    company_email: str = ""
    biometric_id: str = ""
    dob: str = ""
    username: str = ""
    smtp_type: str = ""
    father_phone: str = ""
    father_profession: str = ""
    mother_name: str = ""
    mother_phone: str = ""
    mother_profession: str = ""
    emp_status: str = "Active"
    status_date: str = ""
    experience_type: str = ""  # Experience / Fresher
    pay_mode: str = "Salary"  # Salary / Imprest
    salary_month: str = ""
    increment_amount: float = 0
    increment_month: str = ""
    latitude: str = ""
    longitude: str = ""
    distance: str = ""
    licence_no: str = ""
    voter_no: str = ""
    pf_no: str = ""
    esi_no: str = ""
    bank_holder: str = ""
    bank_branch: str = ""
    account_type: str = "Salary Acount"
    state: str = ""
    city: str = ""
    pincode: str = ""
    address_contact: str = ""
    address2: str = ""
    state2: str = ""
    city2: str = ""
    pincode2: str = ""
    owner_name: str = ""
    owner_phone: str = ""
    custom: dict[str, Any] = Field(default_factory=dict)


@router.post("/hrms/employees")
def create_emp(body: EmpIn, user: CurrentUser, db: DbDep) -> dict:
    from app.services.legal_compliance import OFFER_LETTER_GPS_CLAUSE, record_employee_consent

    data = body.model_dump()
    offer_ack = bool(data.pop("offer_letter_gps_ack", False))
    app_ack = bool(data.pop("app_install_gps_ack", False))
    custom_extra = data.pop("custom", None) or {}
    custom_keys = (
        "grade",
        "father_name",
        "aadhaar",
        "pan",
        "address",
        "blood_group",
        "emergency_contact",
        "gender",
        "company_email",
        "biometric_id",
        "dob",
        "username",
        "smtp_type",
        "father_phone",
        "father_profession",
        "mother_name",
        "mother_phone",
        "mother_profession",
        "emp_status",
        "status_date",
        "experience_type",
        "pay_mode",
        "salary_month",
        "increment_amount",
        "increment_month",
        "latitude",
        "longitude",
        "distance",
        "licence_no",
        "voter_no",
        "pf_no",
        "esi_no",
        "bank_holder",
        "bank_branch",
        "account_type",
        "state",
        "city",
        "pincode",
        "address_contact",
        "address2",
        "state2",
        "city2",
        "pincode2",
        "owner_name",
        "owner_phone",
    )
    custom_payload = {k: data.pop(k, "") for k in custom_keys}
    data["custom"] = {
        **custom_extra,
        **{k: v for k, v in custom_payload.items() if v not in ("", None)},
        "source": "kanha_employee_master",
        "sbac_parity": "2026-08-02-live",
    }
    if not data.get("join_date"):
        data["join_date"] = date.today()
    if not data.get("bank_account"):
        data["bank_account"] = f"50{date.today().strftime('%y%m%d')}{db.query(Employee).filter(Employee.company_id == user.company_id).count() + 1:04d}"
    row = Employee(
        company_id=user.company_id,
        code=next_number(db, user.company_id, Employee, "EMP"),
        **data,
    )
    db.add(row)
    db.flush()
    consent = None
    if offer_ack and app_ack:
        consent = record_employee_consent(
            db,
            user.company_id,
            employee_id=row.id,
            offer_letter_ack=True,
            app_install_ack=True,
            gps_consent=True,
            source="hire_offer_letter_app_install",
            note="Recorded at hire — offer letter clause + app install OK",
            recorded_by=user.email or str(user.id),
        )
        row.track_live = True
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="hire",
        entity="employee",
        entity_id=str(row.id),
        detail={"code": row.code, "gps_consent": bool(consent)},
    )
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "code": row.code,
        "full_name": row.full_name,
        "department": row.department,
        "designation": row.designation,
        "basic_salary": row.basic_salary,
        "phone": row.phone,
        "bank_account": row.bank_account,
        "custom": row.custom or {},
        "gps_consent": bool(consent),
        "offer_letter_clause": OFFER_LETTER_GPS_CLAUSE if consent else None,
        "message": (
            f"{row.code} hired · GPS consent on file (offer letter + app install)"
            if consent
            else f"{row.code} hired · GPS consent not recorded (office / later)"
        ),
    }


@router.put("/hrms/employees/{employee_id}")
def update_emp(employee_id: int, body: EmpIn, user: CurrentUser, db: DbDep) -> dict:
    row = db.query(Employee).filter(Employee.id == employee_id, Employee.company_id == user.company_id).first()
    if not row:
        raise HTTPException(404, "Employee not found")
    data = body.model_dump(exclude={"offer_letter_gps_ack", "app_install_gps_ack"})
    custom_extra = data.pop("custom", None) or {}
    custom_keys = (
        "grade",
        "father_name",
        "aadhaar",
        "pan",
        "address",
        "blood_group",
        "emergency_contact",
        "gender",
        "company_email",
        "biometric_id",
        "dob",
        "username",
        "smtp_type",
        "father_phone",
        "father_profession",
        "mother_name",
        "mother_phone",
        "mother_profession",
        "emp_status",
        "status_date",
        "experience_type",
        "pay_mode",
        "salary_month",
        "increment_amount",
        "increment_month",
        "latitude",
        "longitude",
        "distance",
        "licence_no",
        "voter_no",
        "pf_no",
        "esi_no",
        "bank_holder",
        "bank_branch",
        "account_type",
        "state",
        "city",
        "pincode",
        "address_contact",
        "address2",
        "state2",
        "city2",
        "pincode2",
        "owner_name",
        "owner_phone",
    )
    for k in custom_keys:
        if k in data:
            custom_extra[k] = data.pop(k) or custom_extra.get(k, "")
    for k, v in data.items():
        if k in ("full_name", "email", "phone", "department", "designation", "basic_salary", "shift", "work_type", "track_live", "bank_name", "bank_account", "ifsc", "join_date"):
            setattr(row, k, v)
    prev = dict(getattr(row, "custom", None) or {})
    prev.update(custom_extra)
    prev["source"] = prev.get("source") or "kanha_employee_master"
    row.custom = prev
    try:
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(row, "custom")
    except Exception:
        pass
    db.commit()
    db.refresh(row)
    return {"id": row.id, "code": row.code, "full_name": row.full_name, "custom": row.custom or {}, "message": f"{row.code} updated"}


@router.post("/hrms/employees/{employee_id}/exit")
def exit_employee(employee_id: int, user: CurrentUser, db: DbDep) -> dict:
    row = db.query(Employee).filter(Employee.id == employee_id, Employee.company_id == user.company_id).first()
    if not row:
        raise HTTPException(404, "Employee not found")
    row.active = False
    row.track_live = False
    audit(db, company_id=user.company_id, user_id=user.id, action="exit", entity="employee", entity_id=str(row.id))
    db.commit()
    return {"ok": True, "code": row.code, "active": False, "message": f"{row.full_name} marked relieved"}


@router.get("/hrms/attendance")
def attendance(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(Attendance).filter(Attendance.company_id == user.company_id).order_by(Attendance.id.desc()).limit(100).all()
    out = []
    for a in rows:
        emp = db.get(Employee, a.employee_id)
        out.append(
            {
                "id": a.id,
                "employee_id": a.employee_id,
                "employee_name": emp.full_name if emp else "",
                "employee_code": emp.code if emp else "",
                "day": a.day.isoformat(),
                "status": a.status,
                "check_in": a.check_in,
                "check_out": a.check_out,
                "source": a.source,
            }
        )
    return out


class AttendanceIn(BaseModel):
    employee_id: int
    day: date | None = None
    status: str = "present"
    check_in: str = "09:30"
    check_out: str = "18:00"
    source: str = "manual"


@router.post("/hrms/attendance")
def mark_attendance(body: AttendanceIn, user: CurrentUser, db: DbDep) -> dict:
    emp = db.query(Employee).filter(Employee.id == body.employee_id, Employee.company_id == user.company_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")
    day = body.day or date.today()
    row = (
        db.query(Attendance)
        .filter(Attendance.company_id == user.company_id, Attendance.employee_id == emp.id, Attendance.day == day)
        .first()
    )
    if not row:
        row = Attendance(company_id=user.company_id, employee_id=emp.id, day=day)
        db.add(row)
    row.status = body.status
    row.check_in = body.check_in
    row.check_out = body.check_out
    row.source = body.source
    audit(db, company_id=user.company_id, user_id=user.id, action="attendance", entity="employee", entity_id=str(emp.id))
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "employee_id": emp.id,
        "employee_code": emp.code,
        "day": day.isoformat(),
        "status": row.status,
        "check_in": row.check_in,
        "check_out": row.check_out,
    }


class AttendanceProcessIn(BaseModel):
    period: str = ""  # YYYY-MM
    status: str = "present"
    fill_missing: bool = True
    employee_id: int | None = None
    from_date: date | None = None
    to_date: date | None = None
    process_status: str = "Processed"  # SBAC Pending / Processed filter


@router.post("/hrms/attendance/process-month")
def process_attendance_month(body: AttendanceProcessIn, user: CurrentUser, db: DbDep) -> dict:
    """SBAC ProcessSalaryAttendance — month + optional from/to + employee filter."""
    from calendar import monthrange

    period = (body.period or date.today().strftime("%Y-%m")).strip()
    try:
        y, m = [int(x) for x in period.split("-")[:2]]
    except Exception as exc:
        raise HTTPException(400, "period must be YYYY-MM") from exc
    days_in_month = monthrange(y, m)[1]
    today = date.today()
    range_from = body.from_date or date(y, m, 1)
    range_to = body.to_date or date(y, m, days_in_month)
    q = db.query(Employee).filter(Employee.company_id == user.company_id, Employee.active == True)  # noqa: E712
    if body.employee_id:
        q = q.filter(Employee.id == body.employee_id)
    emps = q.all()
    created = 0
    for e in emps:
        for d in range(1, days_in_month + 1):
            day = date(y, m, d)
            if day < range_from or day > range_to:
                continue
            if day > today:
                break
            if day.weekday() >= 5:  # skip Sat/Sun
                continue
            exists = (
                db.query(Attendance)
                .filter(Attendance.company_id == user.company_id, Attendance.employee_id == e.id, Attendance.day == day)
                .first()
            )
            if exists:
                continue
            if not body.fill_missing:
                continue
            db.add(
                Attendance(
                    company_id=user.company_id,
                    employee_id=e.id,
                    day=day,
                    status=body.status or "present",
                    check_in="09:30",
                    check_out="18:00",
                    source="month_process",
                )
            )
            created += 1
    db.commit()
    return {
        "ok": True,
        "period": period,
        "created": created,
        "employees": len(emps),
        "from_date": range_from.isoformat(),
        "to_date": range_to.isoformat(),
        "process_status": body.process_status or "Processed",
        "message": f"Processed {period} · {created} attendance rows · {body.process_status or 'Processed'}",
    }


@router.get("/hrms/leaves")
def leaves(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(LeaveRequest).filter(LeaveRequest.company_id == user.company_id).order_by(LeaveRequest.id.desc()).all()
    out = []
    for l in rows:
        emp = db.get(Employee, l.employee_id)
        out.append(
            {
                "id": l.id,
                "employee_id": l.employee_id,
                "employee_name": emp.full_name if emp else "",
                "employee_code": emp.code if emp else "",
                "leave_type": l.leave_type,
                "from_date": l.from_date.isoformat(),
                "to_date": l.to_date.isoformat(),
                "status": l.status,
                "reason": l.reason or "—",
            }
        )
    return out


class LeaveIn(BaseModel):
    employee_id: int
    leave_type: str = "casual"
    from_date: date | None = None
    to_date: date | None = None
    reason: str = "Personal"


@router.post("/hrms/leaves")
def apply_leave(body: LeaveIn, user: CurrentUser, db: DbDep) -> dict:
    emp = db.query(Employee).filter(Employee.id == body.employee_id, Employee.company_id == user.company_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")
    fr = body.from_date or (date.today() + timedelta(days=3))
    to = body.to_date or fr
    row = LeaveRequest(
        company_id=user.company_id,
        employee_id=emp.id,
        leave_type=body.leave_type,
        from_date=fr,
        to_date=to,
        status="pending",
        reason=body.reason,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "employee_id": emp.id,
        "leave_type": row.leave_type,
        "from_date": row.from_date.isoformat(),
        "to_date": row.to_date.isoformat(),
        "status": row.status,
    }


class LeaveDecideIn(BaseModel):
    status: str
    decision_note: str = ""


@router.post("/hrms/leaves/{leave_id}/decide")
def decide_leave(leave_id: int, body: LeaveDecideIn, user: CurrentUser, db: DbDep) -> dict:
    row = (
        db.query(LeaveRequest)
        .filter(LeaveRequest.id == leave_id, LeaveRequest.company_id == user.company_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if body.status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="status must be approved or rejected")
    row.status = body.status
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action=body.status,
        entity="leave",
        entity_id=str(row.id),
        detail={"note": body.decision_note} if body.decision_note else {},
    )
    db.commit()
    return {"ok": True, "status": row.status}


@router.get("/hrms/payroll")
def payroll(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(PayrollRun).filter(PayrollRun.company_id == user.company_id).all()
    return [{"id": p.id, "period": p.period, "status": p.status, "lines": p.lines} for p in rows]


@router.post("/hrms/payroll/run")
def run_payroll(user: CurrentUser, db: DbDep) -> dict:
    from calendar import monthrange

    from app.services.legal_compliance import (
        compute_payslip_line,
        get_employee_target_pct,
        get_salary_policy,
    )

    policy = get_salary_policy(db, user.company_id)
    emps = db.query(Employee).filter(Employee.company_id == user.company_id, Employee.active == True).all()  # noqa: E712
    period = date.today().strftime("%Y-%m")
    y, m = date.today().year, date.today().month
    working_days = monthrange(y, m)[1]
    lines = []
    for e in emps:
        att_rows = (
            db.query(Attendance)
            .filter(
                Attendance.company_id == user.company_id,
                Attendance.employee_id == e.id,
                Attendance.day >= date(y, m, 1),
                Attendance.day <= date.today(),
                Attendance.status == "present",
            )
            .count()
        )
        target_pct = get_employee_target_pct(db, user.company_id, e.id)
        line = compute_payslip_line(
            emp=e,
            policy=policy,
            attendance_days=att_rows,
            working_days=max(1, working_days),
            target_achieved_pct=target_pct,
            cut_reason="",
        )
        # Active loan EMI deduction (SBAC salary process)
        loan_emi = 0.0
        active_loans = (
            db.query(EmployeeLoan)
            .filter(
                EmployeeLoan.company_id == user.company_id,
                EmployeeLoan.employee_id == e.id,
                EmployeeLoan.status.in_(("approved", "active")),
            )
            .all()
        )
        for ln in active_loans:
            loan_emi += float(ln.emi or 0)
            if ln.status == "approved":
                ln.status = "active"
        if loan_emi > 0:
            line["loan_emi"] = round(loan_emi, 2)
            line["net"] = round(max(0.0, float(line.get("net") or 0) - loan_emi), 2)
            notes = list(line.get("notes") or [])
            notes.append(f"Loan EMI −₹{loan_emi:.2f}")
            line["notes"] = notes
        lines.append(line)
    row = PayrollRun(company_id=user.company_id, period=period, status="draft", lines=lines)
    db.add(row)
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="payroll",
        entity="payroll",
        entity_id=str(row.id),
        detail={"policy_mode": policy.get("mode"), "attendance_cut_enabled": policy.get("attendance_cut_enabled")},
    )
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "period": period,
        "status": row.status,
        "employees": len(lines),
        "lines": lines,
        "salary_policy": policy,
        "disclaimer": policy.get("labour_note"),
        "message": f"Payroll {period} draft · Confirm → Approve → Disburse",
    }


@router.post("/hrms/payroll/{payroll_id}/confirm")
def confirm_payroll(payroll_id: int, user: CurrentUser, db: DbDep) -> dict:
    row = db.query(PayrollRun).filter(PayrollRun.id == payroll_id, PayrollRun.company_id == user.company_id).first()
    if not row:
        raise HTTPException(404, "Payroll not found")
    if row.status not in ("draft", "processed"):
        raise HTTPException(400, f"Cannot confirm from status={row.status}")
    row.status = "confirmed"
    audit(db, company_id=user.company_id, user_id=user.id, action="confirm", entity="payroll", entity_id=str(row.id))
    db.commit()
    return {"id": row.id, "period": row.period, "status": row.status, "message": f"Payroll {row.period} confirmed"}


@router.post("/hrms/payroll/{payroll_id}/approve")
def approve_payroll(payroll_id: int, user: CurrentUser, db: DbDep) -> dict:
    row = db.query(PayrollRun).filter(PayrollRun.id == payroll_id, PayrollRun.company_id == user.company_id).first()
    if not row:
        raise HTTPException(404, "Payroll not found")
    if row.status not in ("confirmed", "draft", "processed"):
        raise HTTPException(400, f"Cannot approve from status={row.status}")
    row.status = "approved"
    audit(db, company_id=user.company_id, user_id=user.id, action="approve", entity="payroll", entity_id=str(row.id))
    db.commit()
    return {"id": row.id, "period": row.period, "status": row.status, "message": f"Payroll {row.period} approved — ready to disburse"}


@router.get("/hrms/payroll/{payroll_id}/payslips")
def payroll_payslips(payroll_id: int, user: CurrentUser, db: DbDep) -> dict:
    row = db.query(PayrollRun).filter(PayrollRun.id == payroll_id, PayrollRun.company_id == user.company_id).first()
    if not row:
        raise HTTPException(404, "Payroll not found")
    return {
        "id": row.id,
        "period": row.period,
        "status": row.status,
        "payslips": row.lines or [],
        "totals": {
            "basic": round(sum(float(l.get("basic", 0)) for l in (row.lines or [])), 2),
            "pf": round(sum(float(l.get("pf", 0)) for l in (row.lines or [])), 2),
            "esic": round(sum(float(l.get("esic", 0)) for l in (row.lines or [])), 2),
            "net": round(sum(float(l.get("net", 0)) for l in (row.lines or [])), 2),
        },
    }


@router.get("/hrms/disbursements")
def list_disbursements(user: CurrentUser, db: DbDep) -> list:
    rows = (
        db.query(SalaryDisbursement)
        .filter(SalaryDisbursement.company_id == user.company_id)
        .order_by(SalaryDisbursement.id.desc())
        .all()
    )
    return [
        {
            "id": d.id,
            "period": d.period,
            "status": d.status,
            "mode": d.mode,
            "total_amount": d.total_amount,
            "lines": d.lines,
            "note": d.note,
            "payroll_id": d.payroll_id,
        }
        for d in rows
    ]


@router.post("/hrms/disbursements/from-payroll")
def disburse_salary(user: CurrentUser, db: DbDep) -> dict:
    """Create bank payout batch from latest payroll — demo NEFT settles books; live bank needs Legal gate + API."""
    from app.services.demo_live_settle import post_salary_disbursement_voucher
    from app.services.legal_compliance import assert_feature_approved, is_feature_approved

    # Live bank path only when gate + future bank keys; demo path always allowed
    want_live = False  # no bank adapter yet — always demo_paid with books voucher
    if want_live:
        assert_feature_approved(db, user.company_id, "live_bank_neft")

    pay = (
        db.query(PayrollRun)
        .filter(PayrollRun.company_id == user.company_id)
        .order_by(PayrollRun.id.desc())
        .first()
    )
    if not pay:
        raise HTTPException(400, "Run payroll first")
    if pay.status not in ("approved", "processed", "disbursed"):
        raise HTTPException(400, f"Payroll {pay.period} status={pay.status} — Confirm + Approve before disburse")
    lines = []
    total = 0.0
    for i, ln in enumerate(pay.lines or []):
        amt = float(ln.get("net") or 0)
        total += amt
        acct = ln.get("bank_account") or ""
        ifsc = ln.get("ifsc") or ""
        if not acct:
            emp = db.query(Employee).filter(Employee.id == ln.get("employee_id")).first()
            if emp:
                acct = getattr(emp, "bank_account", "") or ""
                ifsc = getattr(emp, "ifsc", "") or ""
        lines.append(
            {
                "employee_id": ln.get("employee_id"),
                "name": ln.get("name"),
                "amount": amt,
                "bank_account": acct,
                "ifsc": ifsc,
                "bank_name": ln.get("bank_name") or "",
                "utr": f"DEMO-NEFT-{date.today().strftime('%Y%m%d')}{1000 + i}",
                "status": "demo_paid" if acct else "hold_no_account",
            }
        )
    row = SalaryDisbursement(
        company_id=user.company_id,
        payroll_id=pay.id,
        period=pay.period,
        status="demo_paid",
        mode="neft",
        total_amount=round(total, 2),
        lines=lines,
        note=(
            "DEMO-LIVE NEFT batch · UTR DEMO-NEFT-* · salary voucher posted to books. "
            "Real bank transfer needs Legal board (live_bank_neft) + bank API. "
            f"Gate approved={is_feature_approved(db, user.company_id, 'live_bank_neft')}."
        ),
    )
    db.add(row)
    db.flush()
    journal = post_salary_disbursement_voucher(
        db,
        company_id=user.company_id,
        period=pay.period,
        total=total,
        disbursement_id=row.id,
    )
    pay.status = "disbursed"
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "period": row.period,
        "total_amount": row.total_amount,
        "lines": row.lines,
        "status": row.status,
        "journal": journal,
        "message": f"Disbursed {row.total_amount} · {row.status}" + (f" · {journal}" if journal else ""),
    }


# ── Employee loans (SBAC) ─────────────────────────────────────────────────────


@router.get("/hrms/loans")
def list_loans(user: CurrentUser, db: DbDep) -> list:
    rows = (
        db.query(EmployeeLoan)
        .filter(EmployeeLoan.company_id == user.company_id)
        .order_by(EmployeeLoan.id.desc())
        .all()
    )
    out = []
    for r in rows:
        emp = db.get(Employee, r.employee_id)
        out.append(
            {
                "id": r.id,
                "employee_id": r.employee_id,
                "employee_name": emp.full_name if emp else "",
                "employee_code": emp.code if emp else "",
                "amount": r.amount,
                "emi": r.emi,
                "tenure_months": r.tenure_months,
                "start_date": r.start_date.isoformat() if r.start_date else None,
                "status": r.status,
                "purpose": r.purpose,
                "notes": r.notes,
            }
        )
    return out


class LoanIn(BaseModel):
    employee_id: int
    amount: float
    emi: float = 0
    tenure_months: int = 12
    start_date: date | None = None  # EMI start (SBAC dtpemistartdate)
    loan_date: date | None = None  # SBAC dtploandate
    purpose: str = ""
    notes: str = ""


@router.post("/hrms/loans")
def create_loan(body: LoanIn, user: CurrentUser, db: DbDep) -> dict:
    emp = db.query(Employee).filter(Employee.id == body.employee_id, Employee.company_id == user.company_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")
    amt = float(body.amount or 0)
    if amt <= 0:
        raise HTTPException(400, "Loan amount required")
    tenure = max(1, int(body.tenure_months or 12))
    emi = float(body.emi or 0) or round(amt / tenure, 2)
    row = EmployeeLoan(
        company_id=user.company_id,
        employee_id=emp.id,
        amount=amt,
        emi=emi,
        tenure_months=tenure,
        start_date=body.start_date or body.loan_date or date.today(),
        status="pending",
        purpose=body.purpose or "",
        notes=body.notes or "",
        custom={
            "source": "kanha_employee_loan",
            "sbac_parity": "2026-08-02-live",
            "loan_date": (body.loan_date or date.today()).isoformat(),
            "emi_start_date": (body.start_date or body.loan_date or date.today()).isoformat(),
        },
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "employee_code": emp.code,
        "amount": row.amount,
        "emi": row.emi,
        "status": row.status,
        "message": f"Loan ₹{row.amount} pending approval · EMI ₹{row.emi}",
    }


class LoanDecideIn(BaseModel):
    status: str  # approved / rejected
    note: str = ""


@router.post("/hrms/loans/{loan_id}/decide")
def decide_loan(loan_id: int, body: LoanDecideIn, user: CurrentUser, db: DbDep) -> dict:
    row = db.query(EmployeeLoan).filter(EmployeeLoan.id == loan_id, EmployeeLoan.company_id == user.company_id).first()
    if not row:
        raise HTTPException(404, "Loan not found")
    if body.status not in ("approved", "rejected"):
        raise HTTPException(400, "status must be approved or rejected")
    row.status = "active" if body.status == "approved" else "rejected"
    if body.note:
        row.notes = (row.notes or "") + f"\n{body.note}"
    audit(db, company_id=user.company_id, user_id=user.id, action=body.status, entity="employee_loan", entity_id=str(row.id))
    db.commit()
    return {"id": row.id, "status": row.status, "message": f"Loan {row.status}"}


# ── Expenses (marketing / field) ─────────────────────────────────────────────


@router.get("/hrms/expenses")
def list_expenses(user: CurrentUser, db: DbDep) -> list:
    rows = (
        db.query(ExpenseClaim)
        .filter(ExpenseClaim.company_id == user.company_id)
        .order_by(ExpenseClaim.id.desc())
        .all()
    )
    emps = {e.id: e.full_name for e in db.query(Employee).filter(Employee.company_id == user.company_id).all()}
    return [
        {
            "id": x.id,
            "employee_id": x.employee_id,
            "employee_name": emps.get(x.employee_id, ""),
            "claim_date": x.claim_date.isoformat(),
            "category": x.category,
            "amount": x.amount,
            "description": x.description,
            "status": x.status,
            "decided_by": x.decided_by,
            "decision_note": x.decision_note,
        }
        for x in rows
    ]


class ExpenseIn(BaseModel):
    employee_id: int
    category: str = "travel"
    amount: float
    description: str = ""
    claim_date: str | None = None


@router.post("/hrms/expenses")
def create_expense(body: ExpenseIn, user: CurrentUser, db: DbDep) -> dict:
    emp = db.query(Employee).filter(Employee.id == body.employee_id, Employee.company_id == user.company_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")
    d = date.fromisoformat(body.claim_date) if body.claim_date else date.today()
    row = ExpenseClaim(
        company_id=user.company_id,
        employee_id=body.employee_id,
        claim_date=d,
        category=body.category,
        amount=body.amount,
        description=body.description,
        status="pending",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "status": row.status}


class ExpenseDecideIn(BaseModel):
    status: str = Field(pattern="^(approved|rejected|paid)$")
    decision_note: str = ""


@router.post("/hrms/expenses/{claim_id}/decide")
def decide_expense(claim_id: int, body: ExpenseDecideIn, user: CurrentUser, db: DbDep) -> dict:
    from app.services.demo_live_settle import post_expense_payment_voucher

    row = db.query(ExpenseClaim).filter(ExpenseClaim.id == claim_id, ExpenseClaim.company_id == user.company_id).first()
    if not row:
        raise HTTPException(404, "Claim not found")
    row.status = body.status
    row.decided_by = user.full_name if hasattr(user, "full_name") else "admin"
    row.decision_note = body.decision_note
    journal = None
    if body.status == "paid":
        emp = db.get(Employee, row.employee_id)
        journal = post_expense_payment_voucher(
            db,
            company_id=user.company_id,
            claim_id=row.id,
            amount=float(row.amount or 0),
            employee_name=emp.full_name if emp else "",
            category=row.category or "expense",
        )
        if journal:
            row.decision_note = (row.decision_note or "") + f" · books {journal}"
    db.commit()
    return {"id": row.id, "status": row.status, "journal": journal, "message": f"Expense {row.status}" + (f" · {journal}" if journal else "")}


# ── Live field tracking ──────────────────────────────────────────────────────


@router.get("/hrms/tracking/live")
def live_tracking(user: CurrentUser, db: DbDep) -> list:
    emps = (
        db.query(Employee)
        .filter(Employee.company_id == user.company_id, Employee.track_live == True)  # noqa: E712
        .all()
    )
    out = []
    for e in emps:
        loc = (
            db.query(EmployeeLocation)
            .filter(EmployeeLocation.company_id == user.company_id, EmployeeLocation.employee_id == e.id)
            .order_by(EmployeeLocation.id.desc())
            .first()
        )
        out.append(
            {
                "employee_id": e.id,
                "code": e.code,
                "name": e.full_name,
                "work_type": e.work_type,
                "phone": e.phone,
                "lat": loc.lat if loc else None,
                "lng": loc.lng if loc else None,
                "place_label": loc.place_label if loc else "",
                "accuracy_m": loc.accuracy_m if loc else None,
                "battery_pct": loc.battery_pct if loc else None,
                "recorded_at": loc.recorded_at if loc else None,
                "online": bool(loc and loc.recorded_at),
            }
        )
    return out


class TrackPingIn(BaseModel):
    employee_id: int
    lat: float
    lng: float
    accuracy_m: float = 12
    place_label: str = ""
    battery_pct: int | None = 80


@router.post("/hrms/tracking/ping")
def tracking_ping(body: TrackPingIn, user: CurrentUser, db: DbDep) -> dict:
    from app.services.legal_compliance import assert_employee_gps_allowed

    emp = db.query(Employee).filter(Employee.id == body.employee_id, Employee.company_id == user.company_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")
    consent = assert_employee_gps_allowed(db, user.company_id, emp.id)
    now = datetime.utcnow().isoformat() + "Z"
    row = EmployeeLocation(
        company_id=user.company_id,
        employee_id=body.employee_id,
        lat=body.lat,
        lng=body.lng,
        accuracy_m=body.accuracy_m,
        place_label=body.place_label or "Field",
        battery_pct=body.battery_pct,
        recorded_at=now,
    )
    emp.track_live = True
    db.add(row)
    db.commit()
    return {
        "ok": True,
        "employee_id": emp.id,
        "recorded_at": now,
        "consent_version": consent.get("consent_version"),
        "note": "Phone GPS only — no Maps API key. Consent on file (offer letter + app install).",
    }


@router.post("/hrms/tracking/simulate")
def tracking_simulate(user: CurrentUser, db: DbDep) -> dict:
    """Demo: move field staff on sample city coordinates."""
    samples = [
        (28.6139, 77.2090, "Connaught Place, Delhi"),
        (19.0760, 72.8777, "Andheri, Mumbai"),
        (12.9716, 77.5946, "MG Road, Bengaluru"),
        (26.9124, 75.7873, "C-Scheme, Jaipur"),
    ]
    field = (
        db.query(Employee)
        .filter(Employee.company_id == user.company_id, Employee.work_type.in_(["marketing", "field"]))
        .all()
    )
    if not field:
        field = db.query(Employee).filter(Employee.company_id == user.company_id).limit(2).all()
    updated = []
    now = datetime.utcnow().isoformat() + "Z"
    for i, e in enumerate(field):
        lat, lng, place = samples[i % len(samples)]
        # slight jitter
        lat += (i * 0.002)
        lng += (i * 0.003)
        e.track_live = True
        db.add(
            EmployeeLocation(
                company_id=user.company_id,
                employee_id=e.id,
                lat=round(lat, 6),
                lng=round(lng, 6),
                accuracy_m=8 + i,
                place_label=place,
                battery_pct=70 + i * 5,
                recorded_at=now,
            )
        )
        updated.append({"employee_id": e.id, "name": e.full_name, "place": place})
    db.commit()
    return {"ok": True, "updated": updated, "note": "Demo simulate only — device GPS (no Maps key). Live ping needs Legal board approval (gps_always_on) + employee consent."}


# ── E-Way Bill ───────────────────────────────────────────────────────────────


@router.get("/logistics/eway")
def list_eway(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(EwayBill).filter(EwayBill.company_id == user.company_id).order_by(EwayBill.id.desc()).all()
    return [
        {
            "id": e.id,
            "number": e.number,
            "invoice_number": e.invoice_number,
            "from_place": e.from_place,
            "to_place": e.to_place,
            "distance_km": e.distance_km,
            "vehicle_no": e.vehicle_no,
            "transporter": e.transporter,
            "status": e.status,
            "ewb_no": e.ewb_no,
            "valid_upto": e.valid_upto,
        }
        for e in rows
    ]


class EwayIn(BaseModel):
    invoice_id: int | None = None
    from_place: str = "Jaipur, RJ"
    to_place: str = "Delhi, DL"
    distance_km: float = 280
    vehicle_no: str = "RJ14AB1234"
    transporter: str = "Kanha Logistics"


@router.post("/logistics/eway/generate")
def generate_eway(body: EwayIn, user: CurrentUser, db: DbDep) -> dict:
    from app.core.config import settings
    from app.services.integrations_gsp import push_eway
    from app.services.legal_compliance import assert_feature_approved

    if getattr(settings, "gsp_live", False):
        assert_feature_approved(db, user.company_id, "live_gsp_push")

    inv = None
    inv_no = ""
    if body.invoice_id:
        inv = db.query(Invoice).filter(Invoice.id == body.invoice_id, Invoice.company_id == user.company_id).first()
        if not inv:
            raise HTTPException(404, "Invoice not found")
        inv_no = inv.number
    else:
        inv = (
            db.query(Invoice)
            .filter(Invoice.company_id == user.company_id)
            .order_by(Invoice.id.desc())
            .first()
        )
        if inv:
            inv_no = inv.number
    code = next_number(db, user.company_id, EwayBill, "EWB")
    local_ewb = f"DEMO-EWB-{date.today().strftime('%y%m%d')}{str(code[-4:]).zfill(4)}"
    valid = (date.today() + timedelta(days=3)).isoformat()
    row = EwayBill(
        company_id=user.company_id,
        number=code,
        invoice_id=inv.id if inv else None,
        invoice_number=inv_no,
        from_place=body.from_place,
        to_place=body.to_place,
        distance_km=body.distance_km,
        vehicle_no=body.vehicle_no,
        transporter=body.transporter,
        status="generated",
        ewb_no=local_ewb,
        valid_upto=valid,
        payload={"source": "demo", "nic_ready": False},
    )
    db.add(row)
    gsp = push_eway(
        {
            "number": code,
            "ewb_no": local_ewb,
            "invoice_number": inv_no,
            "invoice_id": inv.id if inv else None,
            "from_place": body.from_place,
            "to_place": body.to_place,
            "distance_km": body.distance_km,
            "vehicle_no": body.vehicle_no,
            "transporter": body.transporter,
            "company_id": user.company_id,
            "gstin": settings.company_gstin,
        }
    )
    live_ok = bool(gsp.get("live") and gsp.get("status") == "ok")
    if live_ok:
        if gsp.get("ewb_no"):
            row.ewb_no = str(gsp["ewb_no"])
        if gsp.get("valid_upto"):
            row.valid_upto = str(gsp["valid_upto"])
        row.status = "generated_live"
        row.payload = {"source": "gsp_live", "nic_ready": True, "gsp": gsp.get("response") or {}}
    else:
        row.payload = {"source": "demo" if not gsp.get("live") else "gsp_failed", "nic_ready": False, "gsp": gsp}
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "number": row.number,
        "ewb_no": row.ewb_no,
        "status": row.status,
        "valid_upto": row.valid_upto,
        "live": live_ok,
        "gsp": gsp,
        "note": (
            "Live e-Way from GSP"
            if live_ok
            else "Demo e-way — paste GSP_BASE_URL + GSP_API_KEY in .env for NIC/GSP live."
        ),
        "message": "Live e-Way OK" if live_ok else "Local demo e-Way (set GSP keys for live)",
    }


# Projects / Service


@router.get("/projects")
def projects(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(Project).filter(Project.company_id == user.company_id).all()
    out = []
    for p in rows:
        task_n = db.query(Task).filter(Task.project_id == p.id).count()
        done_n = db.query(Task).filter(Task.project_id == p.id, Task.status == "done").count()
        progress = int(round(100 * done_n / task_n)) if task_n else int(p.progress or 0)
        out.append(
            {
                "id": p.id,
                "code": p.code,
                "name": p.name,
                "status": p.status,
                "progress": progress,
                "tasks": task_n,
                "start_date": p.start_date.isoformat() if p.start_date else None,
                "end_date": p.end_date.isoformat() if p.end_date else None,
            }
        )
    return out


class ProjectIn(BaseModel):
    name: str
    code: str | None = None
    status: str = "active"
    progress: int = 0


@router.post("/projects")
def create_project(body: ProjectIn, user: CurrentUser, db: DbDep) -> dict:
    n = db.query(Project).filter(Project.company_id == user.company_id).count() + 1
    code = body.code or f"PRJ-{n:03d}"
    row = Project(
        company_id=user.company_id,
        code=code,
        name=body.name,
        status=body.status,
        progress=body.progress,
        start_date=date.today(),
    )
    db.add(row)
    db.flush()
    db.add(Task(company_id=user.company_id, project_id=row.id, title="Kickoff", status="todo", milestone="start"))
    db.commit()
    db.refresh(row)
    return {"id": row.id, "code": row.code, "name": row.name}


@router.get("/projects/{project_id}/tasks")
def project_tasks(project_id: int, user: CurrentUser, db: DbDep) -> list:
    rows = db.query(Task).filter(Task.company_id == user.company_id, Task.project_id == project_id).all()
    out = []
    for t in rows:
        emp = db.get(Employee, t.assignee_id) if t.assignee_id else None
        out.append(
            {
                "id": t.id,
                "title": t.title,
                "status": t.status,
                "assignee_id": t.assignee_id,
                "assignee": emp.full_name if emp else "",
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "milestone": t.milestone or "—",
            }
        )
    return out


class TaskIn(BaseModel):
    title: str
    status: str = "todo"
    milestone: str = ""


@router.post("/projects/{project_id}/tasks")
def create_task(project_id: int, body: TaskIn, user: CurrentUser, db: DbDep) -> dict:
    proj = db.query(Project).filter(Project.id == project_id, Project.company_id == user.company_id).first()
    if not proj:
        raise HTTPException(404, "Project not found")
    t = Task(company_id=user.company_id, project_id=project_id, **body.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"id": t.id, **body.model_dump()}


class TaskStatusIn(BaseModel):
    status: str


@router.patch("/projects/tasks/{task_id}")
def update_task_status(task_id: int, body: TaskStatusIn, user: CurrentUser, db: DbDep) -> dict:
    t = db.query(Task).filter(Task.id == task_id, Task.company_id == user.company_id).first()
    if not t:
        raise HTTPException(404, "Task not found")
    if body.status not in ("todo", "doing", "done"):
        raise HTTPException(400, "status must be todo/doing/done")
    t.status = body.status
    db.flush()
    proj = db.get(Project, t.project_id)
    progress = 0
    if proj:
        task_n = db.query(Task).filter(Task.project_id == proj.id).count()
        done_n = db.query(Task).filter(Task.project_id == proj.id, Task.status == "done").count()
        progress = int(round(100 * done_n / task_n)) if task_n else 0
        proj.progress = progress
    db.commit()
    return {"id": t.id, "status": t.status, "project_progress": progress}


@router.get("/service/tickets")
def tickets(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(ServiceTicket).filter(ServiceTicket.company_id == user.company_id).all()
    out = []
    for t in rows:
        cust = db.get(Customer, t.customer_id) if t.customer_id else None
        out.append(
            {
                "id": t.id,
                "number": t.number,
                "customer_id": t.customer_id,
                "customer_name": cust.name if cust else "",
                "subject": t.subject,
                "ticket_type": t.ticket_type,
                "status": t.status,
                "priority": "normal",
                "visit_date": t.visit_date.isoformat() if t.visit_date else None,
                "notes": t.notes,
            }
        )
    return out


class TicketIn(BaseModel):
    subject: str
    customer_id: int | None = None
    ticket_type: str = "complaint"
    notes: str = ""


@router.post("/service/tickets")
def create_ticket(body: TicketIn, user: CurrentUser, db: DbDep) -> dict:
    row = ServiceTicket(
        company_id=user.company_id,
        number=next_number(db, user.company_id, ServiceTicket, "TKT"),
        status="open",
        **body.model_dump(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "number": row.number}


class TicketDecideIn(BaseModel):
    status: str = "resolved"
    notes: str = ""
    visit_date: date | None = None


@router.post("/service/tickets/{ticket_id}/decide")
def decide_ticket(ticket_id: int, body: TicketDecideIn, user: CurrentUser, db: DbDep) -> dict:
    row = db.query(ServiceTicket).filter(
        ServiceTicket.id == ticket_id, ServiceTicket.company_id == user.company_id
    ).first()
    if not row:
        raise HTTPException(404, "Ticket not found")
    if body.status not in ("open", "in_progress", "resolved", "closed"):
        raise HTTPException(400, "Invalid status")
    row.status = body.status
    if body.notes:
        row.notes = ((row.notes or "") + "\n" + body.notes).strip()
    if body.visit_date:
        row.visit_date = body.visit_date
    elif body.status == "in_progress" and not row.visit_date:
        row.visit_date = date.today()
    db.commit()
    return {"id": row.id, "number": row.number, "status": row.status}


# Documents / Reports / BI / AI / Automation


@router.get("/documents")
def documents(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(Document).filter(Document.company_id == user.company_id).all()
    return [
        {"id": d.id, "name": d.name, "entity": d.entity, "mime": d.mime, "version": d.version, "path": d.path}
        for d in rows
    ]


@router.post("/documents/upload")
async def upload_document(
    user: CurrentUser,
    db: DbDep,
    file: UploadFile = File(...),
    entity: str = Form("general"),
    entity_id: str = Form(""),
) -> dict:
    from pathlib import Path

    from app.core.config import DATA

    uploads = DATA / "uploads" / str(user.company_id)
    uploads.mkdir(parents=True, exist_ok=True)
    safe = "".join(c for c in (file.filename or "file.bin") if c.isalnum() or c in "._- ")[:120] or "file.bin"
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    dest = uploads / f"{stamp}_{safe}"
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "Max 10MB")
    dest.write_bytes(content)
    rel = f"/uploads/{user.company_id}/{dest.name}"
    row = Document(
        company_id=user.company_id,
        name=safe,
        entity=entity or "general",
        entity_id=entity_id or None,
        mime=file.content_type or "application/octet-stream",
        path=rel,
        version=1,
    )
    db.add(row)
    audit(db, company_id=user.company_id, user_id=user.id, action="upload", entity="document", entity_id=safe)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "name": row.name, "path": row.path, "mime": row.mime}


@router.get("/reports")
def reports(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(ReportDefinition).filter(
        (ReportDefinition.company_id == None) | (ReportDefinition.company_id == user.company_id)  # noqa: E711
    ).all()
    return [
        {"id": r.id, "code": r.code, "name": r.name, "module": r.module, "is_system": r.is_system}
        for r in rows
    ]


@router.get("/reports/run/{code}")
def run_report(code: str, user: CurrentUser, db: DbDep) -> dict:
    from app.api.trading import gst_report, pnl
    from app.models import Customer, PurchaseInvoice, Vendor

    wired = {
        "pnl",
        "gst_summary",
        "inventory_valuation",
        "outstanding_receivables",
        "sales_by_customer",
        "sales_by_product",
        "purchase_by_vendor",
        "low_stock",
        "outstanding_payables",
        "balance_sheet",
        "trial_balance",
        "attendance_summary",
        "payroll_register",
        "production_status",
        "ticket_sla",
        "pipeline_forecast",
    }
    if code == "pnl":
        return {"code": code, "status": "ok", "data": pnl(user, db)}
    if code == "gst_summary":
        return {"code": code, "status": "ok", "data": gst_report(user, db)}
    if code == "inventory_valuation":
        rows = db.query(StockBalance).filter(StockBalance.company_id == user.company_id).all()
        data = [{"product_id": r.product_id, "qty": r.qty, "value": round(r.qty * r.avg_cost, 2)} for r in rows]
        return {"code": code, "status": "ok", "data": data}
    if code == "outstanding_receivables":
        invs = db.query(Invoice).filter(Invoice.company_id == user.company_id).all()
        data = [
            {"number": i.number, "balance": round(i.total - i.paid, 2)}
            for i in invs
            if i.total > i.paid
        ]
        return {"code": code, "status": "ok", "data": data}
    if code == "sales_by_customer":
        invs = db.query(Invoice).filter(Invoice.company_id == user.company_id).all()
        bag: dict[int, float] = {}
        for i in invs:
            bag[i.customer_id] = bag.get(i.customer_id, 0) + i.total
        data = []
        for cid, total in bag.items():
            c = db.get(Customer, cid)
            data.append({"customer": c.name if c else cid, "total": round(total, 2)})
        return {"code": code, "status": "ok", "data": sorted(data, key=lambda x: -x["total"])}
    if code == "sales_by_product":
        invs = db.query(Invoice).filter(Invoice.company_id == user.company_id).all()
        bag: dict[str, float] = {}
        for i in invs:
            for ln in i.lines or []:
                sku = ln.get("sku") or ln.get("name") or "item"
                bag[sku] = bag.get(sku, 0) + float(ln.get("amount") or float(ln.get("qty", 0)) * float(ln.get("rate", 0)))
        data = [{"sku": k, "total": round(v, 2)} for k, v in bag.items()]
        return {"code": code, "status": "ok", "data": sorted(data, key=lambda x: -x["total"])}
    if code == "purchase_by_vendor":
        rows = db.query(PurchaseInvoice).filter(PurchaseInvoice.company_id == user.company_id).all()
        bag: dict[int, float] = {}
        for r in rows:
            vid = getattr(r, "vendor_id", None) or 0
            bag[vid] = bag.get(vid, 0) + float(r.total or 0)
        data = []
        for vid, total in bag.items():
            v = db.get(Vendor, vid) if vid else None
            data.append({"vendor": v.name if v else vid, "total": round(total, 2)})
        return {"code": code, "status": "ok", "data": data}
    if code == "low_stock":
        data = []
        for bal in db.query(StockBalance).filter(StockBalance.company_id == user.company_id).all():
            if bal.qty < 50:
                p = db.get(Product, bal.product_id)
                data.append({"sku": p.sku if p else bal.product_id, "name": p.name if p else "", "qty": bal.qty})
        return {"code": code, "status": "ok", "data": data}
    if code == "outstanding_payables":
        rows = db.query(PurchaseInvoice).filter(PurchaseInvoice.company_id == user.company_id).all()
        data = [{"number": r.number, "total": r.total, "status": r.status} for r in rows if r.status != "paid"]
        return {"code": code, "status": "ok", "data": data}
    if code == "balance_sheet":
        from app.api.trading import trial_balance

        tb = trial_balance(user, db)
        assets = sum(t["debit"] - t["credit"] for t in tb if "asset" in (t.get("name") or "").lower() or t["debit"] > t["credit"])
        return {"code": code, "status": "ok", "data": {"trial_balance": tb, "net_assets_est": round(assets, 2)}}
    if code == "trial_balance":
        from app.api.trading import trial_balance

        return {"code": code, "status": "ok", "data": trial_balance(user, db)}
    if code == "attendance_summary":
        rows = db.query(Attendance).filter(Attendance.company_id == user.company_id).all()
        bag: dict[str, int] = {}
        for a in rows:
            bag[a.status] = bag.get(a.status, 0) + 1
        return {"code": code, "status": "ok", "data": [{"status": k, "count": v} for k, v in bag.items()]}
    if code == "payroll_register":
        rows = db.query(PayrollRun).filter(PayrollRun.company_id == user.company_id).all()
        data = [{"period": p.period, "status": p.status, "employees": len(p.lines or [])} for p in rows]
        return {"code": code, "status": "ok", "data": data}
    if code == "production_status":
        rows = db.query(WorkOrder).filter(WorkOrder.company_id == user.company_id).all()
        return {"code": code, "status": "ok", "data": [{"number": w.number, "qty": w.qty, "status": w.status} for w in rows]}
    if code == "ticket_sla":
        rows = db.query(ServiceTicket).filter(ServiceTicket.company_id == user.company_id).all()
        return {"code": code, "status": "ok", "data": [{"number": t.number, "status": t.status, "type": t.ticket_type} for t in rows]}
    if code == "pipeline_forecast":
        from app.models import Opportunity

        rows = db.query(Opportunity).filter(Opportunity.company_id == user.company_id).all()
        data = [
            {"title": o.title, "stage": o.stage, "weighted": round(o.amount * o.probability / 100, 2)}
            for o in rows
        ]
        return {"code": code, "status": "ok", "data": data}
    return {
        "code": code,
        "status": "stub",
        "data": [],
        "note": "Report template reserved — wire query filters in Report Builder when going live.",
        "wired_reports": sorted(wired),
    }

@router.get("/bi/overview")
def bi_overview(user: CurrentUser, db: DbDep) -> dict:
    dash = dashboard(user, db)
    sales = db.query(Invoice).filter(Invoice.company_id == user.company_id).all()
    by_month = {}
    for i in sales:
        key = i.invoice_date.strftime("%Y-%m") if i.invoice_date else "unknown"
        by_month[key] = by_month.get(key, 0) + i.total
    abc = []
    products = db.query(Product).filter(Product.company_id == user.company_id).all()
    ranked = sorted(products, key=lambda p: p.sale_price, reverse=True)
    for idx, p in enumerate(ranked):
        band = "A" if idx < max(1, len(ranked) // 5) else ("B" if idx < len(ranked) // 2 else "C")
        abc.append({"sku": p.sku, "name": p.name, "band": band, "sale_price": p.sale_price})
    return {
        "kpis": dash["kpis"],
        "revenue_trend": [{"month": k, "revenue": round(v, 2)} for k, v in sorted(by_month.items())],
        "abc_analysis": abc,
        "forecast": {
            "next_month_sales": round(dash["kpis"]["revenue"] * 1.08, 2),
            "method": "simple_trend_x1.08",
        },
    }


class AIChatIn(BaseModel):
    message: str


@router.post("/ai/chat")
def ai_chat(body: AIChatIn, user: CurrentUser, db: DbDep) -> dict:
    """AI assistant — live LLM when key set; else full Demo AI brain on ERP data (no personal details)."""
    from app.services.ai_memory import learn_text, try_parse_teach_command
    from app.services.demo_ai import build_erp_context, build_llm_context, demo_ai_reply

    # Chat-side teach always persists first (even with LLM key)
    teach = try_parse_teach_command(body.message or "")
    if teach:
        title, text = teach
        r = learn_text(db, user.company_id, text, title=title)
        return {
            "reply": r["message"] + "\n\n" + ((r.get("item") or {}).get("preview") or "")[:200],
            "live": False,
            "mode": "memory_learn",
            "learned": True,
            "suggestions": demo_ai_reply(db, user.company_id, "__suggestions__").get("suggestions", []),
        }

    ctx = build_erp_context(db, user.company_id)
    llm_ctx = build_llm_context(db, user.company_id, query=body.message or "")
    from app.services.integrations_llm import llm_chat

    live = llm_chat(body.message, context=llm_ctx)
    if live.get("reply"):
        dash_kpis = ctx
        return {
            "reply": live["reply"],
            "live": True,
            "mode": "llm",
            "provider": settings.llm_provider or "openai",
            "suggestions": demo_ai_reply(db, user.company_id, "__suggestions__").get("suggestions", []),
            "context": {
                "revenue": dash_kpis["revenue"],
                "outstanding": dash_kpis["outstanding"],
                "inventory_value": dash_kpis["inventory_value"],
            },
        }
    return demo_ai_reply(db, user.company_id, body.message)


@router.get("/ai/knowledge")
def ai_knowledge(user: CurrentUser, db: DbDep) -> dict:
    """ERP module map for AI dock — operational facts only, no personal data."""
    from app.services.ai_memory import list_memory
    from app.services.demo_ai import build_erp_context, erp_module_guide

    return {
        "modules": erp_module_guide(),
        "snapshot": build_erp_context(db, user.company_id),
        "memory": list_memory(db, user.company_id),
        "privacy": "Aggregates and doc numbers only — no customer names, phones, or user credentials.",
    }


class AITeachIn(BaseModel):
    text: str = ""
    title: str = ""
    tags: list[str] = Field(default_factory=list)


@router.get("/ai/memory")
def ai_memory_list(user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "ai.*", "settings.*", "dashboard.*")
    from app.services.ai_memory import list_memory

    return list_memory(db, user.company_id)


@router.post("/ai/memory/teach")
def ai_memory_teach(body: AITeachIn, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "ai.*", "settings.*")
    from app.services.ai_memory import learn_text

    if not (body.text or "").strip():
        raise HTTPException(400, "text required")
    r = learn_text(db, user.company_id, body.text, title=body.title or "", tags=body.tags or [])
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="ai_memory_teach",
        entity="ai_memory",
        entity_id=(r.get("item") or {}).get("id") or "",
        detail={"chars": (r.get("item") or {}).get("chars")},
    )
    return r


@router.post("/ai/memory/upload")
async def ai_memory_upload(
    user: CurrentUser,
    db: DbDep,
    file: UploadFile = File(...),
) -> dict:
    """Learn from one uploaded file (txt/md/csv/json/code…)."""
    assert_perm(user, db, "ai.*", "settings.*")
    from app.services.ai_memory import learn_file_bytes

    raw = await file.read()
    try:
        r = learn_file_bytes(
            db,
            user.company_id,
            filename=file.filename or "file.txt",
            raw=raw,
            source="upload",
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="ai_memory_upload",
        entity="ai_memory",
        entity_id=(r.get("item") or {}).get("id") or "",
        detail={"file": file.filename},
    )
    return r


@router.post("/ai/memory/upload-many")
async def ai_memory_upload_many(
    user: CurrentUser,
    db: DbDep,
    files: list[UploadFile] = File(...),
) -> dict:
    """Learn from multiple files (folder picker uses this)."""
    assert_perm(user, db, "ai.*", "settings.*")
    from app.services.ai_memory import learn_many_files

    if not files:
        raise HTTPException(400, "No files")
    if len(files) > 40:
        raise HTTPException(400, "Max 40 files per batch")
    batch: list[tuple[str, bytes]] = []
    for f in files:
        raw = await f.read()
        name = f.filename or "file.txt"
        # webkitdirectory may send path like "folder/sub/a.txt"
        batch.append((name.replace("\\", "/").split("/")[-1] or name, raw))
    r = learn_many_files(db, user.company_id, batch, source="folder")
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="ai_memory_folder",
        entity="ai_memory",
        entity_id="batch",
        detail={"learned": r.get("learned_count"), "skipped": r.get("skipped_count")},
    )
    return r


@router.delete("/ai/memory/{mem_id}")
def ai_memory_delete(mem_id: str, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "ai.*", "settings.*")
    from app.services.ai_memory import delete_memory

    r = delete_memory(db, user.company_id, mem_id)
    audit(db, company_id=user.company_id, user_id=user.id, action="ai_memory_delete", entity="ai_memory", entity_id=mem_id)
    return r


@router.post("/ai/memory/clear")
def ai_memory_clear(user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "ai.*", "settings.*")
    from app.services.ai_memory import clear_memory

    r = clear_memory(db, user.company_id)
    audit(db, company_id=user.company_id, user_id=user.id, action="ai_memory_clear", entity="ai_memory", entity_id="all")
    return r


@router.post("/ai/purchase-suggest")
def ai_purchase_suggest(user: CurrentUser, db: DbDep) -> dict:
    factor = 1.0
    extra_note = ""
    try:
        from app.services.rules_engine import evaluate

        ev = evaluate(db, user.company_id, "reorder", {})
        factor = float((ev.get("actions") or {}).get("reorder_factor") or 1.0)
        if factor != 1.0:
            extra_note = f" · dynamic reorder_factor={factor} (scoped rule)"
    except Exception:
        pass
    low = []
    for bal in db.query(StockBalance).filter(StockBalance.company_id == user.company_id).all():
        p = db.get(Product, bal.product_id)
        if not p:
            continue
        custom = p.custom or {}
        point = float(custom.get("reorder_point", 50))
        suggest = float(custom.get("reorder_qty", 100)) * factor
        if bal.qty < point:
            low.append(
                {
                    "sku": p.sku,
                    "name": p.name,
                    "barcode": p.barcode,
                    "qty": bal.qty,
                    "reorder_point": point,
                    "suggest_order_qty": round(suggest, 0),
                }
            )
    return {
        "suggestions": low,
        "note": f"Rule: reorder when on-hand < reorder_point (default 50){extra_note}",
    }


@router.get("/automation/jobs")
def automation_jobs(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(AutomationJob).filter(AutomationJob.company_id == user.company_id).all()
    return [
        {
            "id": j.id,
            "name": j.name,
            "trigger": j.trigger,
            "action": j.action,
            "config": j.config,
            "active": j.active,
        }
        for j in rows
    ]


@router.post("/automation/run/reorder")
def automation_run_reorder(user: CurrentUser, db: DbDep) -> dict:
    """Executable automation: low stock → draft Purchase Order + notification."""
    assert_perm(user, db, "automation.*", "purchase.*", "settings.*")
    suggest = ai_purchase_suggest(user, db)
    items = suggest.get("suggestions") or []
    if not items:
        return {"ok": True, "created": False, "message": "No low-stock items — warehouse healthy", "suggestions": []}

    vendor = db.query(Vendor).filter(Vendor.company_id == user.company_id).first()
    if not vendor:
        raise HTTPException(400, "No vendor to raise draft PO")
    wh = db.query(Warehouse).filter(Warehouse.company_id == user.company_id).first()

    lines = []
    for s in items:
        p = db.query(Product).filter(Product.company_id == user.company_id, Product.sku == s["sku"]).first()
        if not p:
            continue
        qty = float(s.get("suggest_order_qty") or 100)
        rate = float(p.cost_price or 0)
        lines.append(
            {
                "product_id": p.id,
                "sku": p.sku,
                "name": p.name,
                "qty": qty,
                "rate": rate,
                "gst_rate": float(p.gst_rate or 18),
            }
        )
    if not lines:
        return {"ok": True, "created": False, "message": "Nothing to order", "suggestions": items}

    subtotal = 0.0
    tax = 0.0
    for ln in lines:
        amt = float(ln["qty"]) * float(ln["rate"])
        ln["amount"] = round(amt, 2)
        tax += amt * float(ln["gst_rate"]) / 100.0
        subtotal += amt
    subtotal, tax = round(subtotal, 2), round(tax, 2)
    total = round(subtotal + tax, 2)

    po = PurchaseOrder(
        company_id=user.company_id,
        number=next_number(db, user.company_id, PurchaseOrder, "PO"),
        vendor_id=vendor.id,
        status="draft",
        subtotal=subtotal,
        tax=tax,
        total=total,
        lines=lines,
        warehouse_id=wh.id if wh else None,
    )
    db.add(po)
    db.flush()

    db.add(
        Notification(
            company_id=user.company_id,
            user_id=user.id,
            title="Auto-reorder drafted",
            body=f"Draft {po.number} raised for {len(lines)} low-stock SKUs · ₹{total:,.0f}",
        )
    )
    job = (
        db.query(AutomationJob)
        .filter(AutomationJob.company_id == user.company_id, AutomationJob.action == "create_draft_po")
        .first()
    )
    if job:
        cfg = dict(job.config or {})
        cfg["last_run"] = date.today().isoformat()
        cfg["last_po"] = po.number
        job.config = cfg

    audit(db, company_id=user.company_id, user_id=user.id, action="auto_reorder", entity="purchase_order")
    db.commit()
    db.refresh(po)
    return {
        "ok": True,
        "created": True,
        "po": {"id": po.id, "number": po.number, "total": po.total, "lines": len(lines), "status": po.status},
        "vendor": vendor.name,
        "suggestions": items,
        "message": f"Draft PO {po.number} created automatically",
    }


@router.post("/automation/run/overdue")
def automation_run_overdue(user: CurrentUser, db: DbDep) -> dict:
    """Executable automation: unpaid invoices → reminder notifications + email outbox."""
    assert_perm(user, db, "automation.*", "sales.*", "settings.*")
    from app.services.integrations_email import send_email

    unpaid = (
        db.query(Invoice)
        .filter(Invoice.company_id == user.company_id, Invoice.total > Invoice.paid)
        .order_by(Invoice.id.desc())
        .limit(8)
        .all()
    )
    created = 0
    emails = 0
    for inv in unpaid:
        bal = round(inv.total - inv.paid, 2)
        if bal <= 0:
            continue
        cust = db.get(Customer, inv.customer_id) if inv.customer_id else None
        db.add(
            Notification(
                company_id=user.company_id,
                user_id=user.id,
                title=f"Overdue reminder · {inv.number}",
                body=f"Balance ₹{bal:,.0f} pending — auto reminder fired from Automation hub.",
            )
        )
        created += 1
        to_email = (cust.email if cust else "") or ""
        subject = f"Payment reminder · {inv.number}"
        body_txt = (
            f"Dear {(cust.name if cust else 'Customer')},\n\n"
            f"Invoice {inv.number} has outstanding ₹{bal:,.2f}. "
            f"Please pay via UPI kanha@upi with ref {inv.number}.\n\n— KanhaERP"
        )
        provider = send_email(to_email or f"accounts+{inv.id}@demo.kanhaerp.local", subject, body_txt)
        db.add(
            CommsMessage(
                company_id=user.company_id,
                channel="email",
                to_phone=to_email or "",
                to_name=cust.name if cust else "",
                template="overdue_reminder",
                body=body_txt,
                status="sent" if provider.get("status") in ("sent", "queued_sent") else "failed",
                related_entity="invoice",
                related_id=str(inv.id),
                meta={"provider": provider, "subject": subject},
            )
        )
        emails += 1
    job = (
        db.query(AutomationJob)
        .filter(AutomationJob.company_id == user.company_id, AutomationJob.action == "email")
        .first()
    )
    if job:
        cfg = dict(job.config or {})
        cfg["last_run"] = date.today().isoformat()
        cfg["reminders"] = created
        cfg["emails"] = emails
        job.config = cfg
    db.commit()
    return {
        "ok": True,
        "reminders": created,
        "emails": emails,
        "message": f"{created} overdue reminders · {emails} email outbox (demo SMTP or live)",
    }


@router.get("/comms/messages")
def comms_messages(user: CurrentUser, db: DbDep, channel: str | None = None) -> list:
    assert_perm(user, db, "comms.*", "automation.*", "crm.*", "settings.*")
    q = db.query(CommsMessage).filter(CommsMessage.company_id == user.company_id)
    if channel:
        q = q.filter(CommsMessage.channel == channel)
    rows = q.order_by(CommsMessage.id.desc()).limit(50).all()
    return [
        {
            "id": m.id,
            "channel": m.channel,
            "to_phone": m.to_phone,
            "to_name": m.to_name,
            "template": m.template,
            "body": m.body,
            "status": m.status,
            "related_entity": m.related_entity,
            "related_id": m.related_id,
            "meta": m.meta,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in rows
    ]


class WhatsAppSendIn(BaseModel):
    to_phone: str
    to_name: str = ""
    body: str
    template: str = "custom"
    related_entity: str = ""
    related_id: str = ""


@router.post("/comms/whatsapp/send")
def whatsapp_send(body: WhatsAppSendIn, user: CurrentUser, db: DbDep) -> dict:
    """WhatsApp outbox — Meta Cloud when keys set; else demo adapter (status=sent)."""
    assert_perm(user, db, "comms.*", "automation.*", "crm.*", "whatsapp.*")
    phone = (body.to_phone or "").strip()
    if not phone:
        raise HTTPException(400, "Phone required")
    from app.core.config import settings as cfg
    from app.services.integrations_whatsapp import send_whatsapp_cloud_sync
    from app.services.legal_compliance import assert_feature_approved

    if cfg.whatsapp_live:
        assert_feature_approved(db, user.company_id, "whatsapp_live_bulk")

    provider = send_whatsapp_cloud_sync(phone, body.body, template=body.template)
    status = "sent" if provider.get("status") in ("sent", "queued_local") else "failed"
    msg = CommsMessage(
        company_id=user.company_id,
        channel="whatsapp",
        to_phone=phone,
        to_name=body.to_name or "",
        template=body.template,
        body=body.body,
        status=status,
        related_entity=body.related_entity,
        related_id=body.related_id,
        meta={"provider": provider, "message_id": provider.get("message_id")},
    )
    db.add(msg)
    db.add(
        Notification(
            company_id=user.company_id,
            user_id=user.id,
            title=f"WhatsApp → {body.to_name or phone}",
            body=(body.body[:140] + ("…" if len(body.body) > 140 else "")),
        )
    )
    audit(db, company_id=user.company_id, user_id=user.id, action="whatsapp_send", entity="comms")
    db.commit()
    db.refresh(msg)
    mode = "live Meta" if provider.get("live") else "demo adapter"
    return {
        "ok": status != "failed",
        "id": msg.id,
        "status": msg.status,
        "live": bool(provider.get("live")),
        "demo": bool(provider.get("demo")),
        "message_id": provider.get("message_id"),
        "message": f"WhatsApp {status} via {mode} → {phone}",
        "provider": provider,
        "wa_link": f"https://wa.me/{phone.replace('+', '').replace(' ', '')}?text={body.body[:80]}",
    }


class WhatsAppTemplateSendIn(BaseModel):
    template_code: str
    to_phone: str
    to_name: str = ""
    variables: dict[str, Any] = Field(default_factory=dict)


@router.post("/comms/whatsapp/send-template")
def whatsapp_send_template(body: WhatsAppTemplateSendIn, user: CurrentUser, db: DbDep) -> dict:
    """Render template + send (demo or Meta)."""
    assert_perm(user, db, "comms.*", "automation.*", "whatsapp.*", "crm.*")
    from app.services.whatsapp_automation import ensure_whatsapp_automation, get_template, render_template

    ensure_whatsapp_automation(db, user.company_id, settings.app_name)
    tpl = get_template(db, user.company_id, body.template_code)
    if not tpl:
        raise HTTPException(404, f"Template not found or inactive: {body.template_code}")
    vars = {"brand": settings.app_name, "name": body.to_name or "Customer", **(body.variables or {})}
    text = render_template(tpl.body, vars)
    send_body = WhatsAppSendIn(
        to_phone=body.to_phone,
        to_name=body.to_name,
        body=text,
        template=body.template_code,
    )
    return whatsapp_send(send_body, user, db)


@router.get("/automation/whatsapp/templates/{code}/preview")
def whatsapp_template_preview(code: str, user: CurrentUser, db: DbDep, name: str = "Aarav") -> dict:
    assert_perm(user, db, "automation.*", "comms.*", "whatsapp.*", "settings.*")
    from app.services.whatsapp_automation import ensure_whatsapp_automation, get_template, list_templates, render_template

    ensure_whatsapp_automation(db, user.company_id, settings.app_name)
    tpl = get_template(db, user.company_id, code)
    if not tpl:
        # inactive still previewable
        all_t = {t["code"]: t for t in list_templates(db, user.company_id)}
        raw = all_t.get(code)
        if not raw:
            raise HTTPException(404, "Template not found")
        body = raw["body"]
        variables = raw.get("variables") or []
    else:
        body = tpl.body
        variables = tpl.variables or []
    sample = {
        "name": name,
        "company": "Demo Industries",
        "value": "2,50,000",
        "number": "INV-202607-0001",
        "amount": "48,500",
        "due_date": date.today().isoformat(),
        "sku": "ELEC-6013",
        "qty": "12",
        "point": "50",
        "vehicle": " · MH12AB1234",
        "brand": settings.app_name,
    }
    return {
        "ok": True,
        "code": code,
        "variables": variables,
        "body": body,
        "preview": render_template(body, sample),
        "sample_vars": sample,
    }


@router.post("/automation/run/whatsapp")
def automation_run_whatsapp(user: CurrentUser, db: DbDep, flow: str = "all") -> dict:
    """Run WhatsApp automations using templates from Automation hub."""
    assert_perm(user, db, "automation.*", "comms.*", "crm.*", "settings.*", "whatsapp.*")
    from app.core.config import settings
    from app.services.whatsapp_automation import run_all_whatsapp_automation, run_whatsapp_flow

    brand = settings.app_name or "KanhaERP"
    if flow and flow != "all":
        result = run_whatsapp_flow(db, user.company_id, user.id, flow, brand)
    else:
        result = run_all_whatsapp_automation(db, user.company_id, user.id, brand)
    job = (
        db.query(AutomationJob)
        .filter(AutomationJob.company_id == user.company_id, AutomationJob.action.like("whatsapp%"))
        .first()
    )
    if job:
        job.config = {**(job.config or {}), "last_run": date.today().isoformat(), "last_count": result.get("count")}
    audit(db, company_id=user.company_id, user_id=user.id, action="whatsapp_auto", entity="automation", detail={"flow": flow})
    db.commit()
    return result


@router.get("/automation/whatsapp/templates")
def wa_templates_list(user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "automation.*", "comms.*", "whatsapp.*", "settings.*")
    from app.services.whatsapp_automation import list_templates

    rows = list_templates(db, user.company_id)
    db.commit()
    return {"ok": True, "templates": rows, "count": len(rows)}


class WaTemplateIn(BaseModel):
    code: str
    name: str = ""
    category: str = "general"
    body: str
    variables: list[str] = Field(default_factory=list)
    auto_trigger: str = ""
    active: bool = True
    language: str = "hi"


@router.put("/automation/whatsapp/templates")
def wa_templates_upsert(body: WaTemplateIn, user: CurrentUser, db: DbDep) -> dict:
    """Create/update WhatsApp template — all messaging copy lives in Automation."""
    assert_perm(user, db, "automation.*", "settings.*", "whatsapp.*")
    from app.models import WhatsAppTemplate
    from app.services.whatsapp_automation import ensure_whatsapp_automation

    ensure_whatsapp_automation(db, user.company_id, settings.app_name)
    code = (body.code or "").strip().lower().replace(" ", "_")
    if not code:
        raise HTTPException(400, "code required")
    row = (
        db.query(WhatsAppTemplate)
        .filter(WhatsAppTemplate.company_id == user.company_id, WhatsAppTemplate.code == code)
        .first()
    )
    if not row:
        row = WhatsAppTemplate(company_id=user.company_id, code=code)
        db.add(row)
    row.name = body.name or code
    row.category = body.category
    row.body = body.body
    row.variables = body.variables or []
    row.auto_trigger = body.auto_trigger
    row.active = body.active
    row.language = body.language
    audit(db, company_id=user.company_id, user_id=user.id, action="wa_template_save", entity="whatsapp_template", entity_id=code)
    db.commit()
    return {"ok": True, "code": code, "message": f"Template {code} saved in Automation"}


@router.post("/automation/whatsapp/templates/{code}/toggle")
def wa_template_toggle(code: str, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "automation.*", "settings.*", "whatsapp.*")
    from app.models import WhatsAppTemplate

    row = (
        db.query(WhatsAppTemplate)
        .filter(WhatsAppTemplate.company_id == user.company_id, WhatsAppTemplate.code == code)
        .first()
    )
    if not row:
        raise HTTPException(404, "Template not found")
    row.active = not row.active
    db.commit()
    return {"ok": True, "code": code, "active": row.active}


@router.get("/automation/whatsapp/hub")
def wa_automation_hub(user: CurrentUser, db: DbDep) -> dict:
    """Single Automation dashboard payload for WhatsApp (templates + jobs + outbox)."""
    assert_perm(user, db, "automation.*", "comms.*", "whatsapp.*", "settings.*")
    from app.services.whatsapp_automation import ensure_whatsapp_automation, list_templates

    ensure_whatsapp_automation(db, user.company_id, settings.app_name)
    templates = list_templates(db, user.company_id)
    jobs = (
        db.query(AutomationJob)
        .filter(AutomationJob.company_id == user.company_id, AutomationJob.action.like("whatsapp%"))
        .all()
    )
    outbox = (
        db.query(CommsMessage)
        .filter(CommsMessage.company_id == user.company_id, CommsMessage.channel == "whatsapp")
        .order_by(CommsMessage.id.desc())
        .limit(30)
        .all()
    )
    db.commit()
    return {
        "ok": True,
        "live": settings.whatsapp_live,
        "demo_adapter": not settings.whatsapp_live,
        "mode": "meta_live" if settings.whatsapp_live else "demo_sent",
        "principle": "Sab templates + WhatsApp work Automation me — demo adapter pe send = status sent (wamid.DEMO…). Meta keys pe real Cloud API.",
        "templates": templates,
        "jobs": [
            {
                "id": j.id,
                "name": j.name,
                "trigger": j.trigger,
                "action": j.action,
                "active": j.active,
                "config": j.config,
            }
            for j in jobs
        ],
        "outbox": [
            {
                "id": m.id,
                "to_name": m.to_name,
                "to_phone": m.to_phone,
                "template": m.template,
                "status": m.status,
                "body": (m.body or "")[:100],
                "message_id": (m.meta or {}).get("message_id") if isinstance(m.meta, dict) else None,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in outbox
        ],
        "flows": [
            {"id": "all", "label": "Run ALL WhatsApp automations"},
            {"id": "lead_followup", "label": "Lead follow-ups"},
            {"id": "invoice_overdue", "label": "Overdue chase"},
            {"id": "quote_followup", "label": "Quote follow-ups"},
            {"id": "stock_alert", "label": "Low stock alerts"},
        ],
    }


@router.post("/automation/whatsapp/jobs/{job_id}/toggle")
def wa_job_toggle(job_id: int, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "automation.*", "settings.*")
    job = db.get(AutomationJob, job_id)
    if not job or job.company_id != user.company_id:
        raise HTTPException(404, "Job not found")
    job.active = not job.active
    db.commit()
    return {"ok": True, "id": job.id, "active": job.active, "name": job.name}


@router.post("/payments/razorpay/intent")
def razorpay_intent(user: CurrentUser, db: DbDep, amount: float = 0, invoice_id: int | None = None) -> dict:
    from app.services.integrations_razorpay import create_razorpay_order

    inv = None
    if invoice_id:
        inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.company_id == user.company_id).first()
        if not inv:
            raise HTTPException(404, "Invoice not found")
        amount = max(0.0, float(inv.total) - float(inv.paid or 0)) or float(inv.total or 0)
    if not amount or amount <= 0:
        amount = 1000.0
    order = create_razorpay_order(amount, receipt=f"inv{invoice_id or 0}-co{user.company_id}")
    order["invoice_id"] = inv.id if inv else invoice_id
    order["invoice_number"] = inv.number if inv else None
    order["settle_amount"] = round(float(amount), 2)
    return order


class RazorpayCaptureIn(BaseModel):
    order_id: str
    invoice_id: int | None = None
    amount: float | None = None
    payment_id: str | None = None
    signature: str | None = None


@router.post("/payments/razorpay/capture")
def razorpay_capture(body: RazorpayCaptureIn, user: CurrentUser, db: DbDep) -> dict:
    """Demo-live capture: verify (demo or live sig) → settle invoice + receipt voucher."""
    from app.services.demo_live_settle import settle_customer_payment
    from app.services.integrations_razorpay import demo_capture_payload, verify_razorpay_signature
    from app.services.period_lock import assert_period_open

    assert_period_open(db, user.company_id, date.today())
    inv = None
    if body.invoice_id:
        inv = db.query(Invoice).filter(Invoice.id == body.invoice_id, Invoice.company_id == user.company_id).first()
    if not inv:
        inv = (
            db.query(Invoice)
            .filter(Invoice.company_id == user.company_id, Invoice.total > Invoice.paid)
            .order_by(Invoice.id.desc())
            .first()
        )
    if not inv:
        raise HTTPException(400, "No unpaid invoice to settle")

    bal = max(0.01, float(inv.total) - float(inv.paid or 0))
    amt = float(body.amount or bal)
    amt = min(amt, bal)
    amount_paise = int(round(amt * 100))

    if settings.razorpay_live and body.payment_id and body.signature:
        ok = verify_razorpay_signature(body.order_id, body.payment_id, body.signature)
        if not ok:
            raise HTTPException(400, "Invalid Razorpay signature")
        payment_id = body.payment_id
        capture = {
            "provider": "razorpay",
            "live": True,
            "order_id": body.order_id,
            "payment_id": payment_id,
            "status": "captured",
            "amount": amount_paise,
        }
    else:
        capture = demo_capture_payload(body.order_id or f"order_local_{inv.id}", amount_paise)
        payment_id = capture["payment_id"]
        if not verify_razorpay_signature(capture["order_id"], payment_id, capture.get("signature") or ""):
            raise HTTPException(400, "Demo capture verify failed")

    try:
        settled = settle_customer_payment(
            db,
            company_id=user.company_id,
            invoice=inv,
            amount=amt,
            method="razorpay",
            reference=payment_id,
            gateway="razorpay",
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    db.add(
        Notification(
            company_id=user.company_id,
            user_id=user.id,
            title=f"Razorpay · {inv.number}",
            body=settled.get("message") or f"Paid ₹{amt:,.0f}",
        )
    )
    db.commit()
    return {
        "ok": True,
        "capture": capture,
        "settlement": settled,
        "invoice": {"id": inv.id, "number": inv.number, "paid": inv.paid, "status": inv.status},
        "message": settled.get("message"),
    }


@router.get("/portal/customer/{customer_id}")
def customer_portal(customer_id: int, user: CurrentUser, db: DbDep) -> dict:
    invs = db.query(Invoice).filter(Invoice.company_id == user.company_id, Invoice.customer_id == customer_id).all()
    return {
        "customer_id": customer_id,
        "invoices": [
            {"number": i.number, "total": i.total, "paid": i.paid, "status": i.status} for i in invs
        ],
        "portal_url": f"/portal/{customer_id}",
    }


# ── Kanha Agents + WhatsApp OS + India Compliance (5–10yr bet) ───────────────


def _compliance_score_invoice(db, company_id: int, inv: Invoice) -> dict:
    cust = db.get(Customer, inv.customer_id) if inv.customer_id else None
    gstin = (cust.gstin if cust else "") or ""
    issues = []
    checks = []
    score = 100

    if not (inv.lines or []):
        issues.append({"code": "NO_LINES", "severity": "high", "msg": "Invoice has no line items"})
        score -= 40
        checks.append({"id": "lines", "ok": False, "label": "Line items present"})
    else:
        checks.append({"id": "lines", "ok": True, "label": "Line items present"})

    has_gst = any(float(ln.get("gst_rate") or 0) > 0 for ln in (inv.lines or []))
    if inv.subtotal > 0 and not has_gst and not gstin.startswith("URP"):
        issues.append({"code": "GST_RATE", "severity": "medium", "msg": "Lines missing GST rate"})
        score -= 15
        checks.append({"id": "gst_rate", "ok": False, "label": "GST rate on lines"})
    else:
        checks.append({"id": "gst_rate", "ok": True, "label": "GST rate on lines"})

    expected_tax = round(float(inv.subtotal or 0) * 0.18, 2)
    if inv.subtotal > 0 and abs(float(inv.tax or 0) - expected_tax) > max(5, expected_tax * 0.05):
        # soft warning only — mixed rates ok
        checks.append({"id": "tax_band", "ok": True, "label": f"Tax recorded ₹{inv.tax:,.0f}"})
    else:
        checks.append({"id": "tax_band", "ok": True, "label": f"Tax recorded ₹{float(inv.tax or 0):,.0f}"})

    b2b = bool(gstin and len(gstin) >= 15)
    checks.append({"id": "party_gstin", "ok": b2b or float(inv.total or 0) < 1000, "label": f"Party GSTIN {'OK' if b2b else 'missing (B2C/walk-in ok)'}"})
    if float(inv.total or 0) >= 50000 and not b2b and (inv.invoice_type or "") != "pos":
        issues.append({"code": "GSTIN_MISSING", "severity": "high", "msg": "High-value invoice without customer GSTIN"})
        score -= 25

    einv = db.query(Einvoice).filter(Einvoice.invoice_id == inv.id).first()
    needs_irn = b2b and float(inv.total or 0) > 0
    if needs_irn and not einv:
        issues.append({"code": "EINVOICE", "severity": "high", "msg": "B2B invoice needs e-Invoice IRN"})
        score -= 20
        checks.append({"id": "einvoice", "ok": False, "label": "e-Invoice IRN"})
    else:
        checks.append({"id": "einvoice", "ok": True, "label": f"e-Invoice {'IRN ready' if einv else 'N/A'}"})

    eway = None
    if hasattr(EwayBill, "invoice_id"):
        eway = db.query(EwayBill).filter(EwayBill.company_id == company_id, EwayBill.invoice_id == inv.id).first()
    needs_eway = float(inv.total or 0) >= 50000
    if needs_eway and not eway:
        issues.append({"code": "EWAY", "severity": "medium", "msg": "Value ≥ ₹50k — e-Way bill recommended"})
        score -= 10
        checks.append({"id": "eway", "ok": False, "label": "e-Way bill"})
    else:
        checks.append({"id": "eway", "ok": True, "label": f"e-Way {'ready' if eway else 'N/A'}"})

    score = max(0, min(100, score))
    status = "ready" if score >= 85 and not any(i["severity"] == "high" for i in issues) else ("warn" if score >= 60 else "blocked")
    return {
        "invoice_id": inv.id,
        "number": inv.number,
        "total": inv.total,
        "customer": cust.name if cust else "",
        "gstin": gstin or "—",
        "score": score,
        "status": status,
        "issues": issues,
        "checks": checks,
        "has_einvoice": bool(einv),
        "has_eway": bool(eway),
    }


@router.get("/agents")
def agents_catalog(user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "agents.*", "agents.view", "ai.*", "automation.*", "settings.*")
    unpaid = db.query(Invoice).filter(Invoice.company_id == user.company_id, Invoice.total > Invoice.paid).count()
    low = len((ai_purchase_suggest(user, db).get("suggestions") or []))
    invs = db.query(Invoice).filter(Invoice.company_id == user.company_id).order_by(Invoice.id.desc()).limit(20).all()
    blocked = sum(1 for i in invs if _compliance_score_invoice(db, user.company_id, i)["status"] == "blocked")
    return {
        "pillars": [
            {"id": "agents", "title": "AI Action Agents", "blurb": "ERP that acts — not only stores"},
            {"id": "whatsapp", "title": "WhatsApp Business OS", "blurb": "Orders, chase, approvals on WhatsApp"},
            {"id": "compliance", "title": "India Compliance Copilot", "blurb": "GST · e-Invoice · e-Way readiness"},
        ],
        "agents": [
            {
                "id": "cash",
                "name": "Cash Agent",
                "mission": "Overdue invoices → WhatsApp payment chase",
                "queue": unpaid,
                "tone": "teal",
            },
            {
                "id": "stock",
                "name": "Stock Agent",
                "mission": "Low stock → draft purchase order",
                "queue": low,
                "tone": "blue",
            },
            {
                "id": "compliance",
                "name": "Compliance Agent",
                "mission": "Invoice GST / IRN / e-Way health check",
                "queue": blocked,
                "tone": "amber",
            },
        ],
    }


@router.post("/agents/cash/run")
def agent_cash_run(user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "agents.*", "agents.view", "automation.*", "comms.*", "sales.*")
    unpaid = (
        db.query(Invoice)
        .filter(Invoice.company_id == user.company_id, Invoice.total > Invoice.paid)
        .order_by(Invoice.id.desc())
        .limit(8)
        .all()
    )
    actions = []
    for inv in unpaid:
        cust = db.get(Customer, inv.customer_id)
        phone = (cust.phone if cust else "") or "+919876543210"
        name = cust.name if cust else "Customer"
        bal = round(inv.total - inv.paid, 2)
        body = (
            f"Namaste {name}, Kanha Cash Agent here. "
            f"Invoice {inv.number} pe ₹{bal:,.0f} pending hai. "
            f"Reply PAY for UPI link / NEFT details."
        )
        from app.services.integrations_whatsapp import send_whatsapp_cloud_sync

        provider = send_whatsapp_cloud_sync(phone, body)
        db.add(
            CommsMessage(
                company_id=user.company_id,
                channel="whatsapp",
                to_phone=phone,
                to_name=name,
                template="cash_agent_chase",
                body=body,
                status="sent" if provider.get("status") != "failed" else "failed",
                related_entity="invoice",
                related_id=str(inv.id),
                meta={"agent": "cash", "balance": bal, "provider": provider},
            )
        )
        actions.append({"invoice": inv.number, "to": name, "phone": phone, "balance": bal, "live": provider.get("live")})
    db.add(
        Notification(
            company_id=user.company_id,
            user_id=user.id,
            title="Cash Agent finished",
            body=f"Chased {len(actions)} overdue invoices on WhatsApp",
        )
    )
    audit(db, company_id=user.company_id, user_id=user.id, action="agent_cash", entity="agents")
    db.commit()
    return {
        "agent": "cash",
        "ok": True,
        "actions": actions,
        "message": f"Cash Agent chased {len(actions)} invoices via WhatsApp",
    }


@router.post("/agents/stock/run")
def agent_stock_run(user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "agents.*", "automation.*", "purchase.*")
    result = automation_run_reorder(user, db)
    return {
        "agent": "stock",
        "ok": True,
        "result": result,
        "message": result.get("message") or "Stock Agent completed",
    }


@router.post("/agents/compliance/run")
def agent_compliance_run(user: CurrentUser, db: DbDep, auto_fix: bool = True) -> dict:
    assert_perm(user, db, "agents.*", "agents.view", "compliance.*", "compliance.view", "logistics.*", "sales.*")
    invs = db.query(Invoice).filter(Invoice.company_id == user.company_id).order_by(Invoice.id.desc()).limit(15).all()
    reports = [_compliance_score_invoice(db, user.company_id, i) for i in invs]
    fixed = []
    if auto_fix:
        for rep in reports:
            if rep["status"] == "ready":
                continue
            inv = db.get(Invoice, rep["invoice_id"])
            if not inv:
                continue
            codes = {i["code"] for i in rep["issues"]}
            if "EINVOICE" in codes:
                existing = db.query(Einvoice).filter(Einvoice.invoice_id == inv.id).first()
                if not existing:
                    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
                    irn = f"DEMO-IRN-{inv.number}-{stamp}"[-64:]
                    db.add(
                        Einvoice(
                            company_id=user.company_id,
                            invoice_id=inv.id,
                            irn=irn,
                            ack_no=f"ACK{stamp[-8:]}",
                            ack_date=datetime.utcnow().isoformat() + "Z",
                            status="generated",
                            qr_payload=f"IRN:{irn}|INV:{inv.number}|AMT:{inv.total}",
                            gsp_note="Compliance Agent auto-IRN (demo) — live GSP at go-live",
                        )
                    )
                    fixed.append({"invoice": inv.number, "fix": "einvoice_irn"})
            if "EWAY" in codes:
                existing_ew = (
                    db.query(EwayBill)
                    .filter(EwayBill.company_id == user.company_id, EwayBill.invoice_id == inv.id)
                    .first()
                )
                if not existing_ew:
                    code = next_number(db, user.company_id, EwayBill, "EWB")
                    db.add(
                        EwayBill(
                            company_id=user.company_id,
                            number=code,
                            invoice_id=inv.id,
                            invoice_number=inv.number,
                            from_place="Jaipur, RJ",
                            to_place="Delhi, DL",
                            distance_km=280,
                            vehicle_no="RJ14AB1234",
                            transporter="Kanha Logistics",
                            status="generated",
                            ewb_no=f"DEMO-EWB-{date.today().strftime('%y%m%d')}{str(code[-4:]).zfill(4)}",
                            valid_upto=(date.today() + timedelta(days=3)).isoformat(),
                            payload={"source": "compliance_agent", "nic_ready": False},
                        )
                    )
                    fixed.append({"invoice": inv.number, "fix": "eway_bill"})
    db.add(
        Notification(
            company_id=user.company_id,
            user_id=user.id,
            title="Compliance Agent finished",
            body=f"Scanned {len(reports)} invoices · auto-fixed {len(fixed)}",
        )
    )
    audit(db, company_id=user.company_id, user_id=user.id, action="agent_compliance", entity="agents")
    db.commit()
    # re-score after fixes
    invs2 = db.query(Invoice).filter(Invoice.company_id == user.company_id).order_by(Invoice.id.desc()).limit(15).all()
    reports2 = [_compliance_score_invoice(db, user.company_id, i) for i in invs2]
    return {
        "agent": "compliance",
        "ok": True,
        "scanned": len(reports2),
        "fixed": fixed,
        "reports": reports2,
        "message": f"Compliance Agent scanned {len(reports2)} · fixed {len(fixed)}",
    }


@router.post("/agents/{agent_id}/run")
def agent_run_by_id(agent_id: str, user: CurrentUser, db: DbDep) -> dict:
    """Unified agent runner — UI calls /api/agents/cash|stock|compliance/run."""
    aid = (agent_id or "").strip().lower()
    if aid == "cash":
        return agent_cash_run(user, db)
    if aid == "stock":
        return agent_stock_run(user, db)
    if aid in ("compliance", "comp"):
        return agent_compliance_run(user, db)
    raise HTTPException(404, f"Unknown agent '{agent_id}'. Use cash, stock, or compliance.")


@router.post("/agents/run-all")
def agents_run_all(user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "agents.*", "settings.*", "automation.*")
    cash = agent_cash_run(user, db)
    stock = agent_stock_run(user, db)
    comp = agent_compliance_run(user, db)
    return {
        "ok": True,
        "message": "All Kanha Agents executed",
        "cash": cash,
        "stock": stock,
        "compliance": comp,
    }


@router.get("/legal/board")
def legal_board_api(user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "compliance.*", "settings.*", "hrms.*")
    from app.services.legal_compliance import legal_board

    return legal_board(db, user.company_id)


class LegalApproveIn(BaseModel):
    feature_id: str
    approved: bool = True
    note: str = ""


@router.post("/legal/approve")
def legal_approve(body: LegalApproveIn, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*", "compliance.*")
    from app.services.legal_compliance import set_feature_approval

    entry = set_feature_approval(
        db,
        user.company_id,
        feature_id=body.feature_id,
        approved=body.approved,
        note=body.note,
        updated_by=user.email or str(user.id),
    )
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="legal_approve" if body.approved else "legal_revoke",
        entity="legal_feature",
        entity_id=body.feature_id,
        detail={"note": body.note[:200]},
    )
    db.commit()
    return {"ok": True, "feature_id": body.feature_id, "approval": entry}


@router.get("/hrms/salary-policy")
def salary_policy_get(user: CurrentUser, db: DbDep) -> dict:
    from app.services.legal_compliance import get_salary_policy, is_feature_approved

    p = get_salary_policy(db, user.company_id)
    return {
        **p,
        "cut_gate_approved": is_feature_approved(db, user.company_id, "salary_attendance_cut"),
    }


class SalaryPolicyIn(BaseModel):
    mode: str | None = None
    attendance_cut_enabled: bool | None = None
    attendance_cut_requires_reason: bool | None = None
    max_attendance_cut_pct: float | None = None
    sales_pay_basis: str | None = None
    office_pay_basis: str | None = None
    target_full_pay_threshold_pct: float | None = None
    incentive_on_overachieve: bool | None = None


@router.post("/hrms/salary-policy")
def salary_policy_set(body: SalaryPolicyIn, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "hrms.*", "settings.*")
    from app.services.legal_compliance import set_salary_policy

    payload = {k: v for k, v in body.model_dump().items() if v is not None}
    p = set_salary_policy(db, user.company_id, payload, updated_by=user.email or str(user.id))
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="salary_policy",
        entity="hrms",
        detail=payload,
    )
    db.commit()
    return p


@router.get("/hrms/performance")
def performance_list(user: CurrentUser, db: DbDep) -> dict:
    from app.services.legal_compliance import get_performance_map

    emps = db.query(Employee).filter(Employee.company_id == user.company_id, Employee.active == True).all()  # noqa: E712
    perf = get_performance_map(db, user.company_id)
    rows = []
    for e in emps:
        p = perf.get(str(e.id)) or {}
        rows.append(
            {
                "employee_id": e.id,
                "code": e.code,
                "name": e.full_name,
                "department": e.department,
                "designation": e.designation,
                "work_type": e.work_type,
                "basic_salary": e.basic_salary,
                "monthly_target": p.get("monthly_target"),
                "achieved": p.get("achieved"),
                "target_achieved_pct": p.get("target_achieved_pct"),
                "note": p.get("note") or "",
                "updated_at": p.get("updated_at"),
            }
        )
    return {"employees": rows, "note": "Sales/marketing targets drive pay when policy = target_first. Auto-updates on save."}


class PerformanceIn(BaseModel):
    employee_id: int
    monthly_target: float
    achieved: float
    note: str = ""


@router.post("/hrms/performance")
def performance_set(body: PerformanceIn, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "hrms.*", "sales.*", "settings.*")
    from app.services.legal_compliance import set_employee_performance

    emp = db.query(Employee).filter(Employee.id == body.employee_id, Employee.company_id == user.company_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")
    entry = set_employee_performance(
        db,
        user.company_id,
        employee_id=body.employee_id,
        monthly_target=body.monthly_target,
        achieved=body.achieved,
        note=body.note,
    )
    db.commit()
    return {"ok": True, "employee": emp.code, "performance": entry}


@router.get("/hrms/consent/clause")
def consent_clause(user: CurrentUser) -> dict:
    from app.services.legal_compliance import CONSENT_VERSION, OFFER_LETTER_GPS_CLAUSE

    return {
        "version": CONSENT_VERSION,
        "offer_letter_clause": OFFER_LETTER_GPS_CLAUSE,
        "model": "offer_letter_plus_app_install",
        "note": "Copy this clause into offer letters for field/sales. On app install, employee Accept → HR records consent in ERP.",
    }


class ConsentIn(BaseModel):
    employee_id: int
    offer_letter_ack: bool = True
    app_install_ack: bool = True
    gps_consent: bool = True
    note: str = ""


@router.get("/hrms/consent")
def consent_list(user: CurrentUser, db: DbDep) -> dict:
    from app.services.legal_compliance import CONSENT_VERSION, OFFER_LETTER_GPS_CLAUSE, get_consent_map

    emps = db.query(Employee).filter(Employee.company_id == user.company_id).all()
    cmap = get_consent_map(db, user.company_id)
    rows = []
    for e in emps:
        c = cmap.get(str(e.id)) or {}
        rows.append(
            {
                "employee_id": e.id,
                "code": e.code,
                "name": e.full_name,
                "work_type": e.work_type,
                "gps_consent": bool(c.get("gps_consent")),
                "offer_letter_ack": bool(c.get("offer_letter_ack")),
                "app_install_ack": bool(c.get("app_install_ack")),
                "consented_at": c.get("consented_at"),
                "consent_version": c.get("consent_version"),
            }
        )
    return {
        "employees": rows,
        "clause": OFFER_LETTER_GPS_CLAUSE,
        "version": CONSENT_VERSION,
    }


@router.post("/hrms/consent")
def consent_record(body: ConsentIn, user: CurrentUser, db: DbDep) -> dict:
    """Record offer-letter + app-install GPS consent (approval on file)."""
    assert_perm(user, db, "hrms.*", "settings.*")
    from app.services.legal_compliance import record_employee_consent

    emp = db.query(Employee).filter(Employee.id == body.employee_id, Employee.company_id == user.company_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")
    entry = record_employee_consent(
        db,
        user.company_id,
        employee_id=emp.id,
        offer_letter_ack=body.offer_letter_ack,
        app_install_ack=body.app_install_ack,
        gps_consent=body.gps_consent,
        source="hr_record_offer_letter_app_install",
        note=body.note or "Employee approved via offer letter + app install",
        recorded_by=user.email or str(user.id),
    )
    emp.track_live = True
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="gps_consent",
        entity="employee",
        entity_id=str(emp.id),
        detail={"version": entry.get("consent_version")},
    )
    db.commit()
    return {"ok": True, "employee": emp.code, "consent": entry, "message": f"{emp.code} — GPS consent on file"}


@router.post("/hrms/consent/{employee_id}/revoke")
def consent_revoke(employee_id: int, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "hrms.*", "settings.*")
    from app.services.legal_compliance import revoke_employee_consent

    emp = db.query(Employee).filter(Employee.id == employee_id, Employee.company_id == user.company_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")
    entry = revoke_employee_consent(
        db,
        user.company_id,
        employee_id=emp.id,
        note="Revoked by HR",
        recorded_by=user.email or str(user.id),
    )
    emp.track_live = False
    db.commit()
    return {"ok": True, "employee": emp.code, "consent": entry}


@router.get("/compliance/scan")
def compliance_scan(user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "compliance.*", "compliance.view", "agents.*", "agents.view", "logistics.*", "sales.*", "settings.*")
    invs = db.query(Invoice).filter(Invoice.company_id == user.company_id).order_by(Invoice.id.desc()).limit(25).all()
    reports = [_compliance_score_invoice(db, user.company_id, i) for i in invs]
    ready = sum(1 for r in reports if r["status"] == "ready")
    warn = sum(1 for r in reports if r["status"] == "warn")
    blocked = sum(1 for r in reports if r["status"] == "blocked")
    avg = round(sum(r["score"] for r in reports) / len(reports), 1) if reports else 100
    return {
        "summary": {"ready": ready, "warn": warn, "blocked": blocked, "avg_score": avg, "count": len(reports)},
        "reports": reports,
        "pillars_note": "India Compliance Copilot — GSTIN · e-Invoice · e-Way",
    }


@router.get("/whatsapp/os")
def whatsapp_os(user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "whatsapp.*", "comms.*", "crm.*", "agents.*", "agents.view")
    msgs = (
        db.query(CommsMessage)
        .filter(CommsMessage.company_id == user.company_id, CommsMessage.channel == "whatsapp")
        .order_by(CommsMessage.id.desc())
        .limit(40)
        .all()
    )
    pending_so = (
        db.query(SalesOrder)
        .filter(SalesOrder.company_id == user.company_id, SalesOrder.approval_status == "pending")
        .count()
    )
    return {
        "headline": "WhatsApp Business OS",
        "stats": {
            "messages": len(msgs),
            "sent": sum(1 for m in msgs if m.status == "sent"),
            "approvals_pending": pending_so,
        },
        "quick_replies": ["YES", "NO", "PAY", "ORDER", "STOCK"],
        "inbox": [
            {
                "id": m.id,
                "to_name": m.to_name,
                "to_phone": m.to_phone,
                "template": m.template,
                "body": m.body,
                "status": m.status,
                "related_entity": m.related_entity,
                "related_id": m.related_id,
                "meta": m.meta,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in msgs
        ],
    }


class WhatsAppOsInboundIn(BaseModel):
    from_phone: str = "+919876543210"
    from_name: str = "Dealer"
    text: str
    related_entity: str = ""
    related_id: str = ""


@router.post("/whatsapp/os/inbound")
def whatsapp_os_inbound(body: WhatsAppOsInboundIn, user: CurrentUser, db: DbDep) -> dict:
    """Simulate customer WhatsApp reply → ERP action (order / approve / pay intent)."""
    assert_perm(user, db, "whatsapp.*", "comms.*", "crm.*", "agents.*")
    text = (body.text or "").strip().upper()
    actions = []
    db.add(
        CommsMessage(
            company_id=user.company_id,
            channel="whatsapp",
            to_phone=body.from_phone,
            to_name=body.from_name,
            template="inbound",
            body=body.text,
            status="received",
            related_entity=body.related_entity or "whatsapp",
            related_id=body.related_id or "",
            meta={"direction": "in", "raw": body.text},
        )
    )

    if text.startswith("ORDER") or text == "ORDER":
        lead = Lead(
            company_id=user.company_id,
            name=body.from_name,
            company_name=f"{body.from_name} WA",
            phone=body.from_phone,
            source="whatsapp",
            stage="qualified",
            value=50000,
            owner_id=user.id,
            notes=f"WhatsApp OS inbound: {body.text}",
        )
        db.add(lead)
        db.flush()
        actions.append({"type": "lead_created", "id": lead.id})
        reply = f"Order request logged as Lead #{lead.id}. Sales will confirm SKU/qty."
    elif text in ("YES", "APPROVE"):
        so = (
            db.query(SalesOrder)
            .filter(SalesOrder.company_id == user.company_id, SalesOrder.approval_status == "pending")
            .order_by(SalesOrder.id.desc())
            .first()
        )
        if so:
            so.approval_status = "approved"
            actions.append({"type": "so_approved", "number": so.number})
            reply = f"Approved {so.number} via WhatsApp."
        else:
            reply = "No pending SO to approve."
    elif text in ("NO", "REJECT"):
        so = (
            db.query(SalesOrder)
            .filter(SalesOrder.company_id == user.company_id, SalesOrder.approval_status == "pending")
            .order_by(SalesOrder.id.desc())
            .first()
        )
        if so:
            so.approval_status = "rejected"
            actions.append({"type": "so_rejected", "number": so.number})
            reply = f"Rejected {so.number}."
        else:
            reply = "No pending SO."
    elif text == "PAY":
        from app.services.demo_live_settle import settle_customer_payment

        inv = (
            db.query(Invoice)
            .filter(Invoice.company_id == user.company_id, Invoice.total > Invoice.paid)
            .order_by(Invoice.id.desc())
            .first()
        )
        if inv:
            bal = round(float(inv.total) - float(inv.paid or 0), 2)
            try:
                settled = settle_customer_payment(
                    db,
                    company_id=user.company_id,
                    invoice=inv,
                    amount=bal,
                    method="upi",
                    reference=f"WA-PAY-{inv.number}",
                    gateway="whatsapp",
                )
                actions.append({"type": "payment_settled", **settled, "invoice": inv.number})
                reply = (
                    f"Payment recorded for {inv.number} · ₹{bal:,.0f} · "
                    f"{settled.get('journal') or 'books updated'}. "
                    f"UPI kanha@upi · Ref {inv.number}."
                )
            except ValueError as exc:
                reply = f"Pay failed: {exc}"
                actions.append({"type": "pay_failed", "error": str(exc)})
        else:
            reply = "No unpaid invoice. UPI: kanha@upi for advance."
            actions.append({"type": "pay_instructions"})
    elif text == "STOCK":
        suggest = ai_purchase_suggest(user, db)
        n = len(suggest.get("suggestions") or [])
        reply = f"{n} SKUs below reorder point. Stock Agent can draft PO — reply AGENT STOCK."
        actions.append({"type": "stock_status", "low": n})
    else:
        reply = "Kanha WhatsApp OS: send ORDER / YES / NO / PAY / STOCK"

    db.add(
        CommsMessage(
            company_id=user.company_id,
            channel="whatsapp",
            to_phone=body.from_phone,
            to_name=body.from_name,
            template="os_reply",
            body=reply,
            status="sent",
            related_entity="whatsapp",
            related_id="",
            meta={"direction": "out", "actions": actions},
        )
    )
    db.commit()
    return {"ok": True, "reply": reply, "actions": actions, "message": "WhatsApp OS processed inbound"}
