# KanhaERP — Beyond HA: future ERP risks & what we do

Primary = **ERP data + continuity**. Employee “spy app” secondary / often unnecessary.

## Aapke scenarios — clear answer

| Situation | Unnecessary? | Better role |
|-----------|--------------|-------------|
| Note WhatsApp pe draft, send nahi hua | Personal chat pe company data = **galat policy** | Important work **sirf Kanha app** → server draft |
| Form bharà, store nahi hua | Real ERP risk | Failed-entry heal + server draft autosave |
| Mobile chori / kharab | Real | **Revoke sessions** + drafts already on server |
| Employee cheat / time waste | Partial | **Audit anomalies** (backup burst, mass delete, stale drafts) — not keylogger |
| Phone me spyware ERP | Mostly unnecessary | Force company app + MDM later if needed; abhi revoke + drafts kaafi |

**Policy (1 line):** Company ka kaam personal Notes/WhatsApp me mat rakho — Kanha app me likho, har few seconds server pe draft sync.

## Near / mid future ERP problems (priority)

| # | Risk | Kab dukhega | Abhi solution | Baad me |
|---|------|-------------|----------------|---------|
| 1 | Device loss + local-only data | Roz | Server `WorkDraft` + revoke sessions | MDM / remote wipe OS-level |
| 2 | Half-saved entry | Roz | Failed entries + rollback | — |
| 3 | Insider data theft (export/backup) | Kabhi | Anomaly: backup/export burst | DLP / watermark exports |
| 4 | Mass delete / wipe | Kabhi | Anomaly mass_delete | Soft-delete + recycle bin |
| 5 | Shared login / password leak | Common | Login churn signal + revoke | SSO / MFA |
| 6 | GST / e-Invoice rule change | Yearly | Compliance agent hooks | GSP version adapters |
| 7 | Duplicate customers/SKU | Growth | (plan) master dedupe | Fuzzy match UI |
| 8 | Fiscal period open edits | Year-end | (plan) period lock | Hard close accounting |
| 9 | Concurrent two users same invoice | Multi-user | Idempotency keys | Optimistic lock version |
| 10 | SQLite scale / lag | Growth | HA pack + Postgres path | Postgres primary |
| 11 | Integration key leak in .env | Ops | Go-live checklist | Secrets vault |
| 12 | Soft training / wrong module use | Always | RBAC + audit | In-app guided tours |

## Implemented now (this pass)

1. **`PUT /api/drafts`** — server autosave (`API.saveDraft` / `API.draftAutosave`)
2. **`POST /api/auth/revoke-sessions`** — khud ke saare devices logout
3. **`POST /api/security/revoke-user-sessions`** — admin: employee phone stolen
4. **JWT `se` (session_epoch)** — revoke ke baad purana token dead
5. **`GET /api/security/anomalies`** — accountability signals (48h)
6. **Settings UI** — drafts list, revoke buttons, anomaly table

## Mobile app role (recommendation)

Haan — **company mobile app useful hai**, lekin spyware ke liye nahi:

- Offline forms → queue → sync drafts to server  
- Biometric login + short session  
- No “export all” on phone role  
- Stolen → admin Revoke devices; drafts company pe already  

Personal WhatsApp/Notes pe important deal notes = **policy fail**, tech fail nahi.

## Honest “unnecessary”

- Employee ke personal photos track karna  
- Always-on GPS spy (unless field-force product explicitly)  
- Keylogger  

Useful: drafts, revoke, audit anomalies, RBAC, HA.

## Where to click

**Settings → Security — stolen phone / drafts / accountability**  
Also see `HA_RISKS.md` for server failover risks.
