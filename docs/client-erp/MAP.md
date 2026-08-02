# SBAC Digital ERP — Module Map (from live home)

**Source:** https://erp.sbacindia.in/user/UserHome.aspx  
**Company:** SHRI BALAJI ALLOYS CORPORATION - SBAC RPR  
**Captured:** 2026-08-02 (read-only browser scan)  
**Status:** Home + full menu link inventory. Field-level forms = next pass (module by module).

---

## Build rules (locked with client owner)

| Rule | Meaning |
|------|---------|
| **No client data copy** | Unka party/item/invoice data import nahi. KanhaERP pe **fresh entry** |
| **Same logic** | Har module ka flow, fields, validations, approvals — client ERP jaisa |
| **Same features** | Unke saare menus/screens parity pe pehle |
| **Exact fields** | Jo field SBAC pe kaam karta hai — Kanha pe **same working** (ek-ek form deepen) |
| **Better extras** | Parity ke baad UX, AI, WhatsApp, mobile, speed — extra (alag layer) |
| **Our logic stays** | KanhaOS / trading / existing KanhaERP ideas bhi rahenge — merge, replace nahi |
| **Live ERP safe** | Unke server pe sirf padhna/samajhna — write/delete nahi |
| **Our design** | UI/UX, stack, KanhaOS concept — **humara**; unka look copy nahi |
| **Their everything** | Modules, fields, flows, rules — **pura lenge**, humare hisaab se fit |

**Goal line:** *SBAC Digital ERP ka poora kaam + rules → Kanha design/concept me. Empty DB. Extras + our logic on top.*

**Field-level track (active):** Party ✅ → … → MIS/Tally ✅ → Extras ✅ (Meta webhook · OCR · WhatsApp Login · store slots). Track complete.

---

## Top-level menus

1. Admin  
2. Master  
3. Marketing  
4. Order Module  
5. Sales  
6. Purchase  
7. Production  
8. Indents  
9. Accounts  
10. Store  
11. HR  
12. Visit  
13. Task  
14. MIS  
15. MIS Panel  
16. Service  
17. App Menu  
18. Tally  

Quick tiles on home: Admin, Marketing, Sales, Purchase, Accounts, Stock, Data Summary Report.

---

## Core business flow (how modules connect)

```
Lead (Marketing)
  → Sales Order
    → Delivery Challan
      → Sales Invoice / Cash Invoice / E-invoice
        → Receipt / Payment Followup / Outstanding

Indent → Purchase Requisition / RFQ → PO
  → MRN (Material Receipt)
    → Store (Issue / Receive / Physical Stock)
      → Production Challan / Job Work

Accounts: Ledger, Journal, Contra, Payment, Receipt, Credit/Debit Note
  → Day Book, Trial Balance, P&L, Balance Sheet
  → Tally sync (parent mapping, inactive ledger/item, errors)

HR: Employee, Leave, Attendance, Salary process/approval/slip, Loans
```

---

## Screens by module (name → page)

### Admin
| Screen | Path |
|--------|------|
| Create User | `/admin/CreateUser.aspx` |
| User Dashboard | `/User/UserDashboard.aspx` |
| Assign User Dashboard | `/Master/userwiseassigndashboard.aspx` |
| Create Profile | `/Admin/UserProfile.aspx` |
| Change Password | `/admin/UpdateUserPwd.aspx` |
| Site Access (rights) | `/admin/UserRights.aspx` |
| Create Branch | `/Master/BranchMaster.aspx` |
| Edit Company | `/website/Edit_Companydetails.aspx` |
| User Wise Approval | `/Admin/UserwiseApproval.aspx` |
| Admin Dashboard | `/Balaji/BalajiDashBoard.aspx` |
| Document Approval | `/Admin/ApprovalMaster.aspx` |
| Assign App Menu | `/Admin/AssignAppMenu.aspx` |
| Delete Form Entry | `/Admin/DocumentDeletion.aspx` |
| B2B Portal | `/Admin/B2BPortal.aspx` |
| Whatsapp Login | `/user/whatsappset.aspx` |
| Delete Sales Order | `/admin/SalesOrderFroCancelOrDelete.aspx` |
| Delete Delivery Challan | `/admin/DeliveryChallanForCancelOrDelete.aspx` |
| Cancel Sales Invoice | `/admin/SalesInvoiceForCancelOrDelete.aspx` |
| Voucher / Expense / PR Approvals | Account + Admin + Purchase approval pages |

