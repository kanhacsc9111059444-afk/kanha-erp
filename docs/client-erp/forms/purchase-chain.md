# Form: Purchase chain (PO → MRN → Purchase Invoice)

**Source menus (SBAC):** Create PO · Create MRN · Purchase Invoice For Po · Direct/Cash MRN patterns  
**Kanha UI:** `#/purchase` — our design; same process logic  

## Locked rules
- No client vendor/item/bill data import — fresh entry only  
- Kanha logo / look / stack  
- Fields + flow + bal-qty process = SBAC concept  

## Flow
```
Vendor Master → Purchase Order → MRN/GRN (bal qty) → Purchase Invoice → Vendor Payment
                              ↘ Direct Purchase Invoice (optional)
```

## Header fields (PO / Direct PI)
Deep PO fields: see **[purchase-order.md](./purchase-order.md)** (live scan ✅).

| Field | Notes |
|-------|--------|
| Vendor / Supplier | lookup |
| Godown | stock in location |
| Vendor Ref / Quotation No | text |
| Transport | text |
| Order / Invoice Date | date |
| Delivery Date | date |
| Bill To / Remarks | text |
| Item lines | Item, Qty, Rate, GST%, Billing unit |

## Pending PO → MRN
Deep MRN fields: see **[mrn.md](./mrn.md)** (live scan ✅).

| Column | Action |
|--------|--------|
| PO No, Date, Vendor, Total Qty, Bal Qty, Amt | **Create MRN** (stock in; partial bal supported) |

## Pending MRN → Purchase Invoice
Deep PI fields: see **[purchase-invoice.md](./purchase-invoice.md)** (live scan ✅).

| Column | Action |
|--------|--------|
| MRN No, Date, Vendor, Qty, Amt | **Create PI** / **PI (RCM)** |

## Kanha APIs
- `POST /api/purchase/vendors`
- `POST /api/purchase/orders`
- `GET /api/purchase/orders/pending-grn`
- `POST /api/purchase/flow/po-to-grn/{id}`
- `GET /api/purchase/grn/pending-invoice`
- `POST /api/purchase/flow/grn-to-invoice/{id}`
- `POST /api/purchase/invoices/direct`
- Legacy one-shot: `POST /api/purchase/orders/{id}/receive`
