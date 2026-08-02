# KanhaERP — User Manual (Demo)

1. Open the app and login with `admin@kanhaerp.com` / `admin123`.
2. Dashboard shows revenue, outstanding, inventory value, tickets.
3. **Live Flow Tour** creates Lead → Quotation → Sales Order → Delivery/Invoice.
4. CRM, Sales, Purchase, Inventory, Accounting screens list live API data.
5. Settings → toggle modules, add custom fields, view roles & audit.

# Admin Manual

- Module registry: enable/disable per company.
- Custom fields: entity + key + type (text/select).
- Workflows: amount-based SO approval thresholds.
- Payroll: Run Payroll computes PF/ESIC lines.
- Theme: top bar Theme toggle (persisted per user).

# Developer Guide

- Entry: `backend/app/main.py`
- Models: `backend/app/models/__init__.py`
- APIs: `backend/app/api/{core,trading,extended}.py`
- Seed: `backend/app/services/seed.py`
- Frontend: `frontend/js/app.js` (hash router SPA)
- Set `DATABASE_URL` for Postgres; `REDIS_URL` for cache/queues.

# Installation

Python 3.11+, pip install requirements, run uvicorn. Or `docker compose up --build`.
