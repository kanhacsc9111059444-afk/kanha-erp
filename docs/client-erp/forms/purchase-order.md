# Form: Create Purchase Order — field-level parity

**Source:** https://erp.sbacindia.in/Purchase/PurchaseOrderNew.aspx  
**Breadcrumb:** Home / Purchase Management / PO Processing  
**Kanha UI:** `#/purchase` → + Purchase Order  
**Status:** ✅ Complete — live scan 2026-08-02

## Locked
- Fresh entry only — no SBAC PO / vendor data import  
- Same fields + same working (lines Add, Other/Tax AddTax, Terms, Party Details, Other Section)  
- Kanha design · Godown = warehouse mapping  

## Header
| Field | Control | Notes |
|-------|---------|-------|
| Series Type | `ddlseriestype` | Main / RFQ |
| Order_No * | `txtQuotationNo` | auto on Kanha |
| Order_Date * | `dtpQuotationDate_*` | |
| Party Type | `ddlPartyType` | Sundry Creditors / Sundry Debtors |
| Party Name | `txtpartyname` | lookup → Kanha vendor select |
| Freight Mode | `ddlfreightmode` | FOR / PAID / TO PAY |
| Narration | `txtNarrtion` | |
| Delivery Date | `delvrydate_*` | |

## Party Details (`chkparty`)
| Field | Control |
|-------|---------|
| Delivery Branch | `ddlDeliveryBranch` |
| Booked Station | `txtBookedStation` |
| Ship Branch | `ddlshipbranch` |
| Ship / Shipping Address | `txtshipaddress` |

## Other Section (`chkothersection`)
State · Agent · Payment Mode · Currency · Transporter Mode · Transporter · Godown · Supplier Contact · Delivery Per · Delivery Contact No · Ref No · Behalf Of · Order Duration · Declaration

## Item Details (`chkitem`)
Classification · Sub Classification · Category · Item Code · Item · Qty · MRP · Disc value · CD% · Add Tax% · Unit · Make · Model · Specification · Item Specification · Inspection Instr · Convert · **Add** / Reset

## Other Item Details (`chkotheritem`)
Discount · Add Tax Amt · Sale Amt · Description · Remarks · Due Date · Discount Type · Item Tax

## Totals
Total Qty · Total · Round Off · Grand Total

## Other / Tax (`chkother`) — multi via AddTax
Nature (Add/Less) · Tax Type · Value % · Tax Amount · **AddTax**

## Term And Condition (`CheckTerm`)
Terms rich text · Save / Reset

## Actions
Save · Reset

## Downstream flow
Purchase Order → MRN/GRN (bal qty) → Purchase Invoice → Vendor Payment

## Kanha APIs
- `POST /api/purchase/orders` · `GET /api/purchase/orders` · `GET /api/purchase/orders/pending-grn`
- Lines + `charges[]` + header extras in `custom` (`series_type`, `freight_mode`, `narration`, Party Details, Other Section, `terms`, `round_off`, …)

## Next
MRN ✅ · Next: Purchase Invoice deep fields
