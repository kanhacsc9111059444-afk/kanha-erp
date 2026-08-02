# Form: Store (Issue / Receive / Physical / Godown Transfer) — field-level parity

**Sources (live 2026-08-02):**
- Issue Items: https://erp.sbacindia.in/Balaji/IssueItemBalaji.aspx  
- Receive Items: https://erp.sbacindia.in/Balaji/ReceiveItemBalaji.aspx  
- Physical Stock: https://erp.sbacindia.in/Store/PhysicalStock.aspx  
- Related: Pending Indent For Issue · Physical Stock Approval · Godown Master  

**Kanha UI:** `#/store`  
**Status:** ✅ Complete — live scan 2026-08-02

## Locked
- Fresh entry only — no SBAC stock import  
- Same fields + same working (Add lines, Save, Physical draft → Approve)  
- Kanha design · Godown = warehouse  

## Material Issue (`IssueItemBalaji.aspx`)
| Field | Control |
|-------|---------|
| Issue No | `txtissue` (auto) |
| Issue Date | `dtpissue_*` |
| Issue Type | `ddltype` |
| Bill No | `txtbillno` |
| Party | `ddlpartytype` |
| Godown | `ddlgodown` |
| Issued By | `txtissuedby` |
| Remarks | `txtremarks` |
| Item Issue Type | `ddlItemIssueType` — Consumable / Returnable |
| Item · Qty · Rate · Amt | + **Add** |
| Advance · Total Qty · Total Amt · Grand | |
| Save and Print · Edit/Search · Reset | |

Kanha also: Department · Purpose · Indent → Issue flow.

## Material Receive (`ReceiveItemBalaji.aspx`)
| Field | Control |
|-------|---------|
| Receive No | `txtreceive` (auto) |
| Received Date | `dtpreceive_*` |
| Receive Type | `ddltype` |
| Bill No · Party · Godown · Remarks | |
| Item · Qty · Thaan · Rate · Disc% · Amt · Disc Amt · Elongation · Gauge | + **Add** |
| Advance · GST Amt · Totals | |
| Save · Edit/Search · Reset | |

## Physical Stock (`PhysicalStock.aspx`)
| Field | Control |
|-------|---------|
| Physical Stock No * | `txtphysicalstockno` (auto) |
| Store Name * | `ddlStore` |
| Branch | `ddlBranch` |
| Date | `Dtpdate_*` |
| Store Keeper | `ddlStorekeeper` |
| Project Manager | `ddlProjectManager` |
| Item · Item Code · Unit · Current Stock · Stock Entry · Entry Unit · Physical Stock · Item Desc | + **Add** |
| Search · Save · Search/Edit | |

Kanha: draft → **Approve** applies variance (SBAC ApprovalMaster).

## Godown Transfer
From Godown · To Godown · multi-line qty · Notes (Kanha voucher; SBAC often via stock ops).

## Flow
```
Indent (approved) → Material Issue (stock out)
                 ↘ or Direct Material Issue

Material Receive (internal / return) → stock in
Physical Stock (draft) → Approve → variance adjust
Godown Transfer → from WH → to WH
```

## Kanha APIs
- `POST /api/store/issues` · `GET /api/store/indents/pending-issue` · `POST /api/store/flow/indent-to-issue/{id}`
- `POST /api/store/receives`
- `POST /api/store/physical` + `…/{id}/approve`
- `POST /api/store/godown-transfer`
- Header extras in `custom` (`issued_by`, `item_issue_type`, `bill_no`, `store_keeper`, …)

## Next
Accounts deepen (Ledger / Payment / Receipt / Journal) — ek `ok` pe ek form
