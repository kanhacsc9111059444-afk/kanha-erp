# KanhaERP — Setup & Activation Guide

Step-by-step guide to set up KanhaERP for your organization.

---

## Before You Start

**Requirements:**
- Python 3.11+ (or use Docker)
- PostgreSQL 12+ (for production)
- Git
- 2GB RAM minimum
- 5GB disk space

---

## Step 1: Clone Repository

```bash
git clone https://github.com/kanhacsc9111059444-afk/kanha-erp.git
cd kanha-erp
git checkout clean/kanha-fresh-v2  # Use clean version
```

---

## Step 2: Environment Setup

### Copy Environment File

```bash
cp .env.example .env
```

### Edit `.env` with Your Details

```env
# Essential Config
APP_NAME=Your Company ERP
COMPANY_NAME=Your Company Pvt Ltd
COMPANY_GSTIN=22AAAAA0000A1Z5
ADMIN_EMAIL=admin@yourcompany.com
ADMIN_PASSWORD=YourSecurePassword123!
SECRET_KEY=generate-long-random-string-here
DEMO_MODE=false

# Database
DATABASE_URL=sqlite:///./data/kanha_erp.db
# For production, use: DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/kanha_erp
```

---

## Step 3: Backend Setup (Choose One)

### Option A: Docker (Easiest)

```bash
docker-compose up
# API runs on http://127.0.0.1:8080
```

### Option B: Manual Setup (Linux/Mac)

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload
```

### Option C: Windows PowerShell

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload
```

### Option D: Windows Batch (Portable)

Double-click `SETUP_PORTABLE.bat` (first time only), then `START_KANHA.bat`

---

## Step 4: Access Application

1. Open browser: **http://127.0.0.1:8080**
2. Login with:
   - Email: `admin@kanhaerp.com`
   - Password: `admin123`

---

## Step 5: Initial Configuration

### 5.1 Change Admin Password

1. Click user icon (top-right)
2. Go to **Settings** → **Change Password**
3. Enter new strong password
4. Save

### 5.2 Configure Company

1. **Settings** → **Company**
2. Update:
   - Company name
   - GST number
   - Address
   - Phone number
3. Click **Save**

### 5.3 Set Up Chart of Accounts

1. **Accounting** → **Chart of Accounts**
2. Add main account groups:
   - Assets
   - Liabilities
   - Equity
   - Income
   - Expenses
3. Add sub-accounts as needed

### 5.4 Create Warehouses

1. **Settings** → **Warehouses**
2. Click **+ Add Warehouse**
3. Enter:
   - Warehouse name
   - Location
4. Save

### 5.5 Add Users

1. **Settings** → **Users**
2. Click **+ Add User**
3. Enter:
   - Email
   - Full name
   - Role (Admin/Sales/Accounts/etc.)
4. Set password
5. Save

### 5.6 Configure Roles & Permissions

1. **Settings** → **Roles**
2. Create roles as needed:
   - Sales Manager
   - Purchase Manager
   - Accountant
   - HR Manager
3. Assign permissions per role

### 5.7 Add Masters Data

#### Customers
1. **CRM** → **Parties**
2. Click **+ Add Party**
3. Enter customer details
4. Save

#### Products/Items
1. **Inventory** → **Products**
2. Click **+ Add Product**
3. Enter:
   - SKU
   - Name
   - Category
   - Unit of Measure (UOM)
   - Price
   - GST rate
4. Save

#### Vendors
1. **Purchase** → **Vendors**
2. Click **+ Add Vendor**
3. Enter vendor details
4. Save

---

## Step 6: Customize Branding (Optional)

1. **Settings** → **Brand**
2. Update:
   - Logo (upload PNG/SVG)
   - Brand colors
   - Tagline
   - Support email
3. Click **Save**

---

## Step 7: Integration Setup (Optional)

### WhatsApp Business

1. Get credentials from Meta Business Manager
2. **Settings** → **Integrations** → **WhatsApp**
3. Paste:
   - API Token
   - Phone Number ID
   - Verify Token
4. Save

### Razorpay Payments

1. Get keys from Razorpay dashboard
2. **Settings** → **Integrations** → **Razorpay**
3. Paste:
   - Key ID
   - Key Secret
4. Save

### Email (SMTP)

1. **Settings** → **Integrations** → **Email**
2. Configure:
   - SMTP Server (e.g., smtp.gmail.com)
   - Port (usually 587)
   - Username
   - Password (app-specific password)
3. Test connection
4. Save

---

## Step 8: Test Core Functions

### Create Test Sales Order

1. **Sales** → **Sales Orders**
2. Click **+ New Order**
3. Select customer
4. Add products
5. Click **Save**

### Create Test Invoice

1. **Sales** → **Invoices**
2. Click **+ New Invoice**
3. Link to sales order
4. Review amount
5. Click **Save**
6. Click **Print** to generate PDF

### Test Report

1. **Reports**
2. Select a report
3. Set date range
4. Click **Generate**
5. Verify data

---

## Step 9: Data Backup

### Automated Daily Backup

```bash
# Create backup script
echo '#!/bin/bash' > backup.sh
echo 'sqlite3 data/kanha_erp.db ".backup backup_$(date +%Y%m%d).db"' >> backup.sh
chmod +x backup.sh

# Add to crontab (Linux/Mac)
crontab -e
# Add: 0 2 * * * /path/to/backup.sh
```

### Manual Backup

```bash
# SQLite
cp data/kanha_erp.db data/kanha_erp_backup_$(date +%Y%m%d).db

# PostgreSQL
pg_dump -U kanha kanha_erp > backup_$(date +%Y%m%d).sql
gzip backup_$(date +%Y%m%d).sql
```

---

## Step 10: Go Live Checklist

Before production deployment:

- [ ] Changed admin password
- [ ] Set SECRET_KEY to random string
- [ ] Set DEMO_MODE=false
- [ ] Configured company details
- [ ] Added all users with proper roles
- [ ] Imported master data (customers, products, vendors)
- [ ] Tested all core workflows
- [ ] Set up backups
- [ ] Configured HTTPS (if needed)
- [ ] Tested integrations (if using)
- [ ] Trained staff on system
- [ ] Documented custom workflows

---

## Troubleshooting

### Port 8080 Already in Use

```bash
# Find what's using port 8080
lsof -i :8080

# Kill it (Linux/Mac)
kill -9 <PID>

# Or use different port
uvicorn app.main:app --port 8081
```

### Database Connection Error

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Restart if needed
sudo systemctl restart postgresql

# Check connection string in .env
```

### Import Error

```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

---

## Support

- Check `/docs` folder for detailed guides
- See `GO_LIVE.md` for production deployment
- Review `README.md` for architecture overview

---

**Last Updated:** August 2, 2026
