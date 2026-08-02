================================================================================
KANHAERP — GO-LIVE (real ERP / white-label)
================================================================================
Product is treated as production-ready. You only wait on CONNECTIVITY (keys,
domain, Postgres). Core software paths are live-wired.

--------------------------------------------------------------------------------
1) BEFORE FIRST PRODUCTION START
--------------------------------------------------------------------------------
1. copy .env.example → .env
2. Set SECRET_KEY (long random), DEMO_MODE=false, strong ADMIN_PASSWORD
   Before going live with DEMO_MODE=true: Admin → Settings → "Purge demo sample"
   (type DELETE DEMO SAMPLE). This wipes sample transactions only; users/COA stay.
   After DEMO_MODE=false the purge button/API is HARD BLOCKED — never mass-deletes live data.
3. Set CORS_ORIGINS to your real domain(s) — never *
4. Prefer DATABASE_URL=postgresql+... (docker-compose.yml includes Postgres)
5. run.prod.bat  (or uvicorn without --reload)

Local walkthrough can still use run.bat + DEMO_MODE=true.

--------------------------------------------------------------------------------
2) WHAT IS ALREADY REAL (no key needed)
--------------------------------------------------------------------------------
[✓] JWT auth + login rate limit + password policy (prod)
[✓] Hard RBAC on all mutating /api writes
[✓] Change password API
[✓] White-label brand API (/api/brand + /api/brand/public)
[✓] SQLite backup (/api/ops/backup + scripts/backup_db.bat)
[✓] Agent scheduler (stock + compliance; cash opt-in)
[✓] Scan billing, RFID, agents, WhatsApp OS, compliance scorecards
[✓] Integration adapters: WhatsApp / Razorpay / GSP / LLM — switch live when keys set
[✓] HA cluster: primary + hot replicas + 5 identical portable ERP mirrors (see HA_ARCHITECTURE.md)

[✓] Bill-by-bill AR/AP + payment allocations
[✓] Bank statement CSV import + recon match
[✓] FEFO batch issue on Sales/POS
[✓] BOM → WIP → FG costing on production receive
[✓] Godown stock valuation (qty × avg cost)
[✓] GSTR-1 desk JSON + GSTR-3B CGST/SGST/IGST from GSTIN
[✓] Purchase journals + sales COGS + credit limit on SO
[✓] RCM receive (ITC + GST payable) + GSTR-3B RCM netting
[✓] Party ledger CSV export (customer/vendor)
[✓] Vendor/sales multi-bill FIFO pay when amount > one bill
[✓] Demo document links under /uploads/demo (not 404)

--------------------------------------------------------------------------------
3) ONLY WAITING ON CONNECTIVITY (paste keys in .env)
--------------------------------------------------------------------------------
- WHATSAPP_TOKEN + WHATSAPP_PHONE_NUMBER_ID  → live WhatsApp send
- RAZORPAY_KEY_ID + RAZORPAY_KEY_SECRET      → live payment orders
- GSP_BASE_URL + GSP_API_KEY                 → live e-Invoice/e-Way push
- MAPS_API_KEY + MAPS_PROVIDER               → live map tiles
- LLM_API_KEY + LLM_PROVIDER                 → live AI chat
- SMTP_*                                     → live email
- Domain + HTTPS reverse proxy               → public URL
- Postgres URL                               → production DB
  Example: DATABASE_URL=postgresql+psycopg2://kanha:kanha@localhost:5432/kanha_erp
  (docker-compose.yml already has Postgres service)
- Bank NEFT API / payout partner             → real salary/vendor transfer (until then mark paid is honest)
- Extra servers / NAS paths                  → set CLUSTER_PEERS + BACKUP_MIRROR_1..5

Check status anytime: GET /api/health → integrations + golive.checklist
Books desk: #/books → bill-wise, bank CSV, GSTR-1 download
Inventory: #/inventory → godown valuation + FEFO batches
Manufacturing: WO Advance → BOM consume → Challan Receive → WIP→FG

--------------------------------------------------------------------------------
4) WHITE-LABEL FOR A NEW CLIENT
--------------------------------------------------------------------------------
.env:
  APP_NAME=ClientERP
  BRAND_* colors/logo
  COMPANY_NAME / GSTIN
  ADMIN_EMAIL / ADMIN_PASSWORD
OR Settings → brand save via PUT /api/brand (admin)

--------------------------------------------------------------------------------
5) BACKUPS + MULTI-SITE ERP (not DB-only)
--------------------------------------------------------------------------------
- Resilience UI: #/ha  (sync / mirror / promote / failover)
- Portable packs: data/mirrors/site-1..5 (+ BACKUP_USER_PACK USB/NAS)
- scripts\backup_db.bat  (classic SQLite archive)
- Postgres: pg_dump daily (hosting panel / cron)
- Full design: HA_ARCHITECTURE.md
  → 1 primary writer, hot replicas, identical packs, auto-promote on crash

--------------------------------------------------------------------------------
6) SECURITY CHECKLIST
--------------------------------------------------------------------------------
[ ] SECRET_KEY not default
[ ] DEMO_MODE=false
[ ] Admin password changed (not admin123)
[ ] CORS locked to domain
[ ] HTTPS terminated (nginx/Caddy)
[ ] Scheduler cash OFF until WhatsApp verified (SCHEDULER_RUN_CASH=false)
[ ] CLUSTER_TOKEN changed from default (shared on all nodes)
[ ] BACKUP_MIRROR_* on separate disks / NAS (not same drive as primary)

================================================================================
