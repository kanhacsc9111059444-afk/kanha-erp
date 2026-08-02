from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.modules import DEFAULT_PERMISSIONS, default_modules_enabled
from app.core.security import hash_password
from app.models import (
    Account,
    Attendance,
    AutomationJob,
    BOM,
    Branch,
    Budget,
    CommsMessage,
    Company,
    CustomField,
    Customer,
    DealerOrder,
    DispatchChallan,
    Document,
    Einvoice,
    Employee,
    EmployeeLocation,
    EwayBill,
    ExpenseClaim,
    FieldTask,
    FieldVisit,
    FollowUp,
    GoodsReceipt,
    Invoice,
    JournalEntry,
    Lead,
    LeaveRequest,
    Machine,
    MaterialIndent,
    MonitorCamera,
    MonitorSite,
    MrpPlan,
    Notification,
    Opportunity,
    PackingList,
    PaymentRequest,
    PayrollRun,
    PriceList,
    Product,
    Project,
    PurchaseInvoice,
    PurchaseOrder,
    PurchaseRequisition,
    QualityInspection,
    Quotation,
    ReportDefinition,
    RfidScan,
    RfidTag,
    Role,
    SalesOrder,
    ServiceTicket,
    StockBalance,
    StockBatch,
    Task,
    User,
    Vendor,
    Warehouse,
    WorkOrder,
    Workflow,
)


REPORT_SEED = [
    ("sales_by_customer", "Sales by Customer", "sales"),
    ("sales_by_product", "Sales by Product", "sales"),
    ("purchase_by_vendor", "Purchase by Vendor", "purchase"),
    ("inventory_valuation", "Inventory Valuation", "inventory"),
    ("low_stock", "Low Stock Alert", "inventory"),
    ("outstanding_receivables", "Outstanding Receivables", "accounting"),
    ("outstanding_payables", "Outstanding Payables", "accounting"),
    ("gst_summary", "GST Summary", "accounting"),
    ("pnl", "Profit & Loss", "accounting"),
    ("balance_sheet", "Balance Sheet", "accounting"),
    ("trial_balance", "Trial Balance", "accounting"),
    ("attendance_summary", "Attendance Summary", "hrms"),
    ("payroll_register", "Payroll Register", "hrms"),
    ("production_status", "Production Status", "manufacturing"),
    ("ticket_sla", "Service Ticket SLA", "service"),
    ("pipeline_forecast", "CRM Pipeline Forecast", "crm"),
]


