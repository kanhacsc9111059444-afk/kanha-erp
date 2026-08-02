# Form: Create Sales Order — field-level parity

**Source:** https://erp.sbacindia.in/Balaji/CreateNewSaleOrder.aspx  
**Breadcrumb:** Home / Sales Management / Create Sales Orders  
**Kanha UI:** `#/sales` → + Sales Order  
**Status:** ✅ Complete — live scan 2026-08-02

## Locked
- Fresh entry only — no SBAC order import  
- Same fields + same working (lines Add, Other Values Add, Terms, Other Details)  
- Kanha design · Godown kept as Kanha warehouse mapping  

## Header
| Field | Control | Notes |
|-------|---------|-------|
| Entry Type | `ddlentrytype` | Lead / Quotation / Order / Direct Entry Type |
| Series Type | `ddlseriestype` | Main / Export |
| Order No | `txtorderno` | auto |
| Order Date | `dtpentrydate_*` | |
| Delivery Date | `dtpdeliverydate_*` | |
| Quotation No / Ref | `txtquotation` | |
| Party Name | `txtpartyname` | lookup → Kanha select |
| File attach | `fileattch` + Upload | Kanha: attachment note |
| Customer Order No | `txtcutomerorderrefno` | |
| Delivery Type | `ddldeliverytype` | CIF / PAID / TO PAY / CC variants |
| Transport Name | `ddltransportname` | |

## Party Details (`chkparty`)
Bill To Address · Ship To Address · Mobile No · GST No · Order Remarks

## Item Details
| Field | Control |
|-------|---------|
| Item name/Code | `ddlitem` |
| Quantity | `txtqty` |
| MRP | `txtrate` (rate box used as MRP on SBAC UI) |
| GST% | `txtgst` |
| Sale Rate | `txtsalerate` |
| Billing Unit | `ddlunit` |
| Discount (%) | `txtdiscount` |
| Convert Value | `txtconvertvalue` |
| Special Rate | `txtspecialrate` |
| Item Description | `txtitemdescreption` |
| Add | `btnadd` |

Totals: Total Qty · Total Amount · Grand Total

## Other Values (`chkothervalues`) — multi via Add
Nature (Less/Add) · Other Type (Discount/Freight/Insurance/IGST…) · Tax Percent (%) · Amount · Other Tax · Add

## Term And Condition (`CheckTerm`)
Rich description · Add term · Terms text (default: *100% Payment Against Proforma Invoice.*)

## Other Details
Executive · CC · Exemption (Yes/No) · AMC Status (Active/Inactive) · Save

## Actions
Submit · Reset

## Downstream flow
Sales Order → Delivery Challan → Sales Invoice → Payment / Outstanding

## Kanha APIs
- `POST /api/sales/orders` · `GET /api/sales/orders`
- Lines + `charges[]` + header extras in `custom` (`terms`, `executive`, `cc`, `exemption`, `amc_status`, `quotation_ref`, …)

## Next
Sales Invoice deep fields — live expand + one-pass implement