### Master (masters A→Z)
| Screen | Path |
|--------|------|
| Party Master | `/Balaji/BalajiPartymaster.aspx` |
| Upload Party / Party Merge | Upload + Merge pages |
| Item Master | `/Master/ItemMasterConfig.aspx` |
| Merge Item | `/Balaji/Itemdetails.aspx` |
| Unit / Category / Main Group / Sub group | `/Master/*` |
| Godown Master | `/Master/GodownMaster.aspx` |
| Country / State / City / Area | geo masters |
| Employee Master / Edit Employee | `/Master/EmployeeMaster.aspx` |
| Vehicle / Holiday / SMTP / Template / Currency | masters |
| Discount / Party-wise rate / Supplier rate / MRP | pricing masters |
| Tally Erp Parent Mapping | `/Master/TallyErpparentmapping.aspx` |
| Back Date Entry | `/Master/BackDateEntry.aspx` |
| Alert Master / Configuration | alerts |

### Marketing
| Screen | Path |
|--------|------|
| Create Lead Source | `/marketting/LeadMaster.aspx` |
| Lead Entry | `/Balaji/BalajiLeadEntry.aspx` |
| Lead Management | `/Marketting/EditLeadEntryBalaji.aspx` |
| Lead Report | `/Marketting/LeadReport.aspx` |
| Pending Lead → Sales Order | `/Marketting/PendingLeadFor_SalesOrder.aspx` |
| Visit Planner / Management | Visit pages |
| Cost Center | `/marketting/CostCenter.aspx` |

### Sales / Order
| Screen | Path |
|--------|------|
| Create Sales Order | `/Balaji/CreateNewSaleOrder.aspx` |
| Edit Sales Order | `/SalesOrder/EditFrmEntry.aspx?type=SalesOrder` |
| SO → Delivery Challan | `/SalesOrder/PendingSalesOrderForDeliveryChallan.aspx` |
| Edit Delivery Challan | `/SalesOrder/EditFrmEntry.aspx?type=Challan` |
| Pending Challan → Invoice | `/salesorder/PendingChallanForSalesInvoice.aspx` |
| Direct Sales Invoice | `/Balaji/CreateNewSalesInvoice.aspx` |
| Edit Sales Invoice | `/SalesOrder/EditFrmEntry.aspx?type=SalesInvoice` |
| Cash Invoice create/edit | Cash invoice pages |
| Sales Return create/edit | return pages |
| Create E-invoice | `/Salesorder/CreateEinvoice.aspx` |
| Order / Payment Followup | Balaji followup pages |
| Sales Order Report / DSR | report pages |
| Commission process | agent + party commission |

### Purchase
| Screen | Path |
|--------|------|
| Create / Edit PO | PurchaseOrderNew + EditFrmEntry type=PO |
| Purchase Requisition (+ for PO) | Balaji + Purchase PR pages |
| RFQ rate / RFQ → PO | RFQ pages |
| Purchase Invoice for PO | `/Purchase/CreateMaterialReceipt.aspx` (live error 2026-08-02; use Material Receipt Cash / multi-PO fields) |
| Purchase Return | create/edit/delete |
| PO Report | `/Purchase/POReport.aspx` |

### Production / Indents / Store
| Screen | Path |
|--------|------|
| Create Indent / Approval / Pending | Tirupati + Purchase indent pages |
| Production Challan create/list | `/Eminent/*` |
| Job Work Order | SalesOrder job-work pages |
| Issue / Receive Items | Balaji issue/receive |
| Create / Edit MRN (+ cash) | `/Balaji/CreateMaterialReceiptwithmultiplepo.aspx` (+ Cash / EditFrmEntry) |
| Physical Stock + Approval | `/Store/*` |
| Stock Report / Register / Reconciliation | stock reports |

### Accounts
| Screen | Path |
|--------|------|
| Create Ledger / Group Master | `/Account/*` |
| Payment / Receipt / Journal / Contra | Voucherdenominations |
| Credit Note / Debit Note | Voucherdenominations |
| Day Book / Register / Trial Balance | rptDayBook |
| P&L / Balance Sheet | rptDayBook variants |
| Party outstanding (Buyer/Vendor/All) | tirAllpartyoutstanding |
| Payment Request flow (A3M) | Request → Process → Status |
| Voucher Approval / Delete | Account admin |

### HR
| Screen | Path |
|--------|------|
| Grade Pay / Leave / Salary heads | `/HR/*` |
| Leave Application + List | HR leave pages |
| Salary Confirmation / Approval / Slip / Report | Balaji + MIS |
| Attendance process | ProcessSalaryAttendance |
| Employee Loan entry + approval | HR loan pages |

