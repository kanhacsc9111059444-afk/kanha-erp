"""
Fill every demo blank so UI never shows empty fields / empty modules.
Called from ensure_shell_extras — safe to re-run (only fills missing).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.deps import next_number
from app.models import (
    Attendance,
    BOM,
    Branch,
    CommsMessage,
    Customer,
    DealerOrder,
    Delivery,
    DispatchChallan,
    Document,
    Employee,
    EwayBill,
    ExpenseClaim,
    FixedAsset,
    GoodsReceipt,
    Invoice,
    Lead,
    LeaveRequest,
    Machine,
    MonitorCamera,
    MonitorChat,
    MonitorSite,
    Opportunity,
    PackingList,
    Payment,
    PayrollRun,
    Product,
    Project,
    PurchaseInvoice,
    PurchaseOrder,
    QualityInspection,
    Quotation,
    SalaryDisbursement,
    SalesOrder,
    ServiceTicket,
    StockBalance,
    StockBatch,
    StockMove,
    Task,
    User,
    Vendor,
    Warehouse,
    WorkOrder,
)


def _fill_line_names(lines: list | None, products_by_id: dict[int, Product], products_by_sku: dict[str, Product]) -> list:
    out = []
    for ln in lines or []:
        row = dict(ln)
        p = None
        if row.get("product_id"):
            p = products_by_id.get(int(row["product_id"]))
        if not p and row.get("sku"):
            p = products_by_sku.get(str(row["sku"]))
        if p:
            row.setdefault("sku", p.sku)
            row.setdefault("name", p.name)
            row.setdefault("gst_rate", p.gst_rate or 18)
            if not row.get("rate"):
                row["rate"] = p.sale_price or p.cost_price or 0
            qty = float(row.get("qty") or 1)
            rate = float(row.get("rate") or 0)
            row.setdefault("amount", round(qty * rate, 2))
        else:
            row.setdefault("name", row.get("sku") or "Item")
            row.setdefault("sku", row.get("sku") or "ITEM")
            row.setdefault("gst_rate", 18)
            row.setdefault("amount", round(float(row.get("qty") or 1) * float(row.get("rate") or 0), 2))
        out.append(row)
    return out


def fill_demo_completeness(db: Session, company_id: int) -> bool:
    """Return True if anything changed."""
    changed = False
    products = db.query(Product).filter(Product.company_id == company_id).all()
    by_id = {p.id: p for p in products}
    by_sku = {p.sku: p for p in products}
    wh = db.query(Warehouse).filter(Warehouse.company_id == company_id).first()
    admin = db.query(User).filter(User.company_id == company_id).first()
    emps = db.query(Employee).filter(Employee.company_id == company_id).all()
    emp0 = emps[0] if emps else None
    custs = db.query(Customer).filter(Customer.company_id == company_id).all()
    cust0 = next((c for c in custs if not getattr(c, "is_dealer", False)), custs[0] if custs else None)

    # ── Products: brand / category / barcodes ──
    for i, p in enumerate(products):
        if not p.brand:
            p.brand = "Kanha"
            changed = True
        if not p.category or p.category == "General":
            p.category = "Welding Consumables" if "electrode" in (p.name or "").lower() or "RAW" in (p.sku or "") else (p.category or "Finished Goods")
            changed = True
        if not p.barcode:
            p.barcode = f"8901001{str(p.id).zfill(6)}"
            changed = True
        if p.sale_price <= 0 and "RAW" not in (p.sku or ""):
            p.sale_price = 499.0 + i * 50
            changed = True
        if p.cost_price <= 0:
            p.cost_price = round((p.sale_price or 100) * 0.65, 2)
            changed = True

    # ── Leads ──
    for i, lead in enumerate(db.query(Lead).filter(Lead.company_id == company_id).all()):
        if not lead.email:
            lead.email = f"lead{lead.id}@demo.kanhaerp.com"
            changed = True
        if not lead.phone:
            lead.phone = f"98{10000000 + lead.id}"
            changed = True
        if not lead.company_name:
            lead.company_name = f"{lead.name} Industries"
            changed = True
        if not lead.notes:
            lead.notes = "Demo lead — follow-up scheduled"
            changed = True
        if not lead.source:
            lead.source = "web"
            changed = True

    # ── Customers ──
    for c in custs:
        if c.code == "WALKIN" or (c.name or "").upper() == "WALK-IN":
            if not c.phone:
                c.phone = "0000000000"
                changed = True
            if not c.billing_address:
                c.billing_address = "Counter sale — Walk-in"
                changed = True
            continue
        if not c.email:
            c.email = f"{(c.code or 'cust').lower()}@demo.kanhaerp.com"
            changed = True
        if not c.phone:
            c.phone = f"97{10000000 + c.id}"
            changed = True
        if not c.gstin:
            c.gstin = "27AABCK1234A1Z5"
            changed = True
        if not c.billing_address:
            c.billing_address = f"{getattr(c, 'region', None) or 'Mumbai'}, Maharashtra — Demo billing address"
            changed = True
        if not getattr(c, "region", None):
            c.region = "West"
            changed = True

    # ── Vendors ──
    for v in db.query(Vendor).filter(Vendor.company_id == company_id).all():
        if not v.email:
            v.email = f"{(v.code or 'ven').lower()}@supplier.demo"
            changed = True
        if not v.gstin:
            v.gstin = "27AABCS9999C1Z8"
            changed = True
        phone = getattr(v, "phone", None)
        if hasattr(v, "phone") and not phone:
            v.phone = f"96{10000000 + v.id}"
            changed = True

    # ── Opportunities ──
    for o in db.query(Opportunity).filter(Opportunity.company_id == company_id).all():
        if not o.title:
            o.title = "Demo opportunity"
            changed = True
        if not o.stage:
            o.stage = "prospect"
            changed = True
        if not o.amount:
            o.amount = 250000
            changed = True
        if not o.close_date:
            o.close_date = date.today() + timedelta(days=30)
            changed = True
        if not o.customer_id and cust0:
            o.customer_id = cust0.id
            changed = True

    # ── Document lines on quotes / SO / invoices / PO ──
    for model in (Quotation, SalesOrder, Invoice, PurchaseOrder, PurchaseInvoice):
        for row in db.query(model).filter(model.company_id == company_id).all():
            filled = _fill_line_names(row.lines, by_id, by_sku)
            if filled != (row.lines or []):
                row.lines = filled
                changed = True

    # ── BOM components ──
    for bom in db.query(BOM).filter(BOM.company_id == company_id).all():
        comps = []
        for ln in bom.components or []:
            row = dict(ln)
            p = by_id.get(int(row["product_id"])) if row.get("product_id") else None
            if not p and row.get("sku"):
                p = by_sku.get(str(row["sku"]))
            if p:
                row["product_id"] = p.id
                row["sku"] = p.sku
                row["name"] = p.name
            else:
                row.setdefault("sku", "RM-01")
                row.setdefault("name", "Raw material")
            row.setdefault("qty", 1)
            comps.append(row)
        if not comps and products:
            raw = next((p for p in products if "RAW" in (p.sku or "")), products[-1])
            comps = [{"product_id": raw.id, "sku": raw.sku, "name": raw.name, "qty": 2}]
        if comps != (bom.components or []):
            bom.components = comps
            changed = True

    # ── Employees ──
    for e in emps:
        if not e.email:
            e.email = f"{(e.code or 'emp').lower()}@kanhaerp.com"
            changed = True
        if not e.phone:
            e.phone = f"95{10000000 + e.id}"
            changed = True
        if not e.department:
            e.department = "Operations"
            changed = True
        if not e.designation:
            e.designation = "Staff"
            changed = True
        if not getattr(e, "bank_name", None):
            e.bank_name = "HDFC Bank"
            changed = True
        if not getattr(e, "bank_account", None):
            e.bank_account = f"50100{100000 + e.id}"
            changed = True
        if not getattr(e, "ifsc", None):
            e.ifsc = "HDFC0001234"
            changed = True
        if not e.basic_salary:
            e.basic_salary = 35000
            changed = True

    # ── Attendance for every employee today ──
    today = date.today()
    for e in emps:
        exists = (
            db.query(Attendance)
            .filter(Attendance.company_id == company_id, Attendance.employee_id == e.id, Attendance.day == today)
            .first()
        )
        if not exists:
            db.add(
                Attendance(
                    company_id=company_id,
                    employee_id=e.id,
                    day=today,
                    status="present",
                    check_in="09:15",
                    check_out="18:05",
                    source="demo",
                )
            )
            changed = True

    # ── Tasks: assignee + due ──
    for t in db.query(Task).filter(Task.company_id == company_id).all():
        if not t.assignee_id and emp0:
            t.assignee_id = emp0.id
            changed = True
        if not t.due_date:
            t.due_date = date.today() + timedelta(days=7)
            changed = True
        if not t.milestone:
            t.milestone = "delivery"
            changed = True

    # ── Service tickets ──
    for t in db.query(ServiceTicket).filter(ServiceTicket.company_id == company_id).all():
        if not t.customer_id and cust0:
            t.customer_id = cust0.id
            changed = True
        if not t.notes:
            t.notes = "Demo ticket — site visit scheduled with engineer"
            changed = True
        if not t.engineer_id and emp0:
            t.engineer_id = emp0.id
            changed = True
        if not t.visit_date:
            t.visit_date = date.today() + timedelta(days=2)
            changed = True

    # ── Quality ──
    for q in db.query(QualityInspection).filter(QualityInspection.company_id == company_id).all():
        if not q.ref:
            wo = db.query(WorkOrder).filter(WorkOrder.company_id == company_id).first()
            q.ref = wo.number if wo else "WO-DEMO"
            changed = True
        if not q.checklist:
            q.checklist = [
                {"item": "Visual inspection", "ok": True},
                {"item": "Dimension check", "ok": True},
                {"item": "Packaging", "ok": True},
            ]
            changed = True
        if not q.result or q.result == "pending":
            q.result = "pass"
            changed = True
        if not q.capa and q.result == "fail":
            q.capa = "Rework batch"
            changed = True

    # ── E-way / dispatch notes ──
    for e in db.query(EwayBill).filter(EwayBill.company_id == company_id).all():
        if not e.transporter:
            e.transporter = "Kanha Logistics"
            changed = True
        if not e.distance_km:
            e.distance_km = 280
            changed = True
        if not e.from_place:
            e.from_place = "Mumbai, MH"
            changed = True
        if not e.to_place:
            e.to_place = "Pune, MH"
            changed = True
        if not e.vehicle_no:
            e.vehicle_no = "MH12AB1234"
            changed = True

    for d in db.query(DispatchChallan).filter(DispatchChallan.company_id == company_id).all():
        if not d.notes:
            d.notes = "Packed & handed to transporter — demo dispatch"
            changed = True
        if not d.transporter:
            d.transporter = "Kanha Logistics"
            changed = True

    # ── Payments (from invoices with paid > 0 or create partial) ──
    if db.query(Payment).filter(Payment.company_id == company_id).count() == 0:
        for inv in db.query(Invoice).filter(Invoice.company_id == company_id).order_by(Invoice.id).limit(3):
            amt = inv.paid if inv.paid and inv.paid > 0 else round(inv.total * 0.4, 2)
            if amt <= 0:
                amt = round(min(inv.total, 5000), 2)
                inv.paid = amt
                inv.status = "posted" if amt < inv.total else "paid"
            db.add(
                Payment(
                    company_id=company_id,
                    invoice_id=inv.id,
                    party_type="customer",
                    party_id=inv.customer_id,
                    amount=amt,
                    method="bank",
                    reference=f"UTR-DEMO-{inv.id}",
                )
            )
            changed = True

    # ── Delivery for first SO ──
    if db.query(Delivery).filter(Delivery.company_id == company_id).count() == 0:
        so = db.query(SalesOrder).filter(SalesOrder.company_id == company_id).first()
        if so:
            db.add(
                Delivery(
                    company_id=company_id,
                    number="DN-202607-0001",
                    sales_order_id=so.id,
                    status="delivered",
                    lines=so.lines or [],
                )
            )
            changed = True

    # ── Stock moves ──
    if db.query(StockMove).filter(StockMove.company_id == company_id).count() == 0 and wh and products:
        for i, p in enumerate(products[:3]):
            db.add(
                StockMove(
                    company_id=company_id,
                    product_id=p.id,
                    warehouse_id=wh.id,
                    qty=50 - i * 5,
                    move_type="receipt",
                    ref="DEMO-OPENING",
                    notes="Opening stock demo",
                )
            )
        changed = True

    # ── Fixed assets ──
    if db.query(FixedAsset).filter(FixedAsset.company_id == company_id).count() == 0:
        db.add(
            FixedAsset(
                company_id=company_id,
                name="CNC Machine — Line A",
                purchase_date=date.today() - timedelta(days=400),
                cost=850000,
                depreciation_method="slm",
                useful_life_years=10,
                salvage=50000,
            )
        )
        db.add(
            FixedAsset(
                company_id=company_id,
                name="Delivery Van MH12",
                purchase_date=date.today() - timedelta(days=200),
                cost=950000,
                depreciation_method="slm",
                useful_life_years=8,
                salvage=100000,
            )
        )
        changed = True

    # ── Salary disbursement ──
    if db.query(SalaryDisbursement).filter(SalaryDisbursement.company_id == company_id).count() == 0:
        pay = db.query(PayrollRun).filter(PayrollRun.company_id == company_id).order_by(PayrollRun.id.desc()).first()
        lines = []
        total = 0.0
        for e in emps:
            net = float(e.basic_salary or 35000) * 0.92
            total += net
            lines.append(
                {
                    "employee_id": e.id,
                    "code": e.code,
                    "name": e.full_name,
                    "bank": getattr(e, "bank_name", "") or "HDFC",
                    "account": getattr(e, "bank_account", "") or "****",
                    "ifsc": getattr(e, "ifsc", "") or "HDFC0001234",
                    "amount": round(net, 2),
                    "utr": f"NEFT{e.id}DEMO",
                }
            )
        db.add(
            SalaryDisbursement(
                company_id=company_id,
                payroll_id=pay.id if pay else None,
                period=(pay.period if pay else date.today().strftime("%Y-%m")),
                status="paid",
                mode="neft",
                total_amount=round(total, 2),
                lines=lines,
                note="Demo salary batch — NEFT success",
            )
        )
        changed = True

    # ── Monitor chat ──
    if db.query(MonitorChat).filter(MonitorChat.company_id == company_id).count() == 0 and admin:
        site = db.query(MonitorSite).filter(MonitorSite.company_id == company_id).first()
        if site:
            db.add(
                MonitorChat(
                    company_id=company_id,
                    site_id=site.id,
                    user_id=admin.id,
                    body="Gate clear — demo live watch chat",
                )
            )
            db.add(
                MonitorChat(
                    company_id=company_id,
                    site_id=site.id,
                    user_id=admin.id,
                    body="Shop floor Line-A online. DVR recording local — ERP sirf stream link.",
                )
            )
            changed = True

    # ── Leave for second emp if only one leave ──
    if emp0 and len(emps) > 1:
        e2 = emps[1]
        if db.query(LeaveRequest).filter(LeaveRequest.company_id == company_id, LeaveRequest.employee_id == e2.id).count() == 0:
            db.add(
                LeaveRequest(
                    company_id=company_id,
                    employee_id=e2.id,
                    leave_type="casual",
                    from_date=date.today() + timedelta(days=5),
                    to_date=date.today() + timedelta(days=5),
                    status="pending",
                    reason="Personal work — demo",
                )
            )
            changed = True

    # ── Expense decision notes ──
    for x in db.query(ExpenseClaim).filter(ExpenseClaim.company_id == company_id).all():
        if not x.description:
            x.description = f"{x.category} claim — field demo"
            changed = True
        if x.status == "approved" and not x.decision_note:
            x.decision_note = "Approved in demo"
            changed = True

    # ── Packing customer link ──
    for pkl in db.query(PackingList).filter(PackingList.company_id == company_id).all():
        if not pkl.customer_id and cust0:
            pkl.customer_id = cust0.id
            changed = True
        if not pkl.lines:
            inv = db.get(Invoice, pkl.invoice_id) if pkl.invoice_id else None
            pkl.lines = (inv.lines if inv else []) or [{"sku": "DEMO", "name": "Demo pack", "qty": 1}]
            changed = True

    # ── Comms body always present ──
    for m in db.query(CommsMessage).filter(CommsMessage.company_id == company_id).all():
        if not m.body:
            m.body = "KanhaERP demo WhatsApp message"
            changed = True
        if not m.to_name:
            m.to_name = cust0.name if cust0 else "Customer"
            changed = True
        if not m.to_phone:
            m.to_phone = "9999999999"
            changed = True
        if not m.template:
            m.template = "general"
            changed = True

    # ── Documents entity labels in name if blank path fixed already ──
    for d in db.query(Document).filter(Document.company_id == company_id).all():
        if not d.entity:
            d.entity = "general"
            changed = True
        if not d.name:
            d.name = "Demo document"
            changed = True
        if not d.path:
            d.path = "/uploads/demo/readme.txt"
            changed = True

    # ── Project progress from tasks ──
    for proj in db.query(Project).filter(Project.company_id == company_id).all():
        task_n = db.query(Task).filter(Task.project_id == proj.id).count()
        done_n = db.query(Task).filter(Task.project_id == proj.id, Task.status == "done").count()
        if task_n and proj.progress != int(round(100 * done_n / task_n)):
            proj.progress = int(round(100 * done_n / task_n))
            changed = True
        if not proj.status:
            proj.status = "active"
            changed = True

    # ── Cameras must have stream URL ──
    for cam in db.query(MonitorCamera).filter(MonitorCamera.company_id == company_id).all():
        if not cam.stream_url:
            cam.stream_url = "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8"
            changed = True
        if not cam.location_label:
            cam.location_label = cam.name or "Cam"
            changed = True

    # ── Dealer orders: line names + notes ──
    for o in db.query(DealerOrder).filter(DealerOrder.company_id == company_id).all():
        filled = _fill_line_names(o.lines, by_id, by_sku)
        if filled != (o.lines or []):
            o.lines = filled
            changed = True
        if not o.notes:
            o.notes = "Demo dealer portal order"
            changed = True

    if ensure_demo_density(db, company_id):
        changed = True

    db.flush()
    return changed


def ensure_demo_density(db: Session, company_id: int) -> bool:
    """Guarantee every module has enough demo rows — no empty tables in UI."""
    changed = False
    products = db.query(Product).filter(Product.company_id == company_id).all()
    by_id = {p.id: p for p in products}
    whs = db.query(Warehouse).filter(Warehouse.company_id == company_id).all()
    wh0 = whs[0] if whs else None
    custs = db.query(Customer).filter(Customer.company_id == company_id).all()
    cust0 = next((c for c in custs if not getattr(c, "is_dealer", False)), custs[0] if custs else None)
    sos = db.query(SalesOrder).filter(SalesOrder.company_id == company_id).all()
    pos = db.query(PurchaseOrder).filter(PurchaseOrder.company_id == company_id).all()
    invs = db.query(Invoice).filter(Invoice.company_id == company_id).all()
    branch = db.query(Branch).filter(Branch.company_id == company_id).first()

    # Second warehouse (FG / raw split)
    if len(whs) < 2 and branch:
        db.add(
            Warehouse(
                company_id=company_id,
                branch_id=branch.id,
                code="WH-FG",
                name="Finished Goods Store",
                active=True,
            )
        )
        changed = True
        db.flush()
        whs = db.query(Warehouse).filter(Warehouse.company_id == company_id).all()
        wh0 = whs[0] if whs else None

    # Quality: incoming + process + outgoing (pending/pass/fail)
    qi_n = db.query(QualityInspection).filter(QualityInspection.company_id == company_id).count()
    if qi_n < 3:
        need = [
            ("incoming", "GRN-DEMO", "pending", "", [{"item": "Packaging", "ok": True}, {"item": "Label", "ok": False}]),
            ("process", "WO-LINE-A", "pass", "", [{"item": "Weld bead", "ok": True}, {"item": "Dimension", "ok": True}]),
            ("outgoing", "SO-SHIP", "fail", "CAPA: rework + supplier alert — demo", [{"item": "Visual", "ok": False}, {"item": "Voltage", "ok": True}]),
        ]
        existing_types = {
            q.inspection_type
            for q in db.query(QualityInspection).filter(QualityInspection.company_id == company_id).all()
        }
        for typ, ref, result, capa, checklist in need:
            if typ in existing_types and qi_n >= 3:
                continue
            if typ in existing_types:
                continue
            db.add(
                QualityInspection(
                    company_id=company_id,
                    number=next_number(db, company_id, QualityInspection, "QI"),
                    inspection_type=typ,
                    ref=ref,
                    checklist=checklist,
                    result=result,
                    capa=capa,
                )
            )
            changed = True
            qi_n += 1

    # Service tickets density
    tkt_n = db.query(ServiceTicket).filter(ServiceTicket.company_id == company_id).count()
    if tkt_n < 3 and cust0:
        specs = [
            ("complaint", "Controller not powering on", "open", date.today() + timedelta(days=1)),
            ("amc", "Quarterly AMC visit — Line A", "in_progress", date.today()),
            ("warranty", "Warranty claim — electrode feeder", "resolved", date.today() - timedelta(days=2)),
        ]
        existing_subj = {
            t.subject for t in db.query(ServiceTicket).filter(ServiceTicket.company_id == company_id).all()
        }
        for typ, subj, status, visit in specs:
            if subj in existing_subj:
                continue
            db.add(
                ServiceTicket(
                    company_id=company_id,
                    number=next_number(db, company_id, ServiceTicket, "TKT"),
                    customer_id=cust0.id,
                    subject=subj,
                    ticket_type=typ,
                    status=status,
                    visit_date=visit,
                    notes="Demo field service ticket — fully actionable from Service module",
                )
            )
            changed = True

    # Extra work order (planned) so Manufacturing not single-row
    wo_n = db.query(WorkOrder).filter(WorkOrder.company_id == company_id).count()
    bom0 = db.query(BOM).filter(BOM.company_id == company_id).first()
    if wo_n < 2 and products:
        p = products[0]
        db.add(
            WorkOrder(
                company_id=company_id,
                number=next_number(db, company_id, WorkOrder, "WO"),
                product_id=p.id,
                bom_id=bom0.id if bom0 else None,
                qty=10,
                status="planned",
                scheduled_start=date.today() + timedelta(days=2),
                scheduled_end=date.today() + timedelta(days=9),
                cost=42000,
            )
        )
        changed = True

    # Extra machine if only one
    if db.query(Machine).filter(Machine.company_id == company_id).count() < 2:
        db.add(Machine(company_id=company_id, code="WELD-02", name="MIG Welder Bay-2", status="idle"))
        changed = True

    # Stock batches for multiple products
    if wh0 and products:
        batch_n = db.query(StockBatch).filter(StockBatch.company_id == company_id).count()
        if batch_n < 3:
            for i, p in enumerate(products[:3]):
                exists = (
                    db.query(StockBatch)
                    .filter(
                        StockBatch.company_id == company_id,
                        StockBatch.product_id == p.id,
                        StockBatch.batch_no == f"BCH-DEMO-{p.sku}",
                    )
                    .first()
                )
                if exists:
                    continue
                db.add(
                    StockBatch(
                        company_id=company_id,
                        product_id=p.id,
                        warehouse_id=wh0.id,
                        batch_no=f"BCH-DEMO-{p.sku}",
                        qty=50 + i * 10,
                        mfg_date=date.today() - timedelta(days=30),
                        expiry_date=date.today() + timedelta(days=365),
                        notes="Demo batch — inventory complete",
                    )
                )
                changed = True

    # Deliveries for SOs
    if sos and db.query(Delivery).filter(Delivery.company_id == company_id).count() < 2:
        for so in sos[:2]:
            exists = (
                db.query(Delivery)
                .filter(Delivery.company_id == company_id, Delivery.sales_order_id == so.id)
                .first()
            )
            if exists:
                continue
            db.add(
                Delivery(
                    company_id=company_id,
                    number=next_number(db, company_id, Delivery, "DN"),
                    sales_order_id=so.id,
                    status="delivered",
                    lines=_fill_line_names(so.lines, by_id, {p.sku: p for p in products}),
                )
            )
            changed = True

    # GRN rows visible even if only one PO received
    if pos and db.query(GoodsReceipt).filter(GoodsReceipt.company_id == company_id).count() < 1:
        po = pos[0]
        db.add(
            GoodsReceipt(
                company_id=company_id,
                number=next_number(db, company_id, GoodsReceipt, "GRN"),
                purchase_order_id=po.id,
                status="received",
                lines=_fill_line_names(po.lines, by_id, {p.sku: p for p in products}),
            )
        )
        changed = True

    # Second packing / dispatch if thin
    if invs and db.query(PackingList).filter(PackingList.company_id == company_id).count() < 2:
        inv = invs[-1]
        db.add(
            PackingList(
                company_id=company_id,
                number=next_number(db, company_id, PackingList, "PK"),
                invoice_id=inv.id,
                customer_id=inv.customer_id,
                status="packed",
                packages=2,
                weight_kg=18.5,
                lines=_fill_line_names(inv.lines, by_id, {p.sku: p for p in products}),
            )
        )
        changed = True
    if invs and db.query(DispatchChallan).filter(DispatchChallan.company_id == company_id).count() < 2:
        inv = invs[0]
        db.add(
            DispatchChallan(
                company_id=company_id,
                number=next_number(db, company_id, DispatchChallan, "DC"),
                invoice_id=inv.id,
                customer_id=inv.customer_id,
                transporter="Kanha Logistics Demo",
                lr_number=f"LR{date.today().strftime('%y%m%d')}99",
                vehicle_no="MH12CD9876",
                dispatch_date=date.today(),
                status="dispatched",
                notes="Second demo dispatch — logistics complete",
            )
        )
        changed = True

    # Project tasks for every project (not only first)
    for proj in db.query(Project).filter(Project.company_id == company_id).all():
        tn = db.query(Task).filter(Task.project_id == proj.id).count()
        if tn >= 2:
            continue
        for title, status in [("Site survey", "done"), ("Install & commission", "doing"), ("Handover", "todo")]:
            if db.query(Task).filter(Task.project_id == proj.id, Task.title == title).first():
                continue
            db.add(
                Task(
                    company_id=company_id,
                    project_id=proj.id,
                    title=title,
                    status=status,
                    milestone="delivery",
                )
            )
            changed = True

    # Rules density (Automation)
    try:
        from app.services.rules_engine import seed_demo_rules

        if seed_demo_rules(db, company_id):
            changed = True
    except Exception:
        pass

    db.flush()
    return changed