def seed_if_empty(db: Session) -> None:
    if db.query(Company).count():
        return

    company = Company(
        code=settings.company_code or "KANHA",
        name=settings.company_name or "Kanha Industries Pvt Ltd",
        gstin=settings.company_gstin or "27AABCK1234A1Z5",
        currency="INR",
        modules_enabled=default_modules_enabled(),
        settings_json={
            "fiscal_year_start": "04-01",
            "valuation_method": "average",
            "theme_default": "light",
            "demo_bundle": True,
            "demo_bundle_at": None,
            "industry_profile": "hybrid",
            "white_label": {
                "app_name": settings.app_name,
                "tagline": settings.brand_tagline,
                "logo_url": settings.brand_logo_url,
                "primary": settings.brand_primary,
                "accent": settings.brand_accent,
                "support_email": settings.brand_support_email,
            },
        },
    )
    db.add(company)
    db.flush()

    branch = Branch(company_id=company.id, code="HQ", name="Mumbai HQ", city="Mumbai")
    db.add(branch)
    db.flush()

    wh = Warehouse(company_id=company.id, branch_id=branch.id, code="WH-MAIN", name="Main Warehouse")
    db.add(wh)
    db.flush()

    role = Role(
        company_id=company.id,
        code="admin",
        name="Administrator",
        permissions=DEFAULT_PERMISSIONS,
    )
    db.add(role)
    db.flush()

    admin = User(
        company_id=company.id,
        branch_id=branch.id,
        email=(settings.admin_email or "admin@kanhaerp.com").lower(),
        full_name=settings.admin_full_name or "Kanha Admin",
        password_hash=hash_password(settings.admin_password or "admin123"),
        role_id=role.id,
        is_superadmin=True,
    )
    db.add(admin)
    db.flush()

    # Chart of accounts
    coa = [
        ("1000", "Assets", "asset", True),
        ("1100", "Cash", "asset", False),
        ("1200", "Bank", "asset", False),
        ("1300", "Accounts Receivable", "asset", False),
        ("1400", "Inventory", "asset", False),
        ("1450", "Work in Progress (WIP)", "asset", False),
        ("2000", "Liabilities", "liability", True),
        ("2100", "Accounts Payable", "liability", False),
        ("2200", "GST Payable", "liability", False),
        ("2210", "Input GST (ITC)", "asset", False),
        ("3000", "Equity", "equity", True),
        ("3100", "Capital", "equity", False),
        ("4000", "Income", "income", True),
        ("4100", "Sales", "income", False),
        ("5000", "Expenses", "expense", True),
        ("5100", "COGS", "expense", False),
        ("5200", "Salaries", "expense", False),
        ("5300", "Rent", "expense", False),
    ]
    for code, name, atype, is_group in coa:
        db.add(
            Account(
                company_id=company.id,
                code=code,
                name=name,
                account_type=atype,
                is_group=is_group,
            )
        )

    # Custom fields demo
    db.add(
        CustomField(
            company_id=company.id,
            entity="customer",
            field_key="industry",
            label="Industry",
            field_type="select",
            options=["Manufacturing", "Trading", "Retail", "Service"],
        )
    )
    db.add(
        CustomField(
            company_id=company.id,
            entity="lead",
            field_key="priority",
            label="Priority",
            field_type="select",
            options=["Low", "Medium", "High"],
        )
    )

    db.add(
        Workflow(
            company_id=company.id,
            name="Sales Order Approval",
            entity="sales_order",
            steps=[
                {"role": "manager", "min_amount": 100000},
                {"role": "director", "min_amount": 500000},
            ],
        )
    )

    # Products
    products = []
    catalog = [
        ("ETH-CTRL-01", "Industrial Controller X1", "Electronics", 12500, 8200, "8901001000001", 40, 80),
        ("ETH-SNS-02", "Pressure Sensor Pro", "Electronics", 3400, 2100, "8901001000002", 50, 100),
        ("MECH-BRG-10", "Bearing Assembly", "Mechanical", 890, 520, "8901001000003", 60, 120),
        ("PACK-BOX-L", "Packaging Box Large", "Packaging", 45, 22, "8901001000004", 80, 200),
        ("RAW-STL-01", "Steel Sheet Grade A", "Raw Material", 0, 78, "8901001000005", 100, 300),
    ]
    for sku, name, cat, sale, cost, barcode, reorder_point, reorder_qty in catalog:
        p = Product(
            company_id=company.id,
            sku=sku,
            name=name,
            category=cat,
            sale_price=sale,
            cost_price=cost,
            gst_rate=18,
            barcode=barcode,
            custom={"reorder_point": reorder_point, "reorder_qty": reorder_qty},
        )
        db.add(p)
        db.flush()
        products.append(p)
        # PACK-BOX intentionally low so auto-reorder demo fires
        qty = 25 if sku == "PACK-BOX-L" else (100 if sale else 500)
        db.add(
            StockBalance(
                company_id=company.id,
                warehouse_id=wh.id,
                product_id=p.id,
                qty=qty,
                avg_cost=cost,
            )
        )

    # CRM
    lead = Lead(
        company_id=company.id,
        name="Ravi Sharma",
        company_name="Aarav Traders",
        email="ravi@aarav.in",
        phone="+91-9876543210",
        source="whatsapp",
        stage="qualified",
        value=250000,
        owner_id=admin.id,
        custom={"priority": "High"},
        notes="Interested in controller + sensors package",
    )
    db.add(lead)
    db.flush()

    cust = Customer(
        company_id=company.id,
        code="CUST-001",
        name="Aarav Traders",
        email="accounts@aarav.in",
        phone="+91-9876543210",
        gstin="27AABCA9999B1Z1",
        billing_address="Andheri East, Mumbai",
        custom={"industry": "Trading"},
    )
    db.add(cust)
    db.flush()

    walkin = Customer(
        company_id=company.id,
        code="WALKIN",
        name="Walk-in / Cash Counter",
        email="pos@kanhaerp.com",
        phone="",
        gstin="",
        billing_address="Counter sale",
        custom={"channel": "pos"},
    )
    db.add(walkin)
    db.flush()

    db.add(
        Opportunity(
            company_id=company.id,
            lead_id=lead.id,
            customer_id=cust.id,
            title="Controller Package Deal",
            stage="proposal",
            amount=250000,
            probability=60,
            close_date=date.today() + timedelta(days=15),
        )
    )

    lines = [
        {
            "product_id": products[0].id,
            "sku": products[0].sku,
            "name": products[0].name,
            "qty": 10,
            "rate": products[0].sale_price,
            "gst_rate": 18,
            "amount": 10 * products[0].sale_price,
        },
        {
            "product_id": products[1].id,
            "sku": products[1].sku,
            "name": products[1].name,
            "qty": 20,
            "rate": products[1].sale_price,
            "gst_rate": 18,
            "amount": 20 * products[1].sale_price,
        },
    ]
    subtotal = sum(x["amount"] for x in lines)
    tax = round(subtotal * 0.18, 2)
    total = subtotal + tax

    quote = Quotation(
        company_id=company.id,
        number="QT-202607-0001",
        customer_id=cust.id,
        lead_id=lead.id,
        status="sent",
        subtotal=subtotal,
        tax=tax,
        total=total,
        lines=lines,
        valid_until=date.today() + timedelta(days=30),
    )
    db.add(quote)
    db.flush()

    so = SalesOrder(
        company_id=company.id,
        number="SO-202607-0001",
        customer_id=cust.id,
        quotation_id=quote.id,
        status="confirmed",
        approval_status="approved",
        subtotal=subtotal,
        tax=tax,
        total=total,
        lines=lines,
        warehouse_id=wh.id,
    )
    db.add(so)
    db.flush()

    inv = Invoice(
        company_id=company.id,
        number="INV-202607-0001",
        customer_id=cust.id,
        sales_order_id=so.id,
        status="posted",
        invoice_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        subtotal=subtotal,
        tax=tax,
        total=total,
        paid=100000,
        lines=lines,
    )
    db.add(inv)

    vendor = Vendor(
        company_id=company.id,
        code="VEN-001",
        name="Steel Hub Supplies",
        email="sales@steelhub.in",
        phone="+91-9123456780",
        gstin="27AABCS1111C1Z2",
    )
    db.add(vendor)
    db.flush()

    po_lines = [
        {
            "product_id": products[4].id,
            "sku": products[4].sku,
            "name": products[4].name,
            "qty": 200,
            "rate": 78,
            "gst_rate": 18,
            "amount": 15600,
        }
    ]
    po_sub = 15600
    po_tax = round(po_sub * 0.18, 2)
    db.add(
        PurchaseOrder(
            company_id=company.id,
            number="PO-202607-0001",
            vendor_id=vendor.id,
            status="ordered",
            subtotal=po_sub,
            tax=po_tax,
            total=po_sub + po_tax,
            lines=po_lines,
            warehouse_id=wh.id,
        )
    )

    # Manufacturing
    bom = BOM(
        company_id=company.id,
        product_id=products[0].id,
        components=[
            {"product_id": products[4].id, "qty": 2},
            {"product_id": products[2].id, "qty": 1},
        ],
    )
    db.add(bom)
    db.flush()
    db.add(
        WorkOrder(
            company_id=company.id,
            number="WO-202607-0001",
            product_id=products[0].id,
            bom_id=bom.id,
            qty=25,
            status="in_progress",
            scheduled_start=date.today(),
            scheduled_end=date.today() + timedelta(days=7),
            cost=185000,
        )
    )
    db.add(Machine(company_id=company.id, code="CNC-01", name="CNC Lathe 01", status="running"))
    db.add(
        QualityInspection(
            company_id=company.id,
            number="QI-202607-0001",
            inspection_type="outgoing",
            ref="SO-202607-0001",
            checklist=[{"item": "Visual", "ok": True}, {"item": "Voltage", "ok": True}],
            result="pass",
        )
    )

    # HR
    emp = Employee(
        company_id=company.id,
        code="EMP-001",
        full_name="Priya Nair",
        email="priya@kanhaerp.com",
        phone="9876543210",
        department="Sales",
        designation="Manager",
        join_date=date(2024, 4, 1),
        basic_salary=55000,
        bank_name="HDFC Bank",
        bank_account="50100234567890",
        ifsc="HDFC0001234",
        work_type="office",
        track_live=False,
    )
    db.add(emp)
    db.flush()
    emp_mkt = Employee(
        company_id=company.id,
        code="EMP-002",
        full_name="Rahul Mehta",
        email="rahul@kanhaerp.com",
        phone="9988776655",
        department="Marketing",
        designation="Field Executive",
        join_date=date(2025, 1, 10),
        basic_salary=32000,
        bank_name="ICICI Bank",
        bank_account="624501234567",
        ifsc="ICIC0000456",
        work_type="marketing",
        track_live=True,
    )
    db.add(emp_mkt)
    db.flush()
    db.add(
        Attendance(
            company_id=company.id,
            employee_id=emp.id,
            day=date.today(),
            status="present",
            check_in="09:05",
            check_out="18:10",
            source="biometric",
        )
    )
    db.add(
        PayrollRun(
            company_id=company.id,
            period=date.today().strftime("%Y-%m"),
            status="draft",
            lines=[
                {
                    "employee_id": emp.id,
                    "name": emp.full_name,
                    "basic": 55000,
                    "pf": 1800,
                    "esic": 412,
                    "net": 52788,
                    "bank_account": emp.bank_account,
                    "ifsc": emp.ifsc,
                    "bank_name": emp.bank_name,
                },
                {
                    "employee_id": emp_mkt.id,
                    "name": emp_mkt.full_name,
                    "basic": 32000,
                    "pf": 1800,
                    "esic": 240,
                    "net": 29960,
                    "bank_account": emp_mkt.bank_account,
                    "ifsc": emp_mkt.ifsc,
                    "bank_name": emp_mkt.bank_name,
                },
            ],
        )
    )
    db.add(
        ExpenseClaim(
            company_id=company.id,
            employee_id=emp_mkt.id,
            claim_date=date.today() - timedelta(days=1),
            category="travel",
            amount=1850,
            description="Client visit Jaipur → Delhi travel + local cab",
            status="pending",
        )
    )
    db.add(
        ExpenseClaim(
            company_id=company.id,
            employee_id=emp_mkt.id,
            claim_date=date.today() - timedelta(days=5),
            category="client",
            amount=2400,
            description="Client lunch & demo kit",
            status="approved",
            decided_by="Admin",
            decision_note="Within monthly limit",
        )
    )
    db.add(
        EmployeeLocation(
            company_id=company.id,
            employee_id=emp_mkt.id,
            lat=26.9124,
            lng=75.7873,
            accuracy_m=10,
            place_label="C-Scheme, Jaipur",
            battery_pct=78,
            recorded_at=date.today().isoformat() + "T10:30:00Z",
        )
    )

    # Projects / Service
    proj = Project(
        company_id=company.id,
        code="PRJ-ERP",
        name="KanhaERP Rollout",
        status="active",
        progress=35,
        start_date=date.today() - timedelta(days=30),
        end_date=date.today() + timedelta(days=60),
    )
    db.add(proj)
    db.flush()
    for title, st in [("Requirements freeze", "done"), ("Trading MVP", "doing"), ("GST UAT", "todo")]:
        db.add(Task(company_id=company.id, project_id=proj.id, title=title, status=st))

    db.add(
        ServiceTicket(
            company_id=company.id,
            number="TKT-202607-0001",
            customer_id=cust.id,
            subject="Installation support for Controller X1",
            ticket_type="installation",
            status="open",
            visit_date=date.today() + timedelta(days=2),
        )
    )

    for code, name, module in REPORT_SEED:
        db.add(
            ReportDefinition(
                company_id=None,
                code=code,
                name=name,
                module=module,
                query_config={"source": code},
                is_system=True,
            )
        )

    db.add(
        AutomationJob(
            company_id=company.id,
            name="Invoice overdue reminder",
            trigger="schedule",
            action="email",
            config={"cron": "0 9 * * *", "template": "invoice_reminder"},
        )
    )
    db.add(
        AutomationJob(
            company_id=company.id,
            name="Low stock → draft PO",
            trigger="inventory.low",
            action="create_draft_po",
            config={"rule": "qty < reorder_point"},
        )
    )
    db.add(
        AutomationJob(
            company_id=company.id,
            name="POS scan → stock + GST invoice",
            trigger="pos.checkout",
            action="post_invoice",
            config={"channel": "barcode"},
        )
    )
    db.add(
        AutomationJob(
            company_id=company.id,
            name="WhatsApp auto follow-up",
            trigger="schedule",
            action="whatsapp",
            config={"templates": ["lead_followup", "invoice_overdue"]},
        )
    )

    # RFID tags bound to first 3 sellable products
    for i, p in enumerate(products[:3]):
        db.add(
            RfidTag(
                company_id=company.id,
                epc=f"E2801160{1000 + i:04d}ABCD",
                product_id=p.id,
                warehouse_id=wh.id,
                location_code=f"A-0{i + 1}",
                notes="Seed RFID tag",
            )
        )
    db.add(
        Notification(
            company_id=company.id,
            user_id=admin.id,
            title="Welcome to KanhaERP",
            body="Demo company seeded. Start Live Flow: Lead → Quote → SO → Invoice.",
        )
    )
    db.add(
        Notification(
            company_id=company.id,
            user_id=admin.id,
            title="Approval pending",
            body="Large sales orders above ₹5L need approval — check Sales / Live Flow.",
        )
    )

    db.add(
        LeaveRequest(
            company_id=company.id,
            employee_id=emp.id,
            leave_type="casual",
            from_date=date.today() + timedelta(days=7),
            to_date=date.today() + timedelta(days=8),
            status="pending",
            reason="Family function",
        )
    )
    db.add(
        LeaveRequest(
            company_id=company.id,
            employee_id=emp.id,
            leave_type="sick",
            from_date=date.today() - timedelta(days=3),
            to_date=date.today() - timedelta(days=2),
            status="approved",
            reason="Fever",
        )
    )

    db.add(
        Document(
            company_id=company.id,
            name="Customer master GST certificate.pdf",
            entity="customer",
            entity_id=str(cust.id),
            mime="application/pdf",
            path="/demo/docs/gst-cert.pdf",
            version=1,
        )
    )
    db.add(
        Document(
            company_id=company.id,
            name="PO-202607-0001.pdf",
            entity="purchase_order",
            entity_id="1",
            mime="application/pdf",
            path="/demo/docs/po-sample.pdf",
            version=2,
        )
    )

    db.commit()


