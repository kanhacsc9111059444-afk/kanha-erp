# Form: Delivery Challan — field-level parity

**Source A (list):** https://erp.sbacindia.in/SalesOrder/PendingSalesOrderForDeliveryChallan.aspx  
**Source B (create):** https://erp.sbacindia.in/Balaji/CreateNewDeliveryChallan.aspx?orderid=…  
**Kanha UI:** `#/sales` → Pending SO → **Create Challan**  
**Status:** ✅ Complete — live create form scan 2026-08-02

## Locked
- Fresh entry only — no SBAC challan import  
- Same flow: pending SO (bal qty) → Create Challan form → Save (stock out)  
- Kanha design  

## A) Pending Sales Order → Create Challan (list)
| Field | Notes |
|-------|-------|
| Order From / To Date | filter |
| Party Name | filter |
| Order No | filter |
| Search | |

**Grid:** Order No · Order Date · Party Name · Total Qty · Bal Qty · Total Amt · **Create Challan**

## B) Create Delivery Challan (from SO)
| Field | Control | Notes |
|-------|---------|-------|
| Series Type * | `ddlseriestype` | Main / Export |
| Challan No * | `txtchallanno` | auto |
| Challan Date * | `dtpchallandate_*` | |
| Party Name | `txtpartyname` | from SO |
| Transporter | `ddlTransporter` | |
| Godown | `ddlgodown` | |
| Remarks | `txtremarks` | |
| Delivery Boy | `ddldeliveryboy` | |
| Destination | `txtdestination` | |
| No of Cart | `txtnoofcart` | |
| Delivery Type | `ddldeliverytype` | CIF / PAID / TO PAY / CC |

### Export Details
Packing Charge · Pre-Carriage by · Place of Receipt by Pre-Carrier · Port of Discharge · Port of Loading · LUT/Bond No · Final Destination

### Item Details (`gvadditem`)
| Column |
|--------|
| ItemName |
| Balance Qty |
| Issued Qty |
| Godown |
| No Of Packing |
| SaleRate |
| Amount |
| Discount |
| Billing Unit |

Totals: Total Qty · Total Amt · Total Tax · Grand Total

### Term And Condition
`CheckTerm` + description editor

### Actions
Save · Reset · Edit/Search

## C) Edit Delivery Challan (list)
**URL:** `/SalesOrder/EditFrmEntry.aspx?type=Challan`  
Entry From/To Date · Party Name · Entry No · Search

## Downstream
Delivery Challan → Pending Challan → Sales Invoice

## Kanha APIs
- `GET /api/sales/orders/pending-challan`
- `POST /api/sales/flow/order-to-challan/{order_id}` — body: header + `lines[{product_id, qty, godown, no_of_packing}]`
- Storage: `Delivery.custom` (series, transporter, delivery boy, export, terms, …)

## Next
Purchase Invoice ✅ · Next: Store deep fields
