# KanhaERP Enterprise V2 — Living Roadmap

**Status:** Pending SBAC parity sprint in progress (Wave 0–1).  
**Live:** https://kanha-erp.onrender.com  
**Compare:** `docs/client-erp/SBAC_VS_KANHA_COMPARE.md`

## Architecture (do not redo)

| Layer | Purpose |
|-------|---------|
| FileService | `POST /api/files/upload` — Item/Party/SO/HR/Brand logo |
| LookupMaster | `GET/POST /api/masters/{type}` — brand, group, category, unit, transport, agent, country |
| White-label | `GET/PUT /api/brand` + logo file upload |
| Approvals | existing hierarchy engine |
| Print | `GET /api/print/{type}/{id}` |

SaaS path later: same `company_id` filter + tenant slug; schema already company-scoped.

## Wave 0–1 (parity) — this sprint

- [x] FileService + LookupMaster + seed  
- [x] `#/masters` UI + inline + Add on forms  
- [x] Party Transport/Agent masters + Reset  
- [x] Item image upload + master dropdowns + country list  
- [x] DC Edit/Search + Print  
- [x] Cash Invoice + Sales Return (credit note) + E-Invoice per invoice  
- [x] Leave balance EL/CL grid  
- [x] HR photo/sign/doc uploads  
- [x] White-label logo upload  
- [x] Print pack API  

## Wave 2 (future — design only until requested)

1. BOM + Production Order + WIP + Batch + Costing  
2. Quality  
3. Maintenance  
4. Logistics deepen  
5. Advanced CRM funnel  
6. Assets / DMS / Notifications / Role dashboards  
7. SBAC manufacturing registers  
8. Reports + AI deepen  
9. Mobile / Public API / Security / Deploy  

## Rule

Complete pending parity first. Expand on FileService + Masters + Approvals + Print — never invent parallel upload/master systems.
