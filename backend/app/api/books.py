"""Kanha Books — own double-entry desk (Tally-style vouchers, day book, ledgers)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.core.deps import CurrentUser, DbDep, audit, next_number
from app.models import Account, JournalEntry

router = APIRouter(prefix="/api/books", tags=["kanha-books"])

VOUCHER_PREFIX = {
    "payment": "PMT",
    "receipt": "RCT",
    "contra": "CNT",
    "journal": "JV",
    "sales": "SV",
    "purchase": "PV",
    "credit_note": "CN",
    "debit_note": "DN",
}


def _ensure_voucher_columns(db) -> None:
    try:
        cols = {r[1] for r in db.execute(text("PRAGMA table_info(journal_entries)")).fetchall()}
        if "voucher_type" not in cols:
            db.execute(text("ALTER TABLE journal_entries ADD COLUMN voucher_type VARCHAR(32) DEFAULT 'journal'"))
        if "party_name" not in cols:
            db.execute(text("ALTER TABLE journal_entries ADD COLUMN party_name VARCHAR(200) DEFAULT ''"))
        if "custom" not in cols:
            db.execute(text("ALTER TABLE journal_entries ADD COLUMN custom JSON DEFAULT '{}'"))
        acc_cols = {r[1] for r in db.execute(text("PRAGMA table_info(accounts)")).fetchall()}
        if "custom" not in acc_cols:
            db.execute(text("ALTER TABLE accounts ADD COLUMN custom JSON DEFAULT '{}'"))
        db.commit()
    except Exception:
        db.rollback()


def _coa_map(db, company_id: int) -> dict[str, Account]:
    return {
        a.code: a
        for a in db.query(Account)
        .filter(Account.company_id == company_id, Account.is_group == False)  # noqa: E712
        .all()
    }


def _balance_check(lines: list[dict]) -> tuple[float, float]:
    debit = sum(float(ln.get("debit") or 0) for ln in lines)
    credit = sum(float(ln.get("credit") or 0) for ln in lines)
    if abs(debit - credit) > 0.05:
        raise HTTPException(400, f"Voucher not balanced (Dr {debit} != Cr {credit})")
    return debit, credit


@router.get("/summary")
def books_summary(user: CurrentUser, db: DbDep) -> dict:
    _ensure_voucher_columns(db)
    cid = user.company_id
    vouchers = db.query(JournalEntry).filter(JournalEntry.company_id == cid).all()
    by_type: dict[str, int] = {}
    for v in vouchers:
        t = getattr(v, "voucher_type", None) or "journal"
        by_type[t] = by_type.get(t, 0) + 1
    cash = _coa_map(db, cid).get("1100")
    bank = _coa_map(db, cid).get("1200")
    cash_bal = bank_bal = 0.0
    for v in vouchers:
        for ln in v.lines or []:
            aid = ln.get("account_id")
            if cash and aid == cash.id:
                cash_bal += float(ln.get("debit") or 0) - float(ln.get("credit") or 0)
            if bank and aid == bank.id:
                bank_bal += float(ln.get("debit") or 0) - float(ln.get("credit") or 0)
    return {
        "ok": True,
        "module": "Kanha Books",
        "tagline": "Built-in accounts desk — no external Tally dependency",
        "voucher_count": len(vouchers),
        "by_type": by_type,
        "cash_balance": round(cash_bal, 2),
        "bank_balance": round(bank_bal, 2),
        "coa_count": db.query(Account).filter(Account.company_id == cid).count(),
    }


@router.get("/daybook")
def daybook(user: CurrentUser, db: DbDep, on_date: str | None = None) -> dict:
    _ensure_voucher_columns(db)
    d = date.fromisoformat(on_date) if on_date else date.today()
    rows = (
        db.query(JournalEntry)
        .filter(JournalEntry.company_id == user.company_id, JournalEntry.entry_date == d)
        .order_by(JournalEntry.id.desc())
        .all()
    )
    return {
        "date": d.isoformat(),
        "entries": [_voucher_out(r) for r in rows],
        "count": len(rows),
    }


@router.get("/vouchers")
def list_vouchers(user: CurrentUser, db: DbDep, voucher_type: str | None = None, limit: int = 80) -> list[dict]:
    _ensure_voucher_columns(db)
    q = db.query(JournalEntry).filter(JournalEntry.company_id == user.company_id)
    if voucher_type:
        q = q.filter(JournalEntry.voucher_type == voucher_type)
    rows = q.order_by(JournalEntry.id.desc()).limit(min(limit, 200)).all()
    return [_voucher_out(r) for r in rows]


def _voucher_out(r: JournalEntry) -> dict:
    debit = sum(float(ln.get("debit") or 0) for ln in (r.lines or []))
    credit = sum(float(ln.get("credit") or 0) for ln in (r.lines or []))
    return {
        "id": r.id,
        "number": r.number,
        "voucher_type": getattr(r, "voucher_type", None) or "journal",
        "party_name": getattr(r, "party_name", None) or "",
        "entry_date": r.entry_date.isoformat() if r.entry_date else None,
        "narration": r.narration,
        "status": r.status,
        "debit": debit,
        "credit": credit,
        "lines": r.lines or [],
        "custom": getattr(r, "custom", None) or {},
    }


class VoucherIn(BaseModel):
    voucher_type: str = "journal"
    party_name: str = ""
    narration: str = ""
    amount: float = 0
    entry_date: date | None = None
    lines: list[dict[str, Any]] = Field(default_factory=list)
    from_account: str = ""
    to_account: str = ""
    cost_centre: str = ""
    # SBAC Voucherdenominations extras
    receipt_type: str = "Bill"  # Bill / On Account
    cheque_no: str = ""
    cheque_date: str = ""
    currency: str = "Indian Rupee (INR)"
    exchange_rate: float = 1
    convert_amount: float = 0
    sub_narration: str = ""
    adjust_amount: float = 0
    remarks: str = ""
    voucher_mode: str = ""  # Receipt/Payment/Contra/… when switching type on form


class LedgerIn(BaseModel):
    code: str
    name: str
    account_type: str = "expense"  # asset/liability/equity/income/expense
    parent_id: int | None = None
    parent_code: str = ""
    is_group: bool = False
    opening_balance: float = 0
    bal_type: str = "Debit"  # Debit / Credit
    opening_date: str = ""
    currency: str = "Indian Rupee (INR)"
    other_value_pct: float = 0
    other_value_status: str = "No"
    # SBAC bill-wise opening bills grid
    bill_wise: list[dict[str, Any]] = Field(default_factory=list)


@router.post("/vouchers")
def create_voucher(body: VoucherIn, user: CurrentUser, db: DbDep) -> dict:
    from app.services.period_lock import assert_period_open

    _ensure_voucher_columns(db)
    vtype = (body.voucher_type or "journal").lower().strip()
    if vtype not in VOUCHER_PREFIX:
        raise HTTPException(400, f"Unknown voucher type: {vtype}")
    entry_date = body.entry_date or date.today()
    assert_period_open(db, user.company_id, entry_date)
    accounts = _coa_map(db, user.company_id)
    lines = list(body.lines or [])

    # Enrich lines that only have account_code
    if lines:
        enriched: list[dict] = []
        for ln in lines:
            row = dict(ln)
            code = (row.get("account_code") or "").strip()
            if not row.get("account_id") and code:
                acc = accounts.get(code)
                if not acc:
                    raise HTTPException(400, f"Unknown account code {code}")
                row["account_id"] = acc.id
                row["account_code"] = acc.code
            enriched.append(row)
        lines = enriched

    if not lines:
        amt = float(body.amount or 0)
        if amt <= 0:
            raise HTTPException(400, "Amount or balanced lines required")
        cash = accounts.get("1100")
        bank = accounts.get("1200")
        ar = accounts.get("1300")
        ap = accounts.get("2100")
        sales = accounts.get("4100")
        purchase = accounts.get("5100") or accounts.get("5000")
        gst = accounts.get("2200")

        def need(code: str, acc: Account | None) -> Account:
            if not acc:
                raise HTTPException(400, f"COA missing account {code} — seed/open Accounting once")
            return acc

        if vtype == "payment":
            # Dr Expense/AP, Cr Bank/Cash
            dr = accounts.get(body.to_account) or ap or accounts.get("5200")
            cr = accounts.get(body.from_account) or bank or cash
            dr, cr = need("AP/expense", dr), need("Bank/Cash", cr)
            lines = [
                {"account_id": dr.id, "account_code": dr.code, "debit": amt, "credit": 0},
                {"account_id": cr.id, "account_code": cr.code, "debit": 0, "credit": amt},
            ]
        elif vtype == "receipt":
            dr = accounts.get(body.to_account) or bank or cash
            cr = accounts.get(body.from_account) or ar
            dr, cr = need("Bank/Cash", dr), need("AR", cr)
            lines = [
                {"account_id": dr.id, "account_code": dr.code, "debit": amt, "credit": 0},
                {"account_id": cr.id, "account_code": cr.code, "debit": 0, "credit": amt},
            ]
        elif vtype == "contra":
            dr = accounts.get(body.to_account) or cash
            cr = accounts.get(body.from_account) or bank
            dr, cr = need("Cash", dr), need("Bank", cr)
            lines = [
                {"account_id": dr.id, "account_code": dr.code, "debit": amt, "credit": 0},
                {"account_id": cr.id, "account_code": cr.code, "debit": 0, "credit": amt},
            ]
        elif vtype == "sales":
            taxable = round(amt / 1.18, 2) if amt else 0
            tax = round(amt - taxable, 2)
            ar_a, sales_a = need("1300", ar), need("4100", sales)
            lines = [
                {"account_id": ar_a.id, "account_code": ar_a.code, "debit": amt, "credit": 0},
                {"account_id": sales_a.id, "account_code": sales_a.code, "debit": 0, "credit": taxable},
            ]
            if gst and tax:
                lines.append({"account_id": gst.id, "account_code": gst.code, "debit": 0, "credit": tax})
            else:
                lines[1]["credit"] = amt
        elif vtype == "purchase":
            taxable = round(amt / 1.18, 2) if amt else 0
            tax = round(amt - taxable, 2)
            pur = need("1400", accounts.get("1400") or purchase)  # Inventory preferred
            ap_a = need("2100", ap)
            itc = accounts.get("2210") or gst
            if itc and tax:
                lines = [
                    {"account_id": pur.id, "account_code": pur.code, "debit": taxable, "credit": 0},
                    {"account_id": itc.id, "account_code": itc.code, "debit": tax, "credit": 0},
                    {"account_id": ap_a.id, "account_code": ap_a.code, "debit": 0, "credit": amt},
                ]
            else:
                lines = [
                    {"account_id": pur.id, "account_code": pur.code, "debit": amt, "credit": 0},
                    {"account_id": ap_a.id, "account_code": ap_a.code, "debit": 0, "credit": amt},
                ]
        elif vtype == "credit_note":
            # Reduce AR / sales (Dr Sales, Cr AR) — SBAC credit note concept
            ar_a, sales_a = need("1300", ar), need("4100", sales)
            lines = [
                {"account_id": sales_a.id, "account_code": sales_a.code, "debit": amt, "credit": 0},
                {"account_id": ar_a.id, "account_code": ar_a.code, "debit": 0, "credit": amt},
            ]
        elif vtype == "debit_note":
            # Increase AP / purchase (Dr Purchase, Cr AP)
            pur = need("5100", purchase or accounts.get("1400"))
            ap_a = need("2100", ap)
            lines = [
                {"account_id": pur.id, "account_code": pur.code, "debit": amt, "credit": 0},
                {"account_id": ap_a.id, "account_code": ap_a.code, "debit": 0, "credit": amt},
            ]
        else:  # journal
            if body.from_account and body.to_account:
                cr = need(body.from_account, accounts.get(body.from_account))
                dr = need(body.to_account, accounts.get(body.to_account))
                lines = [
                    {"account_id": dr.id, "account_code": dr.code, "debit": amt, "credit": 0},
                    {"account_id": cr.id, "account_code": cr.code, "debit": 0, "credit": amt},
                ]
            else:
                ar_a, sales_a = need("1300", ar), need("4100", sales)
                lines = [
                    {"account_id": ar_a.id, "account_code": ar_a.code, "debit": amt, "credit": 0},
                    {"account_id": sales_a.id, "account_code": sales_a.code, "debit": 0, "credit": amt},
                ]

    debit, credit = _balance_check(lines)
    prefix = VOUCHER_PREFIX[vtype]
    nar = body.narration or f"{vtype.title()} voucher"
    if body.cost_centre:
        nar = f"[{body.cost_centre}] {nar}"
    row = JournalEntry(
        company_id=user.company_id,
        number=next_number(db, user.company_id, JournalEntry, prefix),
        entry_date=entry_date,
        narration=nar,
        lines=lines,
        status="posted",
        voucher_type=vtype,
        party_name=body.party_name or "",
        custom={
            "receipt_type": body.receipt_type,
            "cheque_no": body.cheque_no,
            "cheque_date": body.cheque_date,
            "currency": body.currency,
            "exchange_rate": body.exchange_rate,
            "convert_amount": body.convert_amount,
            "sub_narration": body.sub_narration,
            "adjust_amount": body.adjust_amount,
            "remarks": body.remarks,
            "cost_centre": body.cost_centre,
            "from_account": body.from_account,
            "to_account": body.to_account,
            "source": "kanha_books_voucher",
            "sbac_parity": "2026-08-02-live",
        },
    )
    db.add(row)
    audit(db, company_id=user.company_id, user_id=user.id, action="books_voucher", entity="journal", entity_id=row.number)
    db.commit()
    db.refresh(row)
    return {"ok": True, **_voucher_out(row), "debit": debit, "credit": credit}


@router.get("/ledger/{account_code}")
def ledger_view(account_code: str, user: CurrentUser, db: DbDep) -> dict:
    _ensure_voucher_columns(db)
    acc = (
        db.query(Account)
        .filter(Account.company_id == user.company_id, Account.code == account_code)
        .first()
    )
    if not acc:
        raise HTTPException(404, "Account not found")
    entries = []
    bal = 0.0
    for j in (
        db.query(JournalEntry)
        .filter(JournalEntry.company_id == user.company_id)
        .order_by(JournalEntry.entry_date, JournalEntry.id)
        .all()
    ):
        for ln in j.lines or []:
            if ln.get("account_id") == acc.id or ln.get("account_code") == account_code:
                dr = float(ln.get("debit") or 0)
                cr = float(ln.get("credit") or 0)
                bal += dr - cr
                entries.append(
                    {
                        "date": j.entry_date.isoformat() if j.entry_date else None,
                        "voucher": j.number,
                        "voucher_type": getattr(j, "voucher_type", None) or "journal",
                        "narration": j.narration,
                        "debit": dr,
                        "credit": cr,
                        "balance": round(bal, 2),
                    }
                )
    return {
        "account": {"code": acc.code, "name": acc.name, "type": acc.account_type},
        "entries": entries,
        "closing": round(bal, 2),
    }


@router.get("/reports/trial-balance")
def books_trial(user: CurrentUser, db: DbDep) -> list[dict]:
    accounts = (
        db.query(Account)
        .filter(Account.company_id == user.company_id, Account.is_group == False)  # noqa: E712
        .all()
    )
    bal: dict[int, dict[str, Any]] = {
        a.id: {"code": a.code, "name": a.name, "debit": 0.0, "credit": 0.0} for a in accounts
    }
    for j in db.query(JournalEntry).filter(JournalEntry.company_id == user.company_id).all():
        for ln in j.lines or []:
            aid = ln.get("account_id")
            if aid in bal:
                bal[aid]["debit"] += float(ln.get("debit") or 0)
                bal[aid]["credit"] += float(ln.get("credit") or 0)
    out = []
    for b in bal.values():
        net_dr = max(0.0, b["debit"] - b["credit"])
        net_cr = max(0.0, b["credit"] - b["debit"])
        if net_dr or net_cr or b["debit"] or b["credit"]:
            out.append({"code": b["code"], "name": b["name"], "debit": round(net_dr, 2), "credit": round(net_cr, 2)})
    return sorted(out, key=lambda x: x["code"])


@router.get("/export-pack")
def books_export(user: CurrentUser, db: DbDep) -> dict:
    """JSON pack for accountant / backup — Kanha-native format."""
    vouchers = (
        db.query(JournalEntry)
        .filter(JournalEntry.company_id == user.company_id)
        .order_by(JournalEntry.id.desc())
        .limit(500)
        .all()
    )
    coa = db.query(Account).filter(Account.company_id == user.company_id).all()
    return {
        "ok": True,
        "format": "kanha_books_v1",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "ledgers": [{"code": a.code, "name": a.name, "type": a.account_type} for a in coa],
        "vouchers": [_voucher_out(v) for v in vouchers],
        "note": "Kanha Books native pack — open in KanhaERP or hand to accountant",
    }


# ----- Market depth: cash/bank books, COA balances, cost centres, bank recon, GST -----


@router.get("/coa")
def books_coa(user: CurrentUser, db: DbDep) -> list[dict]:
    _ensure_voucher_columns(db)
    accounts = (
        db.query(Account)
        .filter(Account.company_id == user.company_id)
        .order_by(Account.code)
        .all()
    )
    leaf = [a for a in accounts if not a.is_group]
    bal: dict[int, float] = {a.id: 0.0 for a in leaf}
    for j in db.query(JournalEntry).filter(JournalEntry.company_id == user.company_id).all():
        for ln in j.lines or []:
            aid = ln.get("account_id")
            if aid in bal:
                bal[aid] += float(ln.get("debit") or 0) - float(ln.get("credit") or 0)
    return [
        {
            "id": a.id,
            "code": a.code,
            "name": a.name,
            "type": a.account_type,
            "is_group": bool(a.is_group),
            "parent_id": a.parent_id,
            "balance": round(bal.get(a.id, 0.0), 2),
        }
        for a in accounts
    ]


@router.post("/ledgers")
def create_ledger(body: LedgerIn, user: CurrentUser, db: DbDep) -> dict:
    """SBAC Create Ledger / Group — fresh entry, Kanha COA."""
    from app.core.deps import assert_perm

    assert_perm(user, db, "accounting.*", "books.*", "settings.*")
    _ensure_voucher_columns(db)
    code = (body.code or "").strip().upper()
    name = (body.name or "").strip()
    if not code or not name:
        raise HTTPException(400, "Code and name required")
    atype = (body.account_type or "expense").lower().strip()
    if atype not in ("asset", "liability", "equity", "income", "expense"):
        raise HTTPException(400, "account_type must be asset/liability/equity/income/expense")
    exists = (
        db.query(Account)
        .filter(Account.company_id == user.company_id, Account.code == code)
        .first()
    )
    if exists:
        raise HTTPException(400, f"Ledger code {code} already exists")
    parent_id = body.parent_id
    if not parent_id and body.parent_code:
        parent = (
            db.query(Account)
            .filter(Account.company_id == user.company_id, Account.code == body.parent_code.strip().upper())
            .first()
        )
        if parent:
            parent_id = parent.id
    if parent_id:
        parent = db.query(Account).filter(Account.id == parent_id, Account.company_id == user.company_id).first()
        if not parent:
            raise HTTPException(404, "Parent group not found")
    row = Account(
        company_id=user.company_id,
        code=code,
        name=name,
        account_type=atype,
        parent_id=parent_id,
        is_group=bool(body.is_group),
        custom={
            "opening_balance": body.opening_balance,
            "bal_type": body.bal_type or "Debit",
            "opening_date": body.opening_date or str(date.today()),
            "currency": body.currency or "Indian Rupee (INR)",
            "other_value_pct": body.other_value_pct,
            "other_value_status": body.other_value_status,
            "parent_code": body.parent_code,
            "bill_wise": list(body.bill_wise or []),
            "source": "kanha_ledger",
            "sbac_parity": "2026-08-02-live",
        },
    )
    db.add(row)
    db.flush()
    # Opening balance as opening journal (optional)
    open_amt = float(body.opening_balance or 0)
    if open_amt > 0 and not body.is_group:
        equity = (
            db.query(Account)
            .filter(Account.company_id == user.company_id, Account.code == "3100")
            .first()
        )
        if equity:
            bal_type = (body.bal_type or "Debit").lower()
            if bal_type.startswith("cr"):
                lines = [
                    {"account_id": equity.id, "account_code": equity.code, "debit": open_amt, "credit": 0},
                    {"account_id": row.id, "account_code": row.code, "debit": 0, "credit": open_amt},
                ]
            else:
                lines = [
                    {"account_id": row.id, "account_code": row.code, "debit": open_amt, "credit": 0},
                    {"account_id": equity.id, "account_code": equity.code, "debit": 0, "credit": open_amt},
                ]
            je = JournalEntry(
                company_id=user.company_id,
                number=next_number(db, user.company_id, JournalEntry, "OB"),
                entry_date=date.today(),
                narration=f"Opening balance · {row.code} {row.name}",
                lines=lines,
                status="posted",
                voucher_type="journal",
                party_name="",
                custom={"source": "kanha_opening_balance", "ledger": row.code},
            )
            db.add(je)
    audit(db, company_id=user.company_id, user_id=user.id, action="create", entity="ledger", entity_id=code)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "code": row.code,
        "name": row.name,
        "account_type": row.account_type,
        "is_group": row.is_group,
        "parent_id": row.parent_id,
        "custom": row.custom or {},
        "message": f"Ledger {row.code} created",
    }

def _book_for_code(user: CurrentUser, db: DbDep, code: str) -> dict:
    _ensure_voucher_columns(db)
    acc = (
        db.query(Account)
        .filter(Account.company_id == user.company_id, Account.code == code)
        .first()
    )
    if not acc:
        raise HTTPException(404, f"Account {code} missing — open Accounting once to seed COA")
    entries = []
    running = 0.0
    for j in (
        db.query(JournalEntry)
        .filter(JournalEntry.company_id == user.company_id)
        .order_by(JournalEntry.entry_date, JournalEntry.id)
        .all()
    ):
        for ln in j.lines or []:
            if ln.get("account_id") != acc.id and ln.get("account_code") != code:
                continue
            dr = float(ln.get("debit") or 0)
            cr = float(ln.get("credit") or 0)
            running += dr - cr
            entries.append(
                {
                    "date": j.entry_date.isoformat() if j.entry_date else None,
                    "voucher": j.number,
                    "type": getattr(j, "voucher_type", None) or "journal",
                    "party": getattr(j, "party_name", None) or "",
                    "narration": j.narration,
                    "debit": dr,
                    "credit": cr,
                    "balance": round(running, 2),
                }
            )
    return {"account": {"code": acc.code, "name": acc.name}, "entries": entries, "closing": round(running, 2)}


@router.get("/cash-book")
def cash_book(user: CurrentUser, db: DbDep) -> dict:
    return _book_for_code(user, db, "1100")


@router.get("/bank-book")
def bank_book(user: CurrentUser, db: DbDep) -> dict:
    return _book_for_code(user, db, "1200")


@router.get("/reports/pnl")
def books_pnl(user: CurrentUser, db: DbDep) -> dict:
    rows = books_trial(user, db)
    income = sum(r["credit"] for r in rows if str(r["code"]).startswith(("4",)))
    expense = sum(r["debit"] for r in rows if str(r["code"]).startswith(("5",)))
    return {
        "income": round(income, 2),
        "expense": round(expense, 2),
        "net_profit": round(income - expense, 2),
    }


@router.get("/reports/balance-sheet")
def books_balance_sheet(user: CurrentUser, db: DbDep) -> dict:
    coa = books_coa(user, db)
    assets = [a for a in coa if a["type"] == "asset"]
    liabilities = [a for a in coa if a["type"] in ("liability", "equity")]
    return {
        "assets": assets,
        "liabilities": liabilities,
        "assets_total": round(sum(max(0, a["balance"]) for a in assets), 2),
        "liabilities_total": round(sum(abs(min(0, a["balance"])) + max(0, -a["balance"]) for a in liabilities), 2),
    }


@router.get("/reports/gstr3b")
def books_gstr3b(user: CurrentUser, db: DbDep) -> dict:
    """GSTR-3B style desk from live invoices / purchase invoices — not GSTN filed."""
    from app.models import Invoice, PurchaseInvoice, Vendor
    from app.services.ops_intelligence import company_gstin, gst_for_party

    cid = user.company_id
    co_gst = company_gstin(db, cid)
    outs = db.query(Invoice).filter(Invoice.company_id == cid).all()
    inns = db.query(PurchaseInvoice).filter(PurchaseInvoice.company_id == cid).all()
    out_taxable = out_cgst = out_sgst = out_igst = 0.0
    for i in outs:
        sign = -1 if (i.invoice_type or "sales") == "credit" else 1
        from app.models import Customer

        cust = db.get(Customer, i.customer_id) if i.customer_id else None
        split = gst_for_party(i.subtotal, 18, company_gstin=co_gst, party_gstin=cust.gstin if cust else None)
        out_taxable += sign * float(i.subtotal or 0)
        out_cgst += sign * split["cgst"]
        out_sgst += sign * split["sgst"]
        out_igst += sign * split["igst"]
    in_taxable = in_cgst = in_sgst = in_igst = 0.0
    rcm_taxable = rcm_cgst = rcm_sgst = rcm_igst = 0.0
    rcm_docs = 0
    for i in inns:
        vend = db.get(Vendor, i.vendor_id) if i.vendor_id else None
        split = gst_for_party(i.subtotal, 18, company_gstin=co_gst, party_gstin=vend.gstin if vend else None)
        in_taxable += float(i.subtotal or 0)
        in_cgst += split["cgst"]
        in_sgst += split["sgst"]
        in_igst += split["igst"]
        if getattr(i, "rcm", False):
            rcm_docs += 1
            rcm_taxable += float(i.subtotal or 0)
            rcm_cgst += split["cgst"]
            rcm_sgst += split["sgst"]
            rcm_igst += split["igst"]
    out_tax = round(out_cgst + out_sgst + out_igst, 2)
    in_tax = round(in_cgst + in_sgst + in_igst, 2)
    rcm_tax = round(rcm_cgst + rcm_sgst + rcm_igst, 2)
    # RCM: self-assessed GST is payable (like outward) while same amount stays in ITC
    return {
        "ok": True,
        "period": date.today().strftime("%Y-%m"),
        "watermark": "KANHA DESK — not filed on GSTN",
        "outward": {
            "taxable": round(out_taxable, 2),
            "cgst": round(out_cgst, 2),
            "sgst": round(out_sgst, 2),
            "igst": round(out_igst, 2),
            "total_tax": out_tax,
            "docs": len(outs),
        },
        "inward_itc": {
            "taxable": round(in_taxable, 2),
            "cgst": round(in_cgst, 2),
            "sgst": round(in_sgst, 2),
            "igst": round(in_igst, 2),
            "total_tax": in_tax,
            "docs": len(inns),
        },
        "rcm": {
            "taxable": round(rcm_taxable, 2),
            "cgst": round(rcm_cgst, 2),
            "sgst": round(rcm_sgst, 2),
            "igst": round(rcm_igst, 2),
            "total_tax": rcm_tax,
            "docs": rcm_docs,
            "note": "Reverse charge — liability + matching ITC (net cash ≈ 0 if full credit)",
        },
        "net_payable": round(out_tax + rcm_tax - in_tax, 2),
        "note": "CGST/SGST vs IGST from GSTIN state · net = output + RCM − ITC",
    }


@router.get("/reports/gstr1")
def books_gstr1(user: CurrentUser, db: DbDep) -> dict:
    """GSTR-1 style outward supply JSON (local export — not GSTN upload)."""
    from app.models import Customer, Invoice
    from app.services.ops_intelligence import company_gstin, gst_for_party

    cid = user.company_id
    co_gst = company_gstin(db, cid)
    rows = []
    for inv in db.query(Invoice).filter(Invoice.company_id == cid).order_by(Invoice.id).all():
        if (inv.invoice_type or "sales") == "credit":
            continue
        cust = db.get(Customer, inv.customer_id) if inv.customer_id else None
        split = gst_for_party(inv.subtotal, 18, company_gstin=co_gst, party_gstin=cust.gstin if cust else None)
        rows.append(
            {
                "inum": inv.number,
                "idt": inv.invoice_date.isoformat() if inv.invoice_date else None,
                "ctin": cust.gstin if cust else "",
                "party": cust.name if cust else "",
                "val": round(float(inv.total or 0), 2),
                "txval": round(float(inv.subtotal or 0), 2),
                "rt": 18,
                "cgst": split["cgst"],
                "sgst": split["sgst"],
                "igst": split["igst"],
                "intra_state": split["intra_state"],
            }
        )
    return {
        "ok": True,
        "period": date.today().strftime("%Y-%m"),
        "watermark": "KANHA DESK GSTR-1 JSON — not uploaded to GSTN",
        "b2b": rows,
        "count": len(rows),
        "note": "Download/copy this pack for CA · live filing needs GSP",
    }


# Cost centres
class CostCentreIn(BaseModel):
    code: str
    name: str


@router.get("/cost-centres")
def list_cost_centres(user: CurrentUser, db: DbDep) -> list[dict]:
    from app.models import CostCentre

    rows = db.query(CostCentre).filter(CostCentre.company_id == user.company_id, CostCentre.active == True).all()  # noqa: E712
    if not rows:
        # seed defaults once
        for code, name in (("HO", "Head Office"), ("PLANT", "Plant / Works"), ("SALES", "Sales")):
            db.add(CostCentre(company_id=user.company_id, code=code, name=name))
        db.commit()
        rows = db.query(CostCentre).filter(CostCentre.company_id == user.company_id).all()
    return [{"id": r.id, "code": r.code, "name": r.name} for r in rows]


@router.post("/cost-centres")
def create_cost_centre(body: CostCentreIn, user: CurrentUser, db: DbDep) -> dict:
    from app.models import CostCentre

    row = CostCentre(company_id=user.company_id, code=body.code.strip().upper(), name=body.name.strip())
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"ok": True, "id": row.id, "code": row.code, "name": row.name}


# Bank reconciliation
class BankReconIn(BaseModel):
    statement_date: date | None = None
    description: str = ""
    amount: float
    notes: str = ""


@router.get("/bank-recon")
def list_bank_recon(user: CurrentUser, db: DbDep) -> dict:
    from app.models import BankReconItem

    rows = (
        db.query(BankReconItem)
        .filter(BankReconItem.company_id == user.company_id)
        .order_by(BankReconItem.id.desc())
        .limit(100)
        .all()
    )
    open_amt = sum(float(r.amount) for r in rows if r.status == "open")
    matched = sum(1 for r in rows if r.status == "matched")
    return {
        "items": [
            {
                "id": r.id,
                "statement_date": r.statement_date.isoformat() if r.statement_date else None,
                "description": r.description,
                "amount": r.amount,
                "status": r.status,
                "matched_voucher_id": r.matched_voucher_id,
                "notes": r.notes,
            }
            for r in rows
        ],
        "open_count": sum(1 for r in rows if r.status == "open"),
        "matched_count": matched,
        "open_amount": round(open_amt, 2),
        "books_bank": bank_book(user, db).get("closing", 0),
    }


@router.post("/bank-recon")
def add_bank_recon(body: BankReconIn, user: CurrentUser, db: DbDep) -> dict:
    from app.models import BankReconItem

    row = BankReconItem(
        company_id=user.company_id,
        statement_date=body.statement_date or date.today(),
        description=body.description,
        amount=float(body.amount),
        notes=body.notes,
        status="open",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"ok": True, "id": row.id}


class BankReconImportIn(BaseModel):
    """CSV text: date,description,amount  (header optional)."""
    csv_text: str
    auto_match: bool = False


@router.post("/bank-recon/import")
def import_bank_recon(body: BankReconImportIn, user: CurrentUser, db: DbDep) -> dict:
    """Import bank statement CSV into recon desk."""
    import csv
    import io
    from datetime import datetime

    from app.models import BankReconItem

    raw = (body.csv_text or "").strip()
    if not raw:
        raise HTTPException(400, "csv_text required")
    # Accept pasted TSV/CSV
    sample = raw.splitlines()[0]
    dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    reader = csv.reader(io.StringIO(raw), dialect)
    rows_in = list(reader)
    if not rows_in:
        raise HTTPException(400, "Empty CSV")
    # Detect header
    start = 0
    first = [c.strip().lower() for c in rows_in[0]]
    if any(x in first for x in ("date", "description", "amount", "narration", "particulars")):
        start = 1
        # map columns
        idx = {h: i for i, h in enumerate(first)}
        di = idx.get("date", 0)
        desci = idx.get("description") or idx.get("narration") or idx.get("particulars") or 1
        amti = idx.get("amount", 2)
    else:
        di, desci, amti = 0, 1, 2

    created = 0
    skipped = 0
    for cols in rows_in[start:]:
        if len(cols) <= max(di, desci, amti):
            skipped += 1
            continue
        draw = (cols[di] or "").strip()
        desc = (cols[desci] or "").strip()
        amt_raw = (cols[amti] or "").strip().replace(",", "")
        try:
            amt = float(amt_raw)
        except ValueError:
            skipped += 1
            continue
        sd = date.today()
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d-%b-%Y", "%d/%m/%y"):
            try:
                sd = datetime.strptime(draw, fmt).date()
                break
            except ValueError:
                continue
        # Dedupe same day+desc+amount open
        exists = (
            db.query(BankReconItem)
            .filter(
                BankReconItem.company_id == user.company_id,
                BankReconItem.description == desc,
                BankReconItem.amount == amt,
                BankReconItem.statement_date == sd,
            )
            .first()
        )
        if exists:
            skipped += 1
            continue
        db.add(
            BankReconItem(
                company_id=user.company_id,
                statement_date=sd,
                description=desc or "Bank statement",
                amount=amt,
                notes="CSV import",
                status="open",
            )
        )
        created += 1
    db.commit()
    return {
        "ok": True,
        "created": created,
        "skipped": skipped,
        "auto_matched": 0,
        "message": f"Imported {created} statement lines · open Auto-match on each row if needed",
        "hint": "auto_match flag reserved — use Match buttons for control",
    }


@router.post("/bank-recon/{item_id}/match")
def match_bank_recon(item_id: int, user: CurrentUser, db: DbDep, voucher_id: int | None = None) -> dict:
    from app.models import BankReconItem

    row = db.get(BankReconItem, item_id)
    if not row or row.company_id != user.company_id:
        raise HTTPException(404, "Recon line not found")
    # Auto-match nearest bank book amount if voucher_id omitted
    if not voucher_id:
        target = abs(float(row.amount))
        bank = _coa_map(db, user.company_id).get("1200")
        best = None
        best_diff = 1e18
        for j in db.query(JournalEntry).filter(JournalEntry.company_id == user.company_id).all():
            for ln in j.lines or []:
                if bank and ln.get("account_id") == bank.id:
                    mov = abs(float(ln.get("debit") or 0) - float(ln.get("credit") or 0))
                    diff = abs(mov - target)
                    if diff < best_diff:
                        best_diff = diff
                        best = j.id
        voucher_id = best
    row.matched_voucher_id = voucher_id
    row.status = "matched" if voucher_id else "ignored"
    db.commit()
    return {"ok": True, "status": row.status, "matched_voucher_id": row.matched_voucher_id}


@router.post("/vouchers/{vid}/reverse")
def reverse_voucher(vid: int, user: CurrentUser, db: DbDep) -> dict:
    """Post reversing voucher — never deletes (Core Control friendly)."""
    from app.services.period_lock import assert_period_open

    _ensure_voucher_columns(db)
    src = db.get(JournalEntry, vid)
    if not src or src.company_id != user.company_id:
        raise HTTPException(404, "Voucher not found")
    if (src.status or "") == "reversed":
        raise HTTPException(400, "Already reversed")
    assert_period_open(db, user.company_id, date.today())
    rev_lines = []
    for ln in src.lines or []:
        rev_lines.append(
            {
                "account_id": ln.get("account_id"),
                "account_code": ln.get("account_code"),
                "debit": float(ln.get("credit") or 0),
                "credit": float(ln.get("debit") or 0),
            }
        )
    _balance_check(rev_lines)
    vtype = getattr(src, "voucher_type", None) or "journal"
    prefix = VOUCHER_PREFIX.get(vtype, "JV")
    row = JournalEntry(
        company_id=user.company_id,
        number=next_number(db, user.company_id, JournalEntry, prefix),
        entry_date=date.today(),
        narration=f"REVERSAL of {src.number} — {src.narration or ''}",
        lines=rev_lines,
        status="posted",
        voucher_type=vtype,
        party_name=getattr(src, "party_name", None) or "",
    )
    db.add(row)
    src.status = "reversed"
    audit(db, company_id=user.company_id, user_id=user.id, action="books_reverse", entity="journal", entity_id=src.number)
    db.commit()
    db.refresh(row)
    return {"ok": True, "reversed": src.number, "reversal": row.number, "id": row.id}


@router.post("/vouchers/{vid}/submit-approval")
def submit_voucher_approval(vid: int, user: CurrentUser, db: DbDep) -> dict:
    """Send voucher into hierarchy ApprovalEngine (SBAC Voucher Approval)."""
    from app.services.hierarchy_approvals import submit_approval

    _ensure_voucher_columns(db)
    row = db.get(JournalEntry, vid)
    if not row or row.company_id != user.company_id:
        raise HTTPException(404, "Voucher not found")
    if (row.status or "") in ("reversed", "deleted", "rejected"):
        raise HTTPException(400, f"Cannot approve voucher in status {row.status}")
    amt = sum(float(ln.get("debit") or 0) for ln in (row.lines or []))
    try:
        appr = submit_approval(
            db,
            company_id=user.company_id,
            requester=user,
            module="voucher",
            entity_type="journal",
            entity_id=str(row.id),
            title=f"Voucher {row.number}",
            amount=amt,
        )
    except Exception as e:
        # If no hierarchy configured, mark pending locally
        custom = dict(getattr(row, "custom", None) or {})
        custom["approval_status"] = "pending"
        custom["approval_note"] = str(e)[:200]
        row.custom = custom
        row.status = "pending_approval"
        db.commit()
        return {"ok": True, "status": "pending_approval", "message": "Marked pending (configure hierarchy for multi-level)"}
    custom = dict(getattr(row, "custom", None) or {})
    custom["approval_status"] = "pending"
    custom["approval_id"] = getattr(appr, "id", None) if not isinstance(appr, dict) else appr.get("id")
    row.custom = custom
    row.status = "pending_approval"
    db.commit()
    return {"ok": True, "status": "pending_approval", "message": f"{row.number} sent for approval"}


@router.post("/vouchers/{vid}/decide")
def decide_voucher(vid: int, user: CurrentUser, db: DbDep, status: str = "approved") -> dict:
    """Approve or reject pending voucher."""
    from app.core.deps import assert_perm

    assert_perm(user, db, "accounting.*", "approvals.*", "settings.*")
    if status not in ("approved", "rejected"):
        raise HTTPException(400, "status must be approved or rejected")
    row = db.get(JournalEntry, vid)
    if not row or row.company_id != user.company_id:
        raise HTTPException(404, "Voucher not found")
    custom = dict(getattr(row, "custom", None) or {})
    custom["approval_status"] = status
    custom["decided_by"] = user.email or str(user.id)
    row.custom = custom
    row.status = "posted" if status == "approved" else "rejected"
    audit(db, company_id=user.company_id, user_id=user.id, action=f"voucher_{status}", entity="journal", entity_id=row.number)
    db.commit()
    return {"ok": True, "status": row.status, "number": row.number}


@router.delete("/vouchers/{vid}")
def delete_voucher(vid: int, user: CurrentUser, db: DbDep) -> dict:
    """SBAC Delete voucher — soft delete (prefer Reverse for posted books trail)."""
    from app.core.deps import assert_perm

    assert_perm(user, db, "accounting.*", "settings.*")
    row = db.get(JournalEntry, vid)
    if not row or row.company_id != user.company_id:
        raise HTTPException(404, "Voucher not found")
    if (row.status or "") == "posted":
        # Force reverse path for posted — keep books honest
        return reverse_voucher(vid, user, db)
    row.status = "deleted"
    custom = dict(getattr(row, "custom", None) or {})
    custom["deleted_at"] = date.today().isoformat()
    row.custom = custom
    audit(db, company_id=user.company_id, user_id=user.id, action="books_delete", entity="journal", entity_id=row.number)
    db.commit()
    return {"ok": True, "number": row.number, "status": "deleted", "message": f"{row.number} deleted"}
