# Form: MIS + Tally / ERP Bridges — field-level parity

**Sources (live 2026-08-02):**
- MIS Report: https://erp.sbacindia.in/MIS/FrmmisReport.aspx  
- Tally Parent Mapping: https://erp.sbacindia.in/Master/TallyErpparentmapping.aspx  
- Tally Error: https://erp.sbacindia.in/Salesorder/Tallyerror.aspx  
- Inactive Ledger: https://erp.sbacindia.in/Master/InactiveLedgerForTally.aspx  
- Inactive Item: https://erp.sbacindia.in/Master/InactiveItemForTally.aspx  
- Related: Sales Analysis · Party Outstanding · Map Tracking · Active Bill and Voucher · BIMISPANEL  

**Kanha UI:** `#/mis` · `#/bridges` · `#/bi` · `#/books`  
**Status:** ✅ Complete — live scan 2026-08-02

## Locked
- No client Tally/Marg DB import — fresh Kanha packs + flags only  
- Existing Tally export/import **kept**  
- Marg / Busy / Vyapar / Other alongside  
- Kanha design  

## MIS Report (`FrmmisReport.aspx`)
| Field | Control |
|-------|---------|
| View | `rdosummary` / `rdodetail` |
| Doc type radios | Lead · Quotation · Order · Dispatch · Challan · Invoice · PO · MRN · Purchase Invoice · Executive · Follow · Issue · Receive |
| Date kind · From · To | `ddldate` · `dtpFrom_*` · `dtpTo_*` |
| Vendor · Buyer · Executive | `txtvendor` · `txtbuyer` · `ddlexecutive` |
| Main group · Item code · Item | `ddlmaingroup` · `txtitemcode` · `txtitem` |
| Status | Pending / Running / Confirmed / Closed Won/Lost |
| Sale type | Cash / Tax |
| Export · Reset | |

Kanha `#/mis`: filter strip + Sales analysis · Party OS · Attendance · Stock ageing · ERP bridge desk.

## Tally Parent Mapping
| Field | Control |
|-------|---------|
| ERP Parent | `ddlerp` (Sundry Debtors, Bank Accounts, …) |
| Tally Name | `txttally` |
| Submit | `btnSubmit` |

Stored in company `settings_json.tally_sync.parent_mappings`.

## Tally Error
| Field | Control |
|-------|---------|
| From · To | `DTP_From_*` · `DTP_To_*` |
| Doc type | Contra · Journal · Payment · Purchase · Receipt · Sale |
| Search · Reset | |

Kanha: filter outbox/manual errors · log note.

## Inactive Ledger / Item
| Screen | Fields |
|--------|--------|
| Inactive Ledger | `txtpartyname` · Search → mark inactive for Tally |
| Inactive Item | `txtitem` · Search → mark inactive for Tally |

Flags in `tally_sync` (+ `Account`/`Product.custom.tally_inactive` when code/sku matches).

## ERP data bridges (`#/bridges`)
| Target | Format |
|--------|--------|
| **Tally** | `kanha_tally_pack_v1` (kept) |
| Marg / Busy / Vyapar / Other | pack + hook |

Also: Dual-mode channels · Outbox · Bridge Intelligence · Third-party hooks.

## Flow
```
MIS filters → charts / OS / attendance / stock
Kanha Books (native) OR Hybrid
  → Tally Parent map · Inactive ledger/item
  → Export pack (Tally/Marg/…) · Error queue search
  → Import buffer + hooks
```

## Kanha APIs
- `GET /api/mis/sales-summary` · outstanding · attendance report · stock-ageing  
- `GET /api/bridges` (includes `tally_sync`)  
- `GET /api/bridges/tally/sync`  
- `POST /api/bridges/tally/parent-mapping`  
- `POST /api/bridges/tally/inactive-ledgers` · `…/inactive-items`  
- `GET/POST /api/bridges/tally/errors`  
- `POST /api/bridges/tally/export` · `…/import` (unchanged)  
- `POST /api/bridges/erp/{target}/export`  

## Next
Field track complete.
