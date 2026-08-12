# KanhaERP — Open-Source ERP for Indian SMBs

**Version:** 2026-08-02 (Production Ready)  
**Stack:** FastAPI + SPA · SQLite (dev) / Postgres (production)  
**Goal:** Complete business ERP for small & medium enterprises · Ready to deploy · White-label capable

---

## 🚀 Quick Start (5 minutes)

### Windows (Portable)
```
1. Python 3.11+ install (Add to PATH)
2. Double-click: SETUP_PORTABLE.bat (first time only)
3. Double-click: START_KANHA.bat
4. Open browser: http://127.0.0.1:8080
```

### Terminal (Any OS)
```bash
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload
```

### Docker
```bash
docker-compose up
```

---

## 👤 Demo Logins

| Role | Email | Password |
|------|--------|----------|
| **Admin** | `admin@kanhaerp.com` | `admin123` |
| Sales | `sales@kanhaerp.com` | `sales123` |
| Accounts | `accounts@kanhaerp.com` | `accounts123` |

**⚠️ Production:** Change all passwords in `.env` before going live.

---

## 📊 Business Flow

```
Lead / Marketing → Sales Order → Delivery Challan → Sales Invoice → Payment
                                                           ↓
Purchase Requisition → Purchase Order → Material Receipt → Purchase Invoice

Inventory Management: Stock Tracking · Batch/Serial · Multi-Warehouse Transfers
Accounting: General Ledger · GST Compliance · Bank Reconciliation
HR & Payroll: Employees · Attendance · Leaves · Payroll · Expense Claims
```

---

## 🎯 Core Modules

| Module | Features |
|--------|----------|
| **CRM** | Parties, Leads, Opportunities, Follow-ups |
| **Sales** | Orders, Delivery Challans, Invoices, Payments |
| **Purchase** | Purchase Orders, Material Receipts, Invoices |
| **Inventory** | Stock Management, Transfers, Physical Count, Batches |
| **Accounting** | Chart of Accounts, Journal Entries, Ledgers, GST |
| **HRMS** | Employees, Attendance, Leaves, Payroll, Loans |
| **Store** | Material Issue/Receive, Physical Stock, Transfers |
| **Reports** | Custom reports, data export |
| **Integrations** | WhatsApp, Razorpay, E-Invoice (GSP), Maps, AI Chat |

---

## 🏗️ Architecture

```
KanhaERP/
├── backend/              FastAPI application
│   ├── app/
│   │   ├── main.py      App factory & middleware
│   │   ├── api/         Route modules (50+ APIs)
│   │   ├── models/      Database models (50+ entities)
│   │   ├── services/    Business logic
│   │   └── core/        Config, DB, Auth, Middleware
│   └── requirements.txt  Dependencies
│
├── frontend/            Single-page application (SPA)
│   ├── js/
│   │   ├── api.js       HTTP client
│   │   └── app.js       Main application logic
│   ├── css/             Styles
│   └── index.html       Entry point
│
├── data/                Database & uploads (runtime)
├── deploy/              Deployment configs
├── docs/                Documentation
└── docker-compose.yml   Multi-container setup
```

**Database Schema:** 50+ tables covering CRM, Sales, Purchase, Inventory, Accounts, HRMS, Manufacturing, Compliance & more.

---

## ⚙️ Configuration

Copy `.env.example` → `.env` and customize:

```env
# Branding
APP_NAME=YourERP
BRAND_TAGLINE=Your Company Tagline
BRAND_PRIMARY=#1d4ed8
BRAND_ACCENT=#0f766e
BRAND_LOGO_URL=/assets/favicon.svg

# Company
COMPANY_NAME=Your Company Pvt Ltd
COMPANY_CODE=YOUR
COMPANY_GSTIN=22AAAAA0000A1Z5

# Security
SECRET_KEY=change-me-to-long-random-string
ADMIN_EMAIL=admin@yourcompany.com
ADMIN_PASSWORD=StrongPassword123!
DEMO_MODE=false

# Database
DATABASE_URL=sqlite:///./data/kanha_erp.db
# Or: postgresql+psycopg2://user:pass@localhost:5432/kanha_erp

# Integrations (set when needed)
WHATSAPP_TOKEN=your_token
RAZORPAY_KEY_ID=your_key
GSP_API_KEY=your_key
SMTP_SERVER=your_smtp_server
```

**Health Check:** http://127.0.0.1:8080/api/health

---

## 📚 Documentation

| File | Purpose |
|------|---------|
| `GO_LIVE.md` | Production deployment checklist |
| `docs/USER_GUIDE.md` | End-user guide |
| `docs/ACTIVATION.md` | Setup & activation |
| `docs/WHITE_LABEL.md` | Custom branding instructions |

---

## 🔐 Security Features

✅ JWT Authentication with rate limiting  
✅ Role-Based Access Control (RBAC)  
✅ Password policies & 2FA support  
✅ Encrypted sensitive data  
✅ Audit logging on all transactions  
✅ HTTPS-ready (reverse proxy)  
✅ CORS protection  
✅ SQL injection prevention (SQLAlchemy ORM)

---

## 🚀 Production Deployment

### Pre-deployment Checklist
- [ ] Change SECRET_KEY (strong random string)
- [ ] Set DEMO_MODE=false
- [ ] Change admin password (not admin123)
- [ ] Set CORS_ORIGINS to your domain
- [ ] Use Postgres database
- [ ] Enable HTTPS (nginx/Caddy reverse proxy)
- [ ] Configure backups (daily)
- [ ] Test email/WhatsApp/payment integrations

### Quick Deploy (Render, Heroku, DigitalOcean)
1. Push to GitHub
2. Connect repository to hosting platform
3. Set environment variables
4. Deploy!

See `GO_LIVE.md` for detailed production setup.

---

## 🔧 Tech Stack

**Backend:**
- Python 3.11+ | FastAPI | Uvicorn
- SQLAlchemy 2.0+ (ORM)
- Pydantic 2.0+ (Validation)
- PostgreSQL / SQLite

**Frontend:**
- Vanilla JavaScript (SPA)
- HTML5 | CSS3
- PWA support (Service Worker)

**Infrastructure:**
- Docker & Docker Compose
- Redis (caching/queue)
- Optional: Postgres, Nginx

---

## 🤝 Support

- **Documentation:** See `/docs` folder
- **Issues:** GitHub Issues
- **Email:** support@kanhaerp.com (configure in `.env`)

---

## 📄 License

Open-source. See LICENSE file for details.

---

## 🎯 Roadmap

**Current Release (v1.0.0):**
- ✅ Core CRM, Sales, Purchase, Inventory
- ✅ Accounting with GST compliance
- ✅ HRMS & Payroll
- ✅ Integration adapters ready
- ✅ White-label support
- ✅ HA/Resilience features

**Future (v2.0+):**
- Native mobile apps (iOS/Android)
- Advanced MRP & Manufacturing
- BI & Data Warehouse integration
- Multi-language support
- Additional payment gateways

---

**Made with ❤️ for Indian businesses**

Last Updated: August 2, 2026
