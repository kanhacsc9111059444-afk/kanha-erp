# Form: Sales Invoice — field-level parity

**Source A:** https://erp.sbacindia.in/Balaji/CreateNewSalesInvoice.aspx (Direct)  
**Source B:** Pending Challan → Invoice  
**Kanha UI:** `#/sales` → + Direct Invoice · Create Invoice (from challan)  
**Status:** ✅ Complete — live Direct Invoice scan 2026-08-02

## Locked
- Fresh entry only — no SBAC invoice import  
- Same fields + same working (lines Add, Other Values, Payment, Terms)  
- Kanha design  

## A) Direct Sales Invoice
| Field | Control | Notes |
|-------|---------|-------|
| Type | `ddlentrytype` | Direct / DeliveryChallan |
| Series Type | `ddlseriestype` | Main / Export |
| Invoice No | `txtinvoiceno` | auto |
| Invoice Date | `dtpinvoicedate_*` | |
| Party Name | `txtpartyname` | lookup |
| Godown | `ddlgodown` | |
| Invoice Remarks | `txtinvoiceremarks` | |
| Agent | `ddlagent` | |
| Transport | `ddltransport` | |
| No of Cartoon | `txtnoofcartoon` | |
| Delivery Type | `ddldeliverytype` | CIF / PAID / TO PAY / CC |
| Freight Mode | `ddlfreightmode` | FOR / PAID / TO PAY |
| E-way Bill No | `txtewaybillno` | |
| Invoice Type | `ddlinvoicetype` | Domestic / Export |
| GR No / GR Date | `txtgrno` / `dtpgrdate_*` | |
| Truck No | `txttruckno` | |
| Pay Mode | `ddlpaymode` | ADVANCE / CASH / NEFT / UPI… |
| Transaction Type | `ddltransactiontype` | Regular / Bill To-Ship To… |
| Transport Mode | `ddltransportmode` | Road / Rail / Air / Ship |
| E-way Bill Type | `ddlewaybilltype` | TransportId / Vehicle |
| Dispatch Place | `txtdispathplace` | |

### Party Details (`chkparty`)
Bill To · Ship To · Mobile No · GST No

### Item Details
Item · Qty · MRP · GST% · Godown · Sale Rate · Rate With Tax · Batch No · Billing Unit · Desc/Packing · Discount% · Convert Value · Add

### Other Values (`chkothervalues`)
Nature Less/Add · Other Type · Tax% · Amount · Other Tax · Add

### Payment (`chkpayment`)
Mode · Amount · Transaction No · Transaction Date · Narration · Add · Total Payable · Advance Adjust · JV Account / Debit-Credit / Amount

### Terms
Term And Condition · Add · Save / Reset

## B) Pending Challan → Invoice
**URL:** `/SalesOrder/PendingChallanForSalesInvoice.aspx`  
Grid: Challan No · Date · Party · Qty · Amt · **Create Invoice**  
Kanha opens header form (Series/Transport/E-way/Payment) then posts.

## Flow
```
Sales Order → Delivery Challan → Sales Invoice
            ↘ Direct Sales Invoice
```

## Kanha APIs
- `POST /api/sales/invoices/direct` — full DirectInvoiceIn + `custom` on Invoice
- `POST /api/sales/flow/delivery-to-invoice/{id}` — InvoiceFromChallanIn body
- `Invoice.custom` JSON (migrated on startup)

## Next
Purchase Invoice ✅ · Next: Store deep fields