### MIS / Dashboards
| Screen | Path |
|--------|------|
| MIS Report | `/MIS/FrmmisReport.aspx` |
| Sales Analysis / Party Outstanding / Attendance / Map | `/MIS/*` |
| Sales Pipeline | `/BIMISPANEL/SalesPipeline.aspx` |
| Accounts / Inventory / Overview dashboards | BIMISPANEL |
| Module MIS Panels | ReportPanel?module=… |

### Service / Tally
| Screen | Path |
|--------|------|
| Generate / Manage Complaint | Master complain pages |
| Tally Error | `/Salesorder/Tallyerror.aspx` |
| Active Bill and Voucher | `/SalesOrder/BillandVoucher.aspx` |
| Inactive Ledger/Item for Tally | Master inactive pages |

---

## KanhaERP build priority (parity first)

1. **Masters** — Party, Item ✅ (Unit/Godown basics already in Kanha)  
2. **Sales chain** — SO → Challan → Invoice ✅ (Return already existed)  
3. **Purchase chain** — Vendor → PO → MRN → PI ✅ (Indent/PR/RFQ later deepen)  
4. **Store** — Issue / Receive / Physical / Godown Transfer ✅  
5. **Accounts** — Ledger + vouchers + outstanding ✅ (`#/books`)  
6. **HR** — Employee + Leave + Salary + Loans ✅ (`#/hrms`)  
7. **MIS dashboards** + Tally bridge ✅ (`#/mis` + `#/bridges`) — Tally kept; Marg / Busy / Vyapar / Other ERP packs added  
8. **Extra features** ✅ (`#/extras`) — Ops Chase Pack · AI dock · WhatsApp · Automation · PWA

---

## Next scan steps (field-level)

Done (pass 1–8):
- [x] Party Master — full live expand (Employee/Address/Account/Company/Bank/Contact/Export) + Kanha one-pass
- [x] Item Master — full live sections (Other/Conversion/Spec/Class/Tax/Dimension/Stock/Rate/Country/Vendor/Packing) + Kanha one-pass
- [x] Create Sales Order — header + line + charges  
- [x] Delivery Challan — pending SO list + edit search  
- [x] Sales Invoice — direct invoice + payments/adjust  
- [x] Purchase chain — Vendor + PO + MRN + PI (process parity; deep SBAC field scan later)  
- [x] Store — Issue / Receive / Physical / Transfer  
- [x] Accounts — Ledger Master + voucher drawers + outstanding / BS  
- [x] HR — Employee Master + Leave + Attendance process + Salary confirm/approve/slip + Loans  
- [x] MIS desk + ERP data bridges (Tally kept · Marg/Busy/Vyapar/Other options)  
- [x] Extras — Ops Chase Pack + AI / WhatsApp / Automation / PWA hub  

Pending later (deepen):
- [x] Party Master — live exact fields + Add Address/Bank/Contact + GST Search (2026-08-02)
- [x] Item Master deep fields — live exact sections + Add Conversion/Vendor/Packing (2026-08-02)
- [x] Create Sales Order — live exact header/lines/Other Values/Terms/Other Details (2026-08-02)
- [x] Delivery Challan — live CreateNewDeliveryChallan form + pending filters (2026-08-02)
- [x] Sales Invoice — live Direct + Challan→Invoice forms (2026-08-02)
- [x] Purchase Order deep fields (live scan 2026-08-02)
- [x] MRN / Material Receipt deep fields (live scan 2026-08-02)
- [x] Purchase Invoice deep fields (live scan 2026-08-02; PI-for-PO page SBAC error — Cash/MRN form used)
- [x] Store deep fields (Issue / Receive / Physical — live scan 2026-08-02)
- [x] Accounts deep fields — LedgerSub + Voucherdenominations (live scan 2026-08-02)
- [x] HR deep fields — EmployeeMaster + Leave + Attendance + Loan + Salary Confirm (live scan 2026-08-02)
- [x] MIS / Tally deepen — FrmmisReport + Parent mapping + Inactive + Tally Error (live scan 2026-08-02)
- [x] Extras deepen — WhatsApp Login + Meta webhook + OCR demo + store slots (2026-08-02)
- [ ] Native store publish / cloud OCR vendor (optional go-live)  

**Note:** SBAC login session expire ho to expandable HTML re-verify next login; Kanha me sections already wired.  

Form docs: `docs/client-erp/forms/*.md`

---

## Notes

- Live ERP is ASP.NET WebForms (`*.aspx`) — KanhaERP will be new stack; we copy **logic & fields**, not their code.  
- Scan is **read-only**; do not save/delete on client ERP.  
- Full raw feature checklist: `_home_extract.txt` (217 permission/menu names).
