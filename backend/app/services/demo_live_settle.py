"""Demo-live settlement helpers — full DB side-effects without external keys."""
from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.core.deps import next_number
from app.models import Account, Customer, Invoice, JournalEntry, Payment, PaymentAllocation


def settle_customer_payment(
    db: Session,
    *,
    company_id: int,
    invoice: Invoice,
    amount: float,
    method: str = "upi",
    reference: str = "",
    gateway: str | None = None,
) -> dict[str, Any]:
    """Apply payment to invoice (+ FIFO overflow), post receipt voucher."""
    amt = round(float(amount or 0), 2)
    if amt <= 0:
        raise ValueError("amount must be > 0")

    bal0 = max(0.0, float(invoice.total) - float(invoice.paid or 0))
    allocs: list[dict] = []
    if amt <= bal0 + 0.01:
        allocs = [{"invoice_id": invoice.id, "amount": amt}]
    else:
        remain = amt
        open_invs = (
            db.query(Invoice)
            .filter(
                Invoice.company_id == company_id,
                Invoice.customer_id == invoice.customer_id,
                Invoice.total > Invoice.paid,
            )
            .order_by(Invoice.invoice_date, Invoice.id)
            .all()
        )
        ordered = [invoice] + [x for x in open_invs if x.id != invoice.id and (x.invoice_type or "sales") != "credit"]
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
            amt = round(amt - remain, 2)
            if amt <= 0:
                raise ValueError("No open balance to settle")

    pay = Payment(
        company_id=company_id,
        invoice_id=invoice.id,
        party_type="customer",
        party_id=invoice.customer_id,
        amount=amt,
        method=method,
        reference=reference,
        gateway=gateway,
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
        target = db.query(Invoice).filter(Invoice.id == iid, Invoice.company_id == company_id).first()
        if not target:
            continue
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
                company_id=company_id,
                payment_id=pay.id,
                invoice_id=target.id,
                amount=use,
            )
        )
        applied.append(
            {
                "invoice": target.number,
                "amount": use,
                "balance": round(target.total - target.paid, 2),
            }
        )

    accounts = {
        a.code: a
        for a in db.query(Account).filter(Account.company_id == company_id, Account.is_group == False).all()  # noqa: E712
    }
    ar = accounts.get("1300")
    cash_bank = (
        accounts.get("1200")
        if (method or "").lower() in ("bank", "upi", "card", "neft", "rtgs", "razorpay")
        else accounts.get("1100")
    )
    cash_bank = cash_bank or accounts.get("1200") or accounts.get("1100")
    receipt_no = None
    if ar and cash_bank and applied:
        cust = db.get(Customer, invoice.customer_id) if invoice.customer_id else None
        receipt_no = next_number(db, company_id, JournalEntry, "RCT")
        db.add(
            JournalEntry(
                company_id=company_id,
                number=receipt_no,
                entry_date=date.today(),
                narration=f"Receipt · {method} · {reference or 'live-demo'} · {', '.join(x['invoice'] for x in applied)}",
                lines=[
                    {"account_id": cash_bank.id, "account_code": cash_bank.code, "debit": amt, "credit": 0},
                    {"account_id": ar.id, "account_code": ar.code, "debit": 0, "credit": amt},
                ],
                status="posted",
                voucher_type="receipt",
                party_name=cust.name if cust else "",
            )
        )

    return {
        "payment_id": pay.id,
        "amount": amt,
        "method": method,
        "reference": reference,
        "gateway": gateway,
        "journal": receipt_no,
        "allocations": applied,
        "message": f"Settled ₹{amt:,.2f} · {len(applied)} bill(s)" + (f" · {receipt_no}" if receipt_no else ""),
    }


def post_expense_payment_voucher(
    db: Session,
    *,
    company_id: int,
    claim_id: int,
    amount: float,
    employee_name: str,
    category: str,
) -> str | None:
    """Dr Staff expense / Cr Bank for paid claim."""
    accounts = {
        a.code: a
        for a in db.query(Account).filter(Account.company_id == company_id, Account.is_group == False).all()  # noqa: E712
    }
    exp = accounts.get("5100") or accounts.get("5200") or accounts.get("5000")
    bank = accounts.get("1200") or accounts.get("1100")
    if not exp or not bank:
        return None
    amt = round(float(amount), 2)
    number = next_number(db, company_id, JournalEntry, "PMT")
    db.add(
        JournalEntry(
            company_id=company_id,
            number=number,
            entry_date=date.today(),
            narration=f"Expense paid · claim #{claim_id} · {employee_name} · {category}",
            lines=[
                {"account_id": exp.id, "account_code": exp.code, "debit": amt, "credit": 0},
                {"account_id": bank.id, "account_code": bank.code, "debit": 0, "credit": amt},
            ],
            status="posted",
            voucher_type="payment",
            party_name=employee_name,
        )
    )
    return number


def post_salary_disbursement_voucher(
    db: Session,
    *,
    company_id: int,
    period: str,
    total: float,
    disbursement_id: int,
) -> str | None:
    accounts = {
        a.code: a
        for a in db.query(Account).filter(Account.company_id == company_id, Account.is_group == False).all()  # noqa: E712
    }
    salary = accounts.get("5200") or accounts.get("5100") or accounts.get("5000")
    bank = accounts.get("1200") or accounts.get("1100")
    if not salary or not bank:
        return None
    amt = round(float(total), 2)
    number = next_number(db, company_id, JournalEntry, "SAL")
    db.add(
        JournalEntry(
            company_id=company_id,
            number=number,
            entry_date=date.today(),
            narration=f"Salary disbursement demo · {period} · batch #{disbursement_id}",
            lines=[
                {"account_id": salary.id, "account_code": salary.code, "debit": amt, "credit": 0},
                {"account_id": bank.id, "account_code": bank.code, "debit": 0, "credit": amt},
            ],
            status="posted",
            voucher_type="payment",
            party_name=f"Payroll {period}",
        )
    )
    return number
