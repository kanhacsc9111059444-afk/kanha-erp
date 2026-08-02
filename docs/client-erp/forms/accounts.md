# Form: Accounts (Ledger + Vouchers) — field-level parity

**Sources (live 2026-08-02):**
- Create Ledger: https://erp.sbacindia.in/Account/LedgerSub.aspx  
- Payment (family): https://erp.sbacindia.in/Account/Voucherdenominations.aspx?Vtype=Payment&Etype=Cr  
- Same page family: Receipt · Contra · Journal · Credit Note · Debit Note  

**Kanha UI:** `#/books` (+ `#/accounting` reports / period lock)  
**Status:** ✅ Complete — live scan 2026-08-02

## Locked
- Fresh entry only — no SBAC ledger/voucher import  
- Same fields + same working (Create Ledger, post vouchers, day book / TB / P&L / BS)  
- Kanha design · Books desk  

## Create Ledger (`LedgerSub.aspx`)
| Field | Control / notes |
|-------|-----------------|
| Ledger Name | `txtLgName` |
| Under Group (Parent) | `ddlParent` → Kanha `parent_code` |
| Opening Date | date |
| Opening Balance | `txtOpBal` |
| Bal Type | `ddlBalType` Debit / Credit |
| Currency | `ddlCurrency` |
| Other Value % | |
| Other Value Status | Yes / No |
| Bill-wise Add | SBAC grid — Kanha extras later |
| Code · Type · Is Group | Kanha COA (asset/liability/equity/income/expense) |
| Submit / Reset / Search | |

Opening balance > 0 → Kanha posts OB journal vs equity `3100`.

## Voucher (`Voucherdenominations.aspx`)
| Field | Notes |
|-------|--------|
| Voucher Type | Payment / Receipt / Contra / Journal / CN / DN |
| Voucher No | Auto |
| Voucher Date | |
| Bill / On Account | `receipt_type` |
| Cost Centre | |
| Bank/Cash · Party accounts | from_account / to_account |
| Party Name | |
| Amount · Adjust Amount | |
| Currency · Exchange Rate · Convert Amount | |
| Cheque No · Cheque Date | |
| Sub Narration · Narration · Remarks | |
| ADD · Debit/Credit totals · Submit / Search / Print | |

Kanha posts balanced lines; extras in `journal_entries.custom`.

## Flow
```
Create Ledger/Group (+ opening OB)
  → Payment | Receipt | Contra | Journal | CN | DN
  → Day Book / Cash / Bank / Trial Balance / P&L / Balance Sheet
  → Party Outstanding (Buyer AR / Vendor AP) + bill-wise
```

## Kanha APIs
- `POST /api/books/ledgers` — parent, opening bal/DrCr, currency, other value → `accounts.custom`
- `POST /api/books/vouchers` — SBAC voucher extras → `journal_entries.custom`
- `GET /api/books/coa` · vouchers · daybook · cash-book · bank-book · trial-balance · pnl · balance-sheet
- `GET /api/outstanding/summary`

## Next
MIS / Tally deepen — next `ok`
