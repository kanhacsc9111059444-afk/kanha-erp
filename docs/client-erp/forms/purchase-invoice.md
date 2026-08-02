# Form: Purchase Invoice — field-level parity

**Sources (live):**
- Create MRN (multi PO): https://erp.sbacindia.in/Balaji/CreateMaterialReceiptwithmultiplepo.aspx?mid=1736  
- Create MRN (CASH) / Direct: https://erp.sbacindia.in/Balaji/CreateMaterialReceiptCash.aspx?mid=1736  
- Purchase Invoice For Po: https://erp.sbacindia.in/Purchase/CreateMaterialReceipt.aspx?mid=1747 — **SBAC server error** on load (varchar→int on `SBAC/R/MR/573`); fields taken from Material Receipt family (same controls)

**Kanha UI:**
- `#/purchase` → Pending MRN → **Create PI** / **PI (RCM)**
- `#/purchase` → **+ Direct PI**

**Status:** ✅ Complete — live scan 2026-08-02 (Cash + Multi-PO Material Receipt; PI-for-PO page broken on client ERP)

## Locked
- Fresh entry only — no SBAC bill import  
- Same fields + same working (AddTax, Payment, JV, RCM)  
- Kanha design  

## Header
| Field | Control | Notes |
|-------|---------|-------|
| Type | `ddlType` | Direct / PO |
| PO No + Search | `txtPono` · `btnsrch` | Kanha: from pending MRN |
| Series Type | `ddlseriestype` | Main |
| Receipt / Invoice No | `txtReceiptNo` | auto |
| Receipt / Invoice Date | `dtpReceiptDate_*` | |
| Party Name | `txtpartyname` | vendor |
| Bill No | `txtBillno` | |
| Bill Date | `dtpbilldate_*` | |
| Godown | `ddlgodown` | Direct PI stock in |
| Freight Mode | `ddlfreightmode` | FOR / PAID / TO PAY |
| QC Status | `ddlqcstatus` | No / Yes |
| Received By | `txtreceivedby` | |
| Invoice Remarks | `txtinvoiceremarks` | |
| RCM | Kanha | Yes/No · AP = taxable when Yes |

## Other Details
Lot No · GR No · GR Date · Total Wt · Description

## Item Details
- **From MRN:** lines locked from goods receipt (qty/rate/GST)  
- **Direct / Cash:** Item · Qty · Rate · Discount · GST% · Godown · Make · Unit · Convert · Remarks · Batch · **Add**

## Other / Tax (`chkother`) — multi via AddTax
Nature (Add/Less) · Tax Type · Value % · Tax Amount · **AddTax**  
Totals: Total Qty · Total Amount · Grand Total · Round Off

## Payment Method (`chkpayment`) — optional
Mode · Amount · Transaction No · Date · Narration · Add · Total Payable

## Bill Adjustment
Advance Adjust · Adjust Amount · Bill Adjusted

## Journal Voucher (`chkjv`) — optional
Account · Debit/Credit · Amount · Txn No · Date · Narration · Add

## Actions
Save · Reset · Edit/Search

## Downstream flow
MRN → **Purchase Invoice** → Vendor Payment  
(or Direct PI → stock + books → Vendor Payment)

## Kanha APIs
- `GET /api/purchase/grn/pending-invoice`
- `POST /api/purchase/flow/grn-to-invoice/{grn_id}` — body + `custom` on PurchaseInvoice
- `POST /api/purchase/invoices/direct` — Direct/Cash path + `custom`
- Model: `PurchaseInvoice.custom` (+ startup ALTER)

## Next
Store ✅ · Next: Accounts deep fields
