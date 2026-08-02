# Form: Create MRN (Material Receipt) — field-level parity

**Source:** https://erp.sbacindia.in/Balaji/CreateMaterialReceiptwithmultiplepo.aspx?mid=1736  
**Breadcrumb:** Home / Purchase Management / PO Processing · Material Receipt  
**Kanha UI:** `#/purchase` → Pending PO → **Create MRN**  
**Status:** ✅ Complete — live scan 2026-08-02

## Locked
- Fresh entry only — no SBAC MRN / stock import  
- Same fields + same working (receive qty from PO bal, Other/Tax AddTax, optional Payment + JV)  
- Kanha design · Godown = warehouse mapping  

## Related SBAC screens
| Screen | Path |
|--------|------|
| Create Mrn | `/Balaji/CreateMaterialReceiptwithmultiplepo.aspx` |
| Create MRN (CASH) | `/Balaji/CreateMaterialReceiptCash.aspx` |
| Edit MRN | `/SalesOrder/EditFrmEntry.aspx?type=MRN` |
| Purchase Invoice For Po | `/Purchase/CreateMaterialReceipt.aspx` (PI deepen — next) |

## Header
| Field | Control | Notes |
|-------|---------|-------|
| Type | `ddlType` | Direct / PO |
| PO No + Search | `txtPono` · `btnsrch` | Kanha: from pending PO |
| Series Type | `ddlseriestype` | Main |
| Receipt No | `txtReceiptNo` | auto |
| Receipt Date | `dtpReceiptDate_*` | |
| Party Name | `txtpartyname` | vendor from PO |
| Bill No | `txtBillno` | |
| Bill Date | `dtpbilldate_*` | |
| Godown | `ddlgodown` | |
| Freight Mode | `ddlfreightmode` | FOR / PAID / TO PAY |
| QC Status | `ddlqcstatus` | No / Yes |
| Received By | `txtreceivedby` | |
| Invoice Remarks | `txtinvoiceremarks` | |

## Other Details
Lot No · GR No · GR Date · Total Wt · Description · Order No · Trans Id · Process (merge)

## Item Details (from PO)
Bal Qty · **Receive Qty** · Godown · Batch/Lot · Packing · Rate · Disc% · Unit

## Other / Tax (`chkother`) — multi via AddTax
Nature (Add/Less) · Tax Type · Value % · Tax Amount · **AddTax**  
Totals: Total Qty · Total Amount · Grand Total

## Payment Method (`chkpayment`) — optional
Mode · Amount · Transaction No · Date · Narration · Add · Total Payable

## Bill Adjustment
Advance Adjust · Adjust Amount · Bill Adjusted

## Journal Voucher (`chkjv`) — optional
Account · Debit/Credit · Amount · Txn No · Date · Narration · Add

## Actions
Save · Reset · Edit/Search

## Downstream flow
PO → **MRN** (stock in) → Purchase Invoice → Vendor Payment

## Kanha APIs
- `GET /api/purchase/orders/pending-grn`
- `POST /api/purchase/flow/po-to-grn/{po_id}` — body: lines + header extras → `GoodsReceipt.custom`
- `GET /api/purchase/grn` · `GET /api/purchase/grn/pending-invoice`

## Next
Purchase Invoice ✅ · Next: Store deep fields
