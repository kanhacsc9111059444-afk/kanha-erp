"""
Demo / sample data purge — ONLY when DEMO_MODE=true.

One-click clean for go-live demos: wipes auto/sample transactional rows.
HARD BLOCK when DEMO_MODE=false — real operational data cannot use this button.
Keeps: company, users, roles, COA, warehouses, branches, module flags.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    Attendance,
    ApprovalRequest,
    AutomationJob,
    BOM,
    BankReconItem,
    Budget,
    CommsMessage,
    Company,
    CostCentre,
    Customer,
    DealerOrder,
    Delivery,
    DispatchChallan,
    Document,
    DynamicRule,
    Einvoice,
    Employee,
    EmployeeLocation,
    EwayBill,
    ExpenseClaim,
    FailedEntry,
    FieldTask,
    FieldVisit,
    FixedAsset,
    FollowUp,
    GoodsReceipt,
    Invoice,
    JournalEntry,
    Lead,
    LeaveRequest,
    Machine,
    MaterialIndent,
    MonitorCamera,
    MonitorChat,
    MonitorSite,
    MrpPlan,
    Notification,
    Opportunity,
    PackingList,
    Payment,
    PaymentRequest,
    PayrollRun,
    PriceList,
    Product,
    ProductionChallan,
    Project,
    PurchaseInvoice,
    PurchaseOrder,
    PurchaseRequisition,
    QualityInspection,
    Quotation,
    ReportDefinition,
    RfidScan,
    RfidTag,
    RuleProposal,
    SalaryDisbursement,
    SalesOrder,
    ServiceTicket,
    StockBalance,
    StockBatch,
    StockMove,
    SyncState,
    Task,
    Vendor,
    VendorRateQuote,
    Warehouse,
    WhatsAppTemplate,
    WorkDraft,
    WorkOrder,
)


# Children → parents. Masters (Account, User, Role, Warehouse, Branch) kept.
_PURGE_MODELS: list[tuple[str, Any]] = [
    ("rfid_scans", RfidScan),
    ("monitor_chats", MonitorChat),
    ("monitor_cameras", MonitorCamera),
    ("monitor_sites", MonitorSite),
    ("failed_entries", FailedEntry),
    ("work_drafts", WorkDraft),
    ("rule_proposals", RuleProposal),
    ("dynamic_rules", DynamicRule),
    ("comms_messages", CommsMessage),
    ("notifications", Notification),
    ("einvoices", Einvoice),
    ("eway_bills", EwayBill),
    ("dispatch_challans", DispatchChallan),
    ("packing_lists", PackingList),
    ("dealer_orders", DealerOrder),
    ("stock_batches", StockBatch),
    ("stock_moves", StockMove),
    ("stock_balances", StockBalance),
    ("mrp_plans", MrpPlan),
    ("production_challans", ProductionChallan),
    ("work_orders", WorkOrder),
    ("quality_inspections", QualityInspection),
    ("boms", BOM),
    ("machines", Machine),
    ("service_tickets", ServiceTicket),
    ("tasks", Task),
    ("projects", Project),
    ("expense_claims", ExpenseClaim),
    ("salary_disbursements", SalaryDisbursement),
    ("payroll_runs", PayrollRun),
    ("leave_requests", LeaveRequest),
    ("attendance", Attendance),
    ("employee_locations", EmployeeLocation),
    ("employees", Employee),
    ("payments", Payment),
    ("payment_requests", PaymentRequest),
    ("deliveries", Delivery),
    ("invoices", Invoice),
    ("sales_orders", SalesOrder),
    ("quotations", Quotation),
    ("purchase_invoices", PurchaseInvoice),
    ("goods_receipts", GoodsReceipt),
    ("purchase_orders", PurchaseOrder),
    ("purchase_requisitions", PurchaseRequisition),
    ("material_indents", MaterialIndent),
    ("vendor_rate_quotes", VendorRateQuote),
    ("field_visits", FieldVisit),
    ("field_tasks", FieldTask),
    ("followups", FollowUp),
    ("approval_requests", ApprovalRequest),
    ("bank_recon_items", BankReconItem),
    ("cost_centres", CostCentre),
    ("opportunities", Opportunity),
    ("leads", Lead),
    ("documents", Document),
    ("journal_entries", JournalEntry),
    ("budgets", Budget),
    ("fixed_assets", FixedAsset),
    ("rfid_tags", RfidTag),
    ("products", Product),
    ("vendors", Vendor),
    ("customers", Customer),
    ("price_lists", PriceList),
    ("whatsapp_templates", WhatsAppTemplate),
    ("automation_jobs", AutomationJob),
    ("report_definitions", ReportDefinition),
]


def mark_company_demo_bundle(db: Session, company_id: int) -> None:
    co = db.get(Company, company_id)
    if not co:
        return
    sj = dict(co.settings_json or {})
    sj["demo_bundle"] = True
    sj["demo_bundle_at"] = datetime.utcnow().isoformat() + "Z"
    sj.pop("demo_purged_at", None)
    sj.pop("ready_for_live_masters", None)
    co.settings_json = sj
    db.flush()


def module_overview(db: Session, company_id: int) -> dict[str, Any]:
    """Per-module counts so every page can show what exists / what's happening."""

    def c(model: Any) -> int:
        if not hasattr(model, "company_id"):
            return 0
        try:
            with db.begin_nested():
                return db.query(model).filter(model.company_id == company_id).count()
        except Exception:
            return 0

    modules = [
        {"key": "crm", "name": "CRM", "what": "Leads, customers, opportunities, quotations", "counts": {"leads": c(Lead), "customers": c(Customer), "opportunities": c(Opportunity), "quotations": c(Quotation)}},
        {"key": "sales", "name": "Sales", "what": "Quotes → SO → Delivery → Invoice → Payment", "counts": {"quotations": c(Quotation), "orders": c(SalesOrder), "deliveries": c(Delivery), "invoices": c(Invoice), "payments": c(Payment)}},
        {"key": "pos", "name": "Scan Billing", "what": "Barcode POS checkout + GST", "counts": {"products": c(Product), "invoices": c(Invoice)}},
        {"key": "purchase", "name": "Purchase", "what": "Vendors, PO, GRN, purchase invoices", "counts": {"vendors": c(Vendor), "orders": c(PurchaseOrder), "grn": c(GoodsReceipt), "invoices": c(PurchaseInvoice)}},
        {"key": "inventory", "name": "Inventory", "what": "Products, warehouses, stock, batches", "counts": {"products": c(Product), "warehouses": c(Warehouse), "balances": c(StockBalance), "batches": c(StockBatch), "moves": c(StockMove)}},
        {"key": "manufacturing", "name": "Manufacturing", "what": "BOM, work orders, machines, MRP", "counts": {"boms": c(BOM), "work_orders": c(WorkOrder), "machines": c(Machine), "mrp": c(MrpPlan)}},
        {"key": "quality", "name": "Quality", "what": "Incoming/process/outgoing inspections + CAPA", "counts": {"inspections": c(QualityInspection)}},
        {"key": "hrms", "name": "HRMS", "what": "Employees, attendance, leave, payroll, expenses", "counts": {"employees": c(Employee), "attendance": c(Attendance), "leaves": c(LeaveRequest), "payroll": c(PayrollRun)}},
        {"key": "projects", "name": "Projects", "what": "Delivery projects + task kanban", "counts": {"projects": c(Project), "tasks": c(Task)}},
        {"key": "service", "name": "Service", "what": "AMC / warranty / complaint tickets", "counts": {"tickets": c(ServiceTicket)}},
        {"key": "logistics", "name": "Logistics", "what": "Packing, dispatch, e-invoice IRN", "counts": {"packing": c(PackingList), "dispatch": c(DispatchChallan), "einvoice": c(Einvoice)}},
        {"key": "dealers", "name": "Dealers", "what": "Channel partners + dealer portal orders", "counts": {"dealer_orders": c(DealerOrder), "price_lists": c(PriceList)}},
        {"key": "rfid", "name": "RFID", "what": "Tags + gate scans (no video store)", "counts": {"tags": c(RfidTag), "scans": c(RfidScan)}},
        {"key": "whatsapp", "name": "WhatsApp", "what": "Templates + outbox (Automation hub)", "counts": {"templates": c(WhatsAppTemplate), "messages": c(CommsMessage)}},
        {"key": "watch", "name": "Live Monitor", "what": "Office sites + camera stream URLs + chat (DVR stays outside ERP)", "counts": {"sites": c(MonitorSite), "cameras": c(MonitorCamera), "chats": c(MonitorChat)}},
        {"key": "automation", "name": "Automation", "what": "Jobs + seasonal/dynamic rules", "counts": {"jobs": c(AutomationJob), "rules": c(DynamicRule)}},
        {"key": "documents", "name": "Documents", "what": "File registry / uploads", "counts": {"docs": c(Document)}},
        {"key": "accounting", "name": "Accounting", "what": "Journals + budgets + fixed assets", "counts": {"journals": c(JournalEntry), "budgets": c(Budget), "assets": c(FixedAsset)}},
    ]
    co = db.get(Company, company_id)
    sj = (co.settings_json or {}) if co else {}
    demo = bool(settings.demo_mode)
    return {
        "ok": True,
        "demo_mode": demo,
        "demo_bundle": bool(sj.get("demo_bundle")),
        "demo_purged_at": sj.get("demo_purged_at"),
        "industry_profile": sj.get("industry_profile") or "hybrid",
        "modules": modules,
        "purge_allowed": demo,
        "purge_confirm_phrase": "DELETE DEMO SAMPLE",
        "purge_note": (
            "One-click purge ONLY removes sample/demo transactional data while DEMO_MODE=true. "
            "When you go live, set DEMO_MODE=false — this button stops working forever on real data."
            if demo
            else "DEMO_MODE=false — purge disabled. Real operational data is protected."
        ),
        "kept_on_purge": ["company", "users", "roles", "chart_of_accounts", "warehouses", "branches", "modules_enabled"],
    }


