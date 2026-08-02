"""Dense demo showcase — every module opens with clickable sample data."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import (
    Account,
    ApprovalRequest,
    BankReconItem,
    CostCentre,
    FieldTask,
    FieldVisit,
    FollowUp,
    Invoice,
    JournalEntry,
    MaterialIndent,
    PaymentRequest,
    ProductionChallan,
    Product,
    PurchaseRequisition,
    VendorRateQuote,
    Warehouse,
    WorkOrder,
)


def ensure_demo_showcase(db: Session, company_id: int, admin_id: int | None = None) -> bool:
    """Fill remaining gaps so every tab shows working demo rows."""
    changed = False
    today = date.today()

    # Cost centres
    if db.query(CostCentre).filter(CostCentre.company_id == company_id).count() == 0:
        for code, name in (("HO", "Head Office"), ("PLANT", "Plant / Works"), ("SALES", "Sales Desk")):
            db.add(CostCentre(company_id=company_id, code=code, name=name))
        changed = True

    # RFQ rates
    if db.query(VendorRateQuote).filter(VendorRateQuote.company_id == company_id).count() < 3:
        samples = [
            ("Steel Mart", "Electrode 3.15mm", 118.0, 100, "kg"),
            ("Flux India", "Flux powder", 42.5, 50, "kg"),
            ("Copper Hub", "Copper tip", 85.0, 200, "nos"),
        ]
        for vn, item, rate, qty, uom in samples:
            exists = (
                db.query(VendorRateQuote)
                .filter(
                    VendorRateQuote.company_id == company_id,
                    VendorRateQuote.vendor_name == vn,
                    VendorRateQuote.item_name == item,
                )
                .first()
            )
            if not exists:
                db.add(
                    VendorRateQuote(
                        company_id=company_id,
                        vendor_name=vn,
                        item_name=item,
                        rate=rate,
                        qty=qty,
                        uom=uom,
                        status="active",
                        notes="Demo RFQ for purchase path",
                        created_by=admin_id,
                    )
                )
                changed = True

    # Extra field ops density
    visit_n = db.query(FieldVisit).filter(FieldVisit.company_id == company_id).count()
    if visit_n < 3:
        for i, client in enumerate(("Aarav Controls", "Jaipur Auto", "Delhi Traders"), start=visit_n + 1):
            db.add(
                FieldVisit(
                    company_id=company_id,
                    plan_no=f"VIS-DEMO-{i:04d}",
                    executive_name="Rahul Mehta",
                    client_name=client,
                    contact_person="Purchase",
                    purpose="Rate + sample follow-up",
                    visit_date=today + timedelta(days=i - 1),
                    visit_time=f"{10 + i}:00",
                    status="planned" if i > 1 else "done",
                    created_by=admin_id,
                )
            )
            changed = True

    if db.query(FieldTask).filter(FieldTask.company_id == company_id).count() < 3:
        for title, pri in (
            ("Collect GST certificate", "High"),
            ("Share rate list WhatsApp", "Medium"),
            ("Schedule plant visit", "Low"),
        ):
            if not db.query(FieldTask).filter(FieldTask.company_id == company_id, FieldTask.title == title).first():
                db.add(
                    FieldTask(
                        company_id=company_id,
                        title=title,
                        assignee_name="Rahul Mehta",
                        given_by="Admin",
                        client_name="Aarav Controls",
                        priority=pri,
                        status="open",
                        due_date=today + timedelta(days=3),
                        task_type="followup",
                        created_by=admin_id,
                    )
                )
                changed = True

    if db.query(FollowUp).filter(FollowUp.company_id == company_id).count() < 3:
        for ptype, party, rem in (
            ("order", "Jaipur Auto", "Confirm SO qty"),
            ("payment", "Aarav Controls", "Overdue chase"),
            ("lead", "Stress Lead Walk-in", "Convert to quote"),
        ):
            if not db.query(FollowUp).filter(FollowUp.company_id == company_id, FollowUp.remarks == rem).first():
                db.add(
                    FollowUp(
                        company_id=company_id,
                        followup_type=ptype,
                        party_name=party,
                        contact_person="Desk",
                        contact_no="9876500000",
                        remarks=rem,
                        executive_name="Sales User",
                        followup_date=today,
                        next_followup_date=today,
                        status="open",
                        created_by=admin_id,
                    )
                )
                changed = True

    if db.query(PurchaseRequisition).filter(PurchaseRequisition.company_id == company_id).count() < 2:
        db.add(
            PurchaseRequisition(
                company_id=company_id,
                number=f"PR-DEMO-{db.query(PurchaseRequisition).filter(PurchaseRequisition.company_id == company_id).count() + 2:04d}",
                requested_by="Production",
                department="Plant",
                status="approved",
                lines=[{"item": "Copper tip", "qty": 50, "uom": "nos", "rate": 85}],
                notes="Approved — ready → PO",
                created_by=admin_id,
            )
        )
        changed = True

    if db.query(MaterialIndent).filter(MaterialIndent.company_id == company_id).count() < 2:
        db.add(
            MaterialIndent(
                company_id=company_id,
                number="IND-DEMO-0002",
                purpose="maintenance",
                status="approved",
                lines=[{"item": "Grease", "qty": 5, "uom": "kg"}],
                notes="Approved — ready → PR",
                created_by=admin_id,
            )
        )
        changed = True

    if db.query(PaymentRequest).filter(PaymentRequest.company_id == company_id).count() < 2:
        db.add(
            PaymentRequest(
                company_id=company_id,
                number="PREQ-DEMO-0002",
                party_name="Steel Mart",
                party_type="vendor",
                amount=18000,
                purpose="Freight clearance",
                status="approved",
                created_by=admin_id,
            )
        )
        changed = True

    # Books: cash + bank vouchers (for cash/bank books)
    accounts = {
        a.code: a
        for a in db.query(Account).filter(Account.company_id == company_id, Account.is_group == False).all()  # noqa: E712
    }
    cash, bank, ar, sales, ap = (
        accounts.get("1100"),
        accounts.get("1200"),
        accounts.get("1300"),
        accounts.get("4100"),
        accounts.get("2100"),
    )
    jv_count = db.query(JournalEntry).filter(JournalEntry.company_id == company_id).count()
    if cash and bank and ar and jv_count < 8:
        demos = [
            ("receipt", "RCT-SHOW-1", "Aarav Controls", cash, ar, 25000, "Demo customer receipt → Cash"),
            ("receipt", "RCT-SHOW-2", "Jaipur Auto", bank, ar, 48000, "Demo UPI receipt → Bank"),
            ("payment", "PMT-SHOW-1", "Steel Mart", ap or ar, bank, 15000, "Demo vendor payment from Bank"),
            ("contra", "CNT-SHOW-1", "", cash, bank, 5000, "Demo cash deposit to bank"),
        ]
        for vtype, num, party, dr_acc, cr_acc, amt, nar in demos:
            if not dr_acc or not cr_acc:
                continue
            if db.query(JournalEntry).filter(JournalEntry.company_id == company_id, JournalEntry.number == num).first():
                continue
            # receipt: Dr cash/bank Cr AR; payment: Dr AP Cr bank; contra: Dr cash Cr bank
            if vtype == "payment":
                lines = [
                    {"account_id": dr_acc.id, "account_code": dr_acc.code, "debit": amt, "credit": 0},
                    {"account_id": cr_acc.id, "account_code": cr_acc.code, "debit": 0, "credit": amt},
                ]
            elif vtype == "contra":
                lines = [
                    {"account_id": cash.id, "account_code": "1100", "debit": amt, "credit": 0},
                    {"account_id": bank.id, "account_code": "1200", "debit": 0, "credit": amt},
                ]
            else:
                lines = [
                    {"account_id": dr_acc.id, "account_code": dr_acc.code, "debit": amt, "credit": 0},
                    {"account_id": cr_acc.id, "account_code": cr_acc.code, "debit": 0, "credit": amt},
                ]
            db.add(
                JournalEntry(
                    company_id=company_id,
                    number=num,
                    entry_date=today - timedelta(days=1),
                    narration=nar,
                    lines=lines,
                    status="posted",
                    voucher_type=vtype,
                    party_name=party,
                )
            )
            changed = True

    if db.query(BankReconItem).filter(BankReconItem.company_id == company_id).count() < 2:
        db.add(
            BankReconItem(
                company_id=company_id,
                statement_date=today,
                description="UPI IN · Jaipur Auto",
                amount=48000,
                status="open",
                notes="Match with bank book receipt",
            )
        )
        db.add(
            BankReconItem(
                company_id=company_id,
                statement_date=today - timedelta(days=1),
                description="NEFT OUT · Steel Mart",
                amount=-15000,
                status="open",
            )
        )
        changed = True

    # Production challan from WO
    if db.query(ProductionChallan).filter(ProductionChallan.company_id == company_id).count() == 0:
        wo = (
            db.query(WorkOrder)
            .filter(WorkOrder.company_id == company_id)
            .order_by(WorkOrder.id.desc())
            .first()
        )
        wh = db.query(Warehouse).filter(Warehouse.company_id == company_id).first()
        prod = db.get(Product, wo.product_id) if wo else None
        if wo:
            wo.status = "completed"
            db.add(
                ProductionChallan(
                    company_id=company_id,
                    number="PC-DEMO-0001",
                    work_order_id=wo.id,
                    product_id=wo.product_id,
                    warehouse_id=wh.id if wh else None,
                    product_name=prod.name if prod else f"Product#{wo.product_id}",
                    qty=float(wo.qty or 10),
                    status="issued",
                    notes=f"Demo challan from {wo.number} — click Receive stock",
                    created_by=admin_id,
                )
            )
            changed = True

    # Pending approval for Approvals inbox
    if db.query(ApprovalRequest).filter(ApprovalRequest.company_id == company_id, ApprovalRequest.status == "pending").count() == 0:
        db.add(
            ApprovalRequest(
                company_id=company_id,
                module="sales",
                entity_type="sales_order",
                entity_id="DEMO-SO",
                title="Approve demo sales order above limit",
                amount=275000,
                payload={"hint": "Open Approvals → Approve or Reject to see flow"},
                status="pending",
                requested_by=admin_id,
                required_level=2,
                current_level=1,
                emergency=False,
            )
        )
        changed = True

    # Overdue invoice for chase drafts (bump due_date on oldest unpaid)
    inv = (
        db.query(Invoice)
        .filter(Invoice.company_id == company_id, Invoice.total > Invoice.paid)
        .order_by(Invoice.id.asc())
        .first()
    )
    if inv and (not inv.due_date or inv.due_date >= today):
        inv.due_date = today - timedelta(days=18)
        changed = True

    # Extra indent/PR labels for convert buttons
    if db.query(PurchaseRequisition).filter(PurchaseRequisition.company_id == company_id, PurchaseRequisition.status == "pending").count() == 0:
        db.add(
            PurchaseRequisition(
                company_id=company_id,
                number="PR-DEMO-PEND",
                requested_by="Store",
                department="Store",
                status="pending",
                lines=[{"item": "Wire spool", "qty": 12, "uom": "nos", "rate": 220}],
                notes="Pending — click Approve then → PO",
                created_by=admin_id,
            )
        )
        changed = True

    return changed