def _ensure_employee_columns(db: Session) -> None:
    """SQLite-safe column adds for existing DBs."""
    from sqlalchemy import text

    cols = {
        "phone": "VARCHAR(32)",
        "bank_name": "VARCHAR(120) DEFAULT ''",
        "bank_account": "VARCHAR(64) DEFAULT ''",
        "ifsc": "VARCHAR(20) DEFAULT ''",
        "work_type": "VARCHAR(32) DEFAULT 'office'",
        "track_live": "BOOLEAN DEFAULT 0",
    }
    existing = {r[1] for r in db.execute(text("PRAGMA table_info(employees)")).fetchall()}
    for name, typ in cols.items():
        if name not in existing:
            try:
                db.execute(text(f"ALTER TABLE employees ADD COLUMN {name} {typ}"))
            except Exception:
                pass
    db.commit()


def _ensure_user_prefs(db: Session) -> None:
    from sqlalchemy import text

    existing = {r[1] for r in db.execute(text("PRAGMA table_info(users)")).fetchall()}
    if "ui_prefs" not in existing:
        try:
            db.execute(text("ALTER TABLE users ADD COLUMN ui_prefs JSON DEFAULT '{}'"))
            db.commit()
        except Exception:
            pass
    if "session_epoch" not in existing:
        try:
            db.execute(text("ALTER TABLE users ADD COLUMN session_epoch INTEGER DEFAULT 0"))
            db.commit()
        except Exception:
            pass