def purge_demo_data(db: Session, company_id: int, *, confirm: str = "") -> dict[str, Any]:
    if not settings.demo_mode:
        return {
            "ok": False,
            "blocked": True,
            "error": (
                "BLOCKED: DEMO_MODE=false. "
                "This one-click delete only cleans auto/sample demo data. "
                "It will never mass-delete live operational data."
            ),
        }
    if (confirm or "").strip().upper() != "DELETE DEMO SAMPLE":
        return {
            "ok": False,
            "error": 'Type confirm phrase exactly: DELETE DEMO SAMPLE',
        }

    co = db.get(Company, company_id)
    if not co:
        return {"ok": False, "error": "Company not found"}

    deleted: dict[str, int] = {}
    for name, model in _PURGE_MODELS:
        try:
            with db.begin_nested():
                q = db.query(model)
                if hasattr(model, "company_id"):
                    q = q.filter(model.company_id == company_id)
                n = q.delete(synchronize_session=False)
                if n:
                    deleted[name] = int(n)
        except Exception:
            continue

    sj = dict(co.settings_json or {})
    sj["demo_bundle"] = False
    sj["demo_purged_at"] = datetime.utcnow().isoformat() + "Z"
    sj["ready_for_live_masters"] = True
    co.settings_json = sj

    for row in db.query(SyncState).filter(SyncState.key.like("idem:%")).all():
        db.delete(row)

    db.flush()
    return {
        "ok": True,
        "deleted": deleted,
        "total_rows": sum(deleted.values()),
        "kept": ["company", "users", "roles", "accounts(COA)", "warehouses", "branches", "modules_enabled"],
        "message": (
            f"Demo/sample data purged ({sum(deleted.values())} rows). "
            "Masters (users/roles/COA/warehouses) kept — ab real products/customers/vendors enter karo. "
            "Restart pe demo rows wapas NAHI aayenge (demo_purged_at locked). "
            "Go-live: set DEMO_MODE=false in .env + paste WhatsApp/GSP keys."
        ),
        "reseed_blocked": True,
        "next_steps": [
            "Enter real products, customers, vendors",
            "Paste WHATSAPP_TOKEN + WHATSAPP_PHONE_NUMBER_ID in .env for live WhatsApp",
            "Paste GSP_BASE_URL + GSP_API_KEY for live IRN/e-Way",
            "Set DEMO_MODE=false and restart before production use",
        ],
    }