def _ensure_customer_columns(db: Session) -> None:
    from sqlalchemy import text

    cols = {
        "party_type": "VARCHAR(32) DEFAULT 'customer'",
        "is_dealer": "BOOLEAN DEFAULT 0",
        "credit_limit": "FLOAT DEFAULT 0",
        "price_list_code": "VARCHAR(64) DEFAULT 'STANDARD'",
        "region": "VARCHAR(100) DEFAULT ''",
    }
    try:
        existing = {r[1] for r in db.execute(text("PRAGMA table_info(customers)")).fetchall()}
    except Exception:
        return
    for name, typ in cols.items():
        if name not in existing:
            try:
                db.execute(text(f"ALTER TABLE customers ADD COLUMN {name} {typ}"))
            except Exception:
                pass
    db.commit()


def ensure_shell_extras(db: Session) -> None:
    """Fill thin demo tables on existing DBs so shell screens are never empty."""
    try:
        _ensure_employee_columns(db)
        _ensure_user_prefs(db)
        _ensure_customer_columns(db)
    except Exception:
        pass

    company = db.query(Company).first()
    if not company:
        return
    admin = db.query(User).filter(User.company_id == company.id).first()
    emp = db.query(Employee).filter(Employee.company_id == company.id).first()
    cust = db.query(Customer).filter(Customer.company_id == company.id).first()
    changed = False
    sj0 = dict(company.settings_json or {})
    # After purge OR production: never re-seed demo transactional density
    skip_demo_seed = bool(sj0.get("demo_purged_at")) or (not settings.demo_mode)

    # Ensure Input GST (ITC) + WIP ledgers exist on older DBs
    for code, name, atype in (
        ("2210", "Input GST (ITC)", "asset"),
        ("1450", "Work in Progress (WIP)", "asset"),
    ):
        if not db.query(Account).filter(Account.company_id == company.id, Account.code == code).first():
            db.add(Account(company_id=company.id, code=code, name=name, account_type=atype, is_group=False))
            changed = True

    # Enable new modules on existing companies (no alias keys like tally)
    from app.core.modules import canonicalize_modules_enabled

    mods = dict(company.modules_enabled or default_modules_enabled())
    for key in ("dealers", "logistics", "pos", "rfid", "agents", "whatsapp", "compliance", "approvals", "ha", "watch", "ops-board", "visit", "tasks", "followup", "payments-ops", "indents", "mis", "rfq", "books", "bridges"):
        if key not in mods:
            mods[key] = True
            changed = True
    # Retire duplicate "Kanha Books" alias module
    if mods.pop("tally", None) is not None:
        mods["books"] = True
        changed = True
    cleaned = canonicalize_modules_enabled(mods)
    if cleaned != mods:
        mods = cleaned
        changed = True
    if changed:
        company.modules_enabled = mods

    # Keep admin role permissions current
    admin_role = db.query(Role).filter(Role.company_id == company.id, Role.code == "admin").first()
    if admin_role:
        perms = list(admin_role.permissions or [])
        # Drop retired tally.* — books.* covers Kanha Books
        if "tally.*" in perms:
            perms = [p for p in perms if p != "tally.*"]
            if "books.*" not in perms and "*" not in perms:
                perms.append("books.*")
            changed = True
        for p in ("pos.*", "rfid.*", "comms.*", "automation.*", "agents.*", "whatsapp.*", "compliance.*", "approvals.*", "ha.*", "watch.*", "ops-board.*", "visit.*", "tasks.*", "followup.*", "payments-ops.*", "indents.*", "mis.*", "rfq.*", "books.*", "bridges.*"):
            if p not in perms and "*" not in perms:
                perms.append(p)
                changed = True
        if len(perms) < len(DEFAULT_PERMISSIONS) - 2:
            admin_role.permissions = DEFAULT_PERMISSIONS
            changed = True
        else:
            admin_role.permissions = perms
            changed = True

    sales_role = db.query(Role).filter(Role.company_id == company.id, Role.code == "sales").first()
    if sales_role:
        sperms = list(sales_role.permissions or [])
        for p in ("pos.*", "rfid.view", "comms.*", "crm.*"):
            if p not in sperms:
                sperms.append(p)
                changed = True
        sales_role.permissions = sperms

    # RFID tags on existing DBs
    if db.query(RfidTag).filter(RfidTag.company_id == company.id).count() == 0:
        wh0 = db.query(Warehouse).filter(Warehouse.company_id == company.id).first()
        prods = (
            db.query(Product)
            .filter(Product.company_id == company.id, Product.sale_price > 0)
            .limit(3)
            .all()
        )
        for i, p in enumerate(prods):
            db.add(
                RfidTag(
                    company_id=company.id,
                    epc=f"E2801160{1000 + i:04d}ABCD",
                    product_id=p.id,
                    warehouse_id=wh0.id if wh0 else None,
                    location_code=f"A-0{i + 1}",
                    notes="Seed RFID tag",
                )
            )
            changed = True

    if "WhatsApp auto follow-up" not in {j.name for j in db.query(AutomationJob).filter(AutomationJob.company_id == company.id).all()}:
        db.add(
            AutomationJob(
                company_id=company.id,
                name="WhatsApp auto follow-up",
                trigger="schedule",
                action="whatsapp",
                config={"templates": ["lead_followup", "invoice_overdue"]},
            )
        )
        changed = True

    # Upgrade product barcodes + reorder rules for Scan Billing demo
    barcode_map = {
        "ETH-CTRL-01": ("8901001000001", 40, 80),
        "ETH-SNS-02": ("8901001000002", 50, 100),
        "MECH-BRG-10": ("8901001000003", 60, 120),
        "PACK-BOX-L": ("8901001000004", 80, 200),
        "RAW-STL-01": ("8901001000005", 100, 300),
    }
    for p in db.query(Product).filter(Product.company_id == company.id).all():
        tip = barcode_map.get(p.sku)
        if not tip:
            continue
        code, rp, rq = tip
        if p.barcode != code or not (p.custom or {}).get("reorder_point"):
            p.barcode = code
            p.custom = {**(p.custom or {}), "reorder_point": rp, "reorder_qty": rq}
            changed = True
        if p.sku == "PACK-BOX-L":
            bal = (
                db.query(StockBalance)
                .filter(StockBalance.company_id == company.id, StockBalance.product_id == p.id)
                .first()
            )
            if bal and bal.qty >= 80:
                bal.qty = 25
                changed = True

    walk = db.query(Customer).filter(Customer.company_id == company.id, Customer.code == "WALKIN").first()
    if not walk:
        db.add(
            Customer(
                company_id=company.id,
                code="WALKIN",
                name="Walk-in / Cash Counter",
                email="pos@kanhaerp.com",
                billing_address="Counter sale",
                custom={"channel": "pos"},
            )
        )
        changed = True

    job_names = {j.name for j in db.query(AutomationJob).filter(AutomationJob.company_id == company.id).all()}
    if "Low stock → draft PO" not in job_names:
        db.add(
            AutomationJob(
                company_id=company.id,
                name="Low stock → draft PO",
                trigger="inventory.low",
                action="create_draft_po",
                config={"rule": "qty < reorder_point"},
            )
        )
        changed = True
    if "POS scan → stock + GST invoice" not in job_names:
        db.add(
            AutomationJob(
                company_id=company.id,
                name="POS scan → stock + GST invoice",
                trigger="pos.checkout",
                action="post_invoice",
                config={"channel": "barcode"},
            )
        )
        changed = True

    try:
        from app.services.whatsapp_automation import ensure_whatsapp_automation

        wa = ensure_whatsapp_automation(db, company.id)
        if wa.get("templates") or wa.get("jobs"):
            changed = True
    except Exception:
        pass

    try:
        from app.services.rules_engine import seed_demo_rules

        if seed_demo_rules(db, company.id):
            changed = True
    except Exception:
        pass

    if db.query(Document).filter(Document.company_id == company.id).count() == 0 and cust:
        db.add(
            Document(
                company_id=company.id,
                name="Customer master GST certificate.pdf",
                entity="customer",
                entity_id=str(cust.id),
                mime="application/pdf",
                path="/demo/docs/gst-cert.pdf",
                version=1,
            )
        )
        db.add(
            Document(
                company_id=company.id,
                name="Sample quotation.pdf",
                entity="quotation",
                entity_id="1",
                mime="application/pdf",
                path="/demo/docs/quote-sample.pdf",
                version=1,
            )
        )
        changed = True

    if emp and db.query(LeaveRequest).filter(LeaveRequest.company_id == company.id).count() == 0:
        db.add(
            LeaveRequest(
                company_id=company.id,
                employee_id=emp.id,
                leave_type="casual",
                from_date=date.today() + timedelta(days=7),
                to_date=date.today() + timedelta(days=8),
                status="pending",
                reason="Family function",
            )
        )
        changed = True

    if admin and db.query(Notification).filter(Notification.company_id == company.id).count() < 2:
        db.add(
            Notification(
                company_id=company.id,
                user_id=admin.id,
                title="Shell ready",
                body="Notifications, Documents, Leaves hooks are live for demo walkthrough.",
            )
        )
        changed = True

    # Bank details on first emp if empty
    if emp and not (getattr(emp, "bank_account", None) or ""):
        emp.bank_name = "HDFC Bank"
        emp.bank_account = "50100234567890"
        emp.ifsc = "HDFC0001234"
        changed = True

    # Marketing field executive
    mkt = (
        db.query(Employee)
        .filter(Employee.company_id == company.id, Employee.work_type == "marketing")
        .first()
    )
    if not mkt:
        mkt = Employee(
            company_id=company.id,
            code="EMP-002",
            full_name="Rahul Mehta",
            email="rahul@kanhaerp.com",
            phone="9988776655",
            department="Marketing",
            designation="Field Executive",
            join_date=date(2025, 1, 10),
            basic_salary=32000,
            bank_name="ICICI Bank",
            bank_account="624501234567",
            ifsc="ICIC0000456",
            work_type="marketing",
            track_live=True,
        )
        db.add(mkt)
        db.flush()
        changed = True

    if mkt and db.query(ExpenseClaim).filter(ExpenseClaim.company_id == company.id).count() == 0:
        db.add(
            ExpenseClaim(
                company_id=company.id,
                employee_id=mkt.id,
                claim_date=date.today() - timedelta(days=1),
                category="travel",
                amount=1850,
                description="Client visit travel + local cab",
                status="pending",
            )
        )
        db.add(
            ExpenseClaim(
                company_id=company.id,
                employee_id=mkt.id,
                claim_date=date.today() - timedelta(days=5),
                category="client",
                amount=2400,
                description="Client lunch & demo kit",
                status="approved",
                decided_by="Admin",
            )
        )
        changed = True

    if mkt and db.query(EmployeeLocation).filter(EmployeeLocation.company_id == company.id).count() == 0:
        db.add(
            EmployeeLocation(
                company_id=company.id,
                employee_id=mkt.id,
                lat=26.9124,
                lng=75.7873,
                accuracy_m=10,
                place_label="C-Scheme, Jaipur",
                battery_pct=78,
                recorded_at=date.today().isoformat() + "T10:30:00Z",
            )
        )
        mkt.track_live = True
        changed = True

    # ── Channel / logistics / MRP extras ──
    products = db.query(Product).filter(Product.company_id == company.id).all()
    wh = db.query(Warehouse).filter(Warehouse.company_id == company.id).first()

    if db.query(PriceList).filter(PriceList.company_id == company.id).count() == 0 and products:
        lines = [
            {"sku": p.sku, "product_id": p.id, "price": round(p.sale_price * 0.88, 2), "discount_pct": 12}
            for p in products[:5]
        ]
        db.add(PriceList(company_id=company.id, code="DEALER", name="Dealer slab", party_type="dealer", lines=lines))
        db.add(
            PriceList(
                company_id=company.id,
                code="DISTRIBUTOR",
                name="Distributor slab",
                party_type="distributor",
                lines=[
                    {"sku": p.sku, "product_id": p.id, "price": round(p.sale_price * 0.82, 2), "discount_pct": 18}
                    for p in products[:5]
                ],
            )
        )
        changed = True

    dealer = (
        db.query(Customer)
        .filter(Customer.company_id == company.id, Customer.is_dealer == True)  # noqa: E712
        .first()
    )
    if not dealer:
        dealer = Customer(
            company_id=company.id,
            code="DLR-001",
            name="Maxidura Dealer — Raipur",
            phone="9876501234",
            email="dealer@demo.kanhaerp.com",
            gstin="22AAAAA0000A1Z5",
            billing_address="Industrial Area, Raipur",
            party_type="dealer",
            is_dealer=True,
            credit_limit=1500000,
            price_list_code="DEALER",
            region="Chhattisgarh",
        )
        db.add(dealer)
        db.flush()
        changed = True
    elif not getattr(dealer, "credit_limit", None):
        dealer.is_dealer = True
        dealer.party_type = "dealer"
        dealer.credit_limit = 1500000
        dealer.price_list_code = "DEALER"
        dealer.region = dealer.region or "North"
        changed = True

    if dealer and db.query(DealerOrder).filter(DealerOrder.company_id == company.id).count() == 0 and products:
        p0 = products[0]
        db.add(
            DealerOrder(
                company_id=company.id,
                number="DO-202607-0001",
                dealer_id=dealer.id,
                status="submitted",
                lines=[{"sku": p0.sku, "product_id": p0.id, "qty": 20, "rate": round(p0.sale_price * 0.88, 2), "amount": round(20 * p0.sale_price * 0.88, 2)}],
                total=round(20 * p0.sale_price * 0.88, 2),
                notes="Urgent stock for cement plant clients",
            )
        )
        changed = True

    if wh and products and db.query(StockBatch).filter(StockBatch.company_id == company.id).count() == 0:
        p0 = products[0]
        p0.track_batch = True
        db.add(
            StockBatch(
                company_id=company.id,
                product_id=p0.id,
                warehouse_id=wh.id,
                batch_no="BCH-2607-A1",
                qty=120,
                mfg_date=date.today() - timedelta(days=30),
                expiry_date=date.today() + timedelta(days=335),
                notes="Demo lot",
            )
        )
        changed = True

    inv = db.query(Invoice).filter(Invoice.company_id == company.id).order_by(Invoice.id.desc()).first()
    if inv and db.query(PackingList).filter(PackingList.company_id == company.id).count() == 0:
        pkl = PackingList(
            company_id=company.id,
            number="PKL-202607-0001",
            invoice_id=inv.id,
            customer_id=inv.customer_id,
            status="packed",
            packages=4,
            weight_kg=52,
            lines=inv.lines or [],
        )
        db.add(pkl)
        db.flush()
        db.add(
            DispatchChallan(
                company_id=company.id,
                number="DC-202607-0001",
                packing_list_id=pkl.id,
                invoice_id=inv.id,
                customer_id=inv.customer_id,
                transporter="Kanha Logistics",
                lr_number="LR26072701",
                vehicle_no="RJ14AB4321",
                dispatch_date=date.today(),
                status="dispatched",
            )
        )
        changed = True

    if inv and db.query(Einvoice).filter(Einvoice.company_id == company.id).count() == 0:
        db.add(
            Einvoice(
                company_id=company.id,
                invoice_id=inv.id,
                irn=f"DEMO-IRN-{inv.number}",
                ack_no="ACK26072701",
                ack_date=date.today().isoformat(),
                status="generated",
                qr_payload=f"IRN:DEMO|{inv.number}",
            )
        )
        changed = True

    if db.query(MrpPlan).filter(MrpPlan.company_id == company.id).count() == 0 and products:
        db.add(
            MrpPlan(
                company_id=company.id,
                number="MRP-202607-0001",
                period=date.today().strftime("%Y-%m"),
                status="planned",
                lines=[
                    {
                        "sku": products[0].sku,
                        "name": products[0].name,
                        "on_hand": 40,
                        "demand": 100,
                        "shortage": 60,
                        "suggest": "work_order",
                        "suggest_qty": 60,
                    }
                ],
                notes="Seed MRP plan",
            )
        )
        changed = True

    sales_role = db.query(Role).filter(Role.company_id == company.id, Role.code == "sales").first()
    if not sales_role:
        sales_role = Role(
            company_id=company.id,
            code="sales",
            name="Sales Executive",
            permissions=[
                "dashboard.view",
                "crm.*",
                "dealers.*",
                "sales.*",
                "pos.*",
                "rfid.view",
                "comms.*",
                "whatsapp.*",
                "agents.view",
                "compliance.view",
                "inventory.view",
                "logistics.view",
            ],
        )
        db.add(sales_role)
        db.flush()
        changed = True
    else:
        sperms = list(sales_role.permissions or [])
        for p in ("pos.*", "rfid.view", "comms.*", "whatsapp.*", "agents.view", "compliance.view"):
            if p not in sperms:
                sperms.append(p)
                changed = True
        sales_role.permissions = sperms

    if sales_role and not db.query(User).filter(User.email == "sales@kanhaerp.com").first():
        db.add(
            User(
                company_id=company.id,
                email="sales@kanhaerp.com",
                full_name="Sales User",
                password_hash=hash_password("sales123"),
                role_id=sales_role.id,
                is_active=True,
            )
        )
        changed = True

    # Accounts / books demo login (3rd portal role)
    accounts_role = db.query(Role).filter(Role.company_id == company.id, Role.code == "accounts").first()
    if not accounts_role:
        accounts_role = Role(
            company_id=company.id,
            code="accounts",
            name="Accounts",
            permissions=[
                "dashboard.view",
                "accounting.*",
                "purchase.*",
                "sales.view",
                "inventory.view",
                "reports.*",
                "compliance.view",
                "documents.view",
            ],
        )
        db.add(accounts_role)
        db.flush()
        changed = True

    if accounts_role and not db.query(User).filter(User.email == "accounts@kanhaerp.com").first():
        db.add(
            User(
                company_id=company.id,
                email="accounts@kanhaerp.com",
                full_name="Accounts User",
                password_hash=hash_password("accounts123"),
                role_id=accounts_role.id,
                is_active=True,
            )
        )
        changed = True

    # ── Completeness pack: empty modules get demo rows so every page is full ──
    inv = db.query(Invoice).filter(Invoice.company_id == company.id).order_by(Invoice.id.desc()).first()
    accounts = {
        a.code: a
        for a in db.query(Account).filter(Account.company_id == company.id, Account.is_group == False).all()  # noqa: E712
    }
    if db.query(JournalEntry).filter(JournalEntry.company_id == company.id).count() == 0 and accounts.get("1300") and accounts.get("4100"):
        amt = float(inv.subtotal) if inv else 10000.0
        tax = float(inv.tax) if inv else 1800.0
        total = amt + tax
        gst_acc = accounts.get("2200") or accounts["4100"]
        db.add(
            JournalEntry(
                company_id=company.id,
                number="JV-202607-0001",
                entry_date=date.today(),
                narration=f"Sales posting · {inv.number if inv else 'demo'}",
                lines=[
                    {"account_id": accounts["1300"].id, "account_code": "1300", "debit": total, "credit": 0},
                    {"account_id": accounts["4100"].id, "account_code": "4100", "debit": 0, "credit": amt},
                    {"account_id": gst_acc.id, "account_code": gst_acc.code, "debit": 0, "credit": tax},
                ],
                status="posted",
            )
        )
        changed = True

    if db.query(Budget).filter(Budget.company_id == company.id).count() == 0:
        db.add(
            Budget(
                company_id=company.id,
                name="FY operating budget",
                fiscal_year=str(date.today().year),
                lines=[
                    {"account": "Sales", "budget": 5000000},
                    {"account": "COGS", "budget": 2800000},
                    {"account": "Salaries", "budget": 900000},
                    {"account": "Rent", "budget": 240000},
                ],
            )
        )
        changed = True

    if inv and db.query(EwayBill).filter(EwayBill.company_id == company.id).count() == 0:
        db.add(
            EwayBill(
                company_id=company.id,
                number="EWB-202607-0001",
                invoice_id=inv.id,
                invoice_number=inv.number,
                from_place="Mumbai",
                to_place="Pune",
                vehicle_no="MH12AB1234",
                ewb_no="DEMO-EWB-" + str(inv.id).zfill(8),
                valid_upto=(date.today() + timedelta(days=1)).isoformat(),
                status="active",
            )
        )
        changed = True

    po = db.query(PurchaseOrder).filter(PurchaseOrder.company_id == company.id).first()
    if po and db.query(PurchaseInvoice).filter(PurchaseInvoice.company_id == company.id).count() == 0:
        if db.query(GoodsReceipt).filter(GoodsReceipt.company_id == company.id).count() == 0:
            db.add(
                GoodsReceipt(
                    company_id=company.id,
                    number="GRN-202607-0001",
                    purchase_order_id=po.id,
                    status="received",
                    lines=po.lines or [],
                )
            )
        db.add(
            PurchaseInvoice(
                company_id=company.id,
                number="PI-202607-0001",
                vendor_id=po.vendor_id,
                purchase_order_id=po.id,
                status="posted",
                subtotal=po.subtotal,
                tax=po.tax,
                total=po.total,
                lines=po.lines or [],
            )
        )
        changed = True

    tags = db.query(RfidTag).filter(RfidTag.company_id == company.id).limit(3).all()
    if tags and db.query(RfidScan).filter(RfidScan.company_id == company.id).count() == 0:
        for i, tag in enumerate(tags):
            db.add(
                RfidScan(
                    company_id=company.id,
                    epc=tag.epc,
                    action=["inbound", "locate", "outbound"][i % 3],
                    warehouse_id=tag.warehouse_id,
                    product_id=tag.product_id,
                    user_id=admin.id if admin else None,
                    notes="Seed scan",
                )
            )
        changed = True

    if db.query(CommsMessage).filter(CommsMessage.company_id == company.id).count() == 0:
        cust = db.query(Customer).filter(Customer.company_id == company.id).first()
        db.add(
            CommsMessage(
                company_id=company.id,
                channel="whatsapp",
                to_name=cust.name if cust else "Demo Customer",
                to_phone=getattr(cust, "phone", None) or "9999999999",
                template="invoice_ready",
                body="Namaste — aapka invoice ready hai. KanhaERP demo.",
                status="queued",
                meta={"direction": "outbound"},
            )
        )
        db.add(
            CommsMessage(
                company_id=company.id,
                channel="whatsapp",
                to_name="Sales desk",
                to_phone="9999999999",
                template="inbound",
                body="Price list chahiye welding electrodes ke liye",
                status="received",
                meta={"direction": "inbound"},
            )
        )
        changed = True

    if db.query(MonitorSite).filter(MonitorSite.company_id == company.id).count() == 0:
        site = MonitorSite(
            company_id=company.id,
            code="HQ-CAM",
            name="Mumbai HQ",
            city="Mumbai",
            notes="Demo site — stream URLs only, no video stored",
        )
        db.add(site)
        db.flush()
        db.add(
            MonitorCamera(
                company_id=company.id,
                site_id=site.id,
                name="Gate",
                stream_url="https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
                location_label="Main gate",
                active=True,
            )
        )
        db.add(
            MonitorCamera(
                company_id=company.id,
                site_id=site.id,
                name="Shop floor",
                stream_url="https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
                location_label="Line A",
                active=True,
            )
        )
        plant = MonitorSite(
            company_id=company.id,
            code="PLT-01",
            name="Pune Plant",
            city="Pune",
            notes="Second site for multi-location watch",
        )
        db.add(plant)
        db.flush()
        db.add(
            MonitorCamera(
                company_id=company.id,
                site_id=plant.id,
                name="Warehouse",
                stream_url="https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
                location_label="WH dock",
                active=True,
            )
        )
        changed = True

    # Fix broken demo document links → local placeholder under /uploads
    from pathlib import Path

    from app.core.config import DATA

    upload_dir = DATA / "uploads" / "demo"
    upload_dir.mkdir(parents=True, exist_ok=True)
    for doc in db.query(Document).filter(Document.company_id == company.id).all():
        path = (doc.path or "").strip()
        broken = (not path) or path.startswith("/demo/") or ("/uploads/" not in path)
        if broken:
            base = (doc.name or "sample").replace(" ", "_")
            fname = base if base.lower().endswith(".txt") else (base.rsplit(".", 1)[0] + ".txt")
            fpath = upload_dir / fname
            if not fpath.exists():
                fpath.write_text(
                    f"KanhaERP demo document: {doc.name}\nEntity: {doc.entity}\nReplace with real PDF at go-live.\n",
                    encoding="utf-8",
                )
            new_path = f"/uploads/demo/{fname}"
            if doc.path != new_path:
                doc.path = new_path
                doc.mime = "text/plain"
                changed = True

    # ── Field ops demo: visits / tasks / followups / PR / payment / indent ──
    if not skip_demo_seed and db.query(FieldVisit).filter(FieldVisit.company_id == company.id).count() == 0:
        db.add(
            FieldVisit(
                company_id=company.id,
                plan_no="VIS-DEMO-0001",
                executive_name="Rahul Mehta",
                client_name="Aarav Controls",
                contact_person="Purchase Head",
                purpose="Demo + rate discussion",
                visit_date=date.today(),
                visit_time="11:00",
                status="planned",
            )
        )
        changed = True
    if not skip_demo_seed and db.query(FieldTask).filter(FieldTask.company_id == company.id).count() == 0:
        db.add(
            FieldTask(
                company_id=company.id,
                title="Collect PO soft copy from dealer",
                assignee_name="Rahul Mehta",
                given_by="Admin",
                client_name="Aarav Controls",
                priority="High",
                status="open",
                due_date=date.today() + timedelta(days=2),
                task_type="followup",
            )
        )
        changed = True
    if not skip_demo_seed and db.query(FollowUp).filter(FollowUp.company_id == company.id).count() == 0:
        db.add(
            FollowUp(
                company_id=company.id,
                followup_type="payment",
                party_name="Aarav Controls",
                contact_person="Accounts",
                contact_no="9876543210",
                remarks="Pending invoice reminder",
                executive_name="Sales User",
                followup_date=date.today(),
                next_followup_date=date.today() + timedelta(days=1),
                status="open",
            )
        )
        changed = True
    if not skip_demo_seed and db.query(PurchaseRequisition).filter(PurchaseRequisition.company_id == company.id).count() == 0:
        db.add(
            PurchaseRequisition(
                company_id=company.id,
                number="PR-DEMO-0001",
                requested_by="Store",
                department="Production",
                status="pending",
                lines=[{"item": "Electrode rod 3.15mm", "qty": 100, "uom": "kg"}],
                notes="Kanha PR demo",
            )
        )
        changed = True
    if not skip_demo_seed and db.query(PaymentRequest).filter(PaymentRequest.company_id == company.id).count() == 0:
        db.add(
            PaymentRequest(
                company_id=company.id,
                number="PREQ-DEMO-0001",
                party_name="Demo Vendor",
                party_type="vendor",
                amount=25000,
                purpose="Advance against PO",
                status="pending",
            )
        )
        changed = True
    if not skip_demo_seed and db.query(MaterialIndent).filter(MaterialIndent.company_id == company.id).count() == 0:
        db.add(
            MaterialIndent(
                company_id=company.id,
                number="IND-DEMO-0001",
                purpose="production",
                status="pending",
                lines=[{"item": "Flux powder", "qty": 20, "uom": "kg"}],
            )
        )
        changed = True

    # ── Completeness + showcase — ONLY while demo and not purged ──
    if not skip_demo_seed:
        try:
            from app.services.demo_completeness import fill_demo_completeness

            if fill_demo_completeness(db, company.id):
                changed = True
        except Exception:
            pass

        try:
            from app.services.demo_showcase import ensure_demo_showcase

            if ensure_demo_showcase(db, company.id, admin_id=admin.id if admin else None):
                changed = True
        except Exception:
            pass

    # Tag demo sample for one-click purge — never re-flag after a purge
    if settings.demo_mode and company:
        sj = company.settings_json or {}
        if not sj.get("demo_purged_at") and not sj.get("demo_bundle"):
            from app.services.demo_purge import mark_company_demo_bundle

            mark_company_demo_bundle(db, company.id)
            changed = True

    if changed:
        db.commit()
