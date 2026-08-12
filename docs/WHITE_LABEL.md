# KanhaERP — White-Label Customization Guide

Configure KanhaERP for any company without code changes.

---

## Quick Rebrand (5 minutes)

### Method 1: Environment Variables (.env)

Edit `.env` file:

```env
APP_NAME=ClientERP
COMPANY_NAME=Client Company Pvt Ltd
COMPANY_CODE=CLIENT
COMPANY_GSTIN=22AAAAA0000A1Z5
BRAND_TAGLINE=Your Company Tagline
BRAND_PRIMARY=#1d4ed8
BRAND_ACCENT=#0f766e
BRAND_LOGO_URL=/assets/your-logo.svg
BRAND_SUPPORT_EMAIL=support@client.com
ADMIN_EMAIL=admin@client.com
ADMIN_PASSWORD=ClientPassword123!
```

Then restart:

```bash
# Stop current instance
Ctrl+C

# Start again
uvicorn app.main:app --reload
```

---

### Method 2: Admin UI (No Restart)

1. Login as Admin
2. Go to **Settings** → **Brand**
3. Update:
   - Company Name
   - Logo (upload PNG/SVG)
   - Brand colors
   - Tagline
   - Support email
4. Click **Save**

Changes apply immediately without restart.

---

## Customization Options

### 1. Company Information

**Settings** → **Company**

- Company name
- GST number
- Address
- Phone number
- Currency
- Financial year

### 2. Branding

**Settings** → **Brand**

- **Logo:** Upload PNG/SVG (recommended 200x50px)
- **Primary Color:** Main brand color (hex)
- **Accent Color:** Secondary color (hex)
- **Tagline:** Your company tagline
- **Support Email:** Help desk email

### 3. User Roles & Permissions

**Settings** → **Roles**

Create custom roles:
- Sales Manager
- Purchase Manager
- Accountant
- HR Manager
- Store Manager

Assign permissions per module.

### 4. Custom Fields

**Settings** → **Custom Fields**

Add fields to any entity:
- Party (customer/vendor)
- Product
- Invoice
- Purchase Order
- Employee

Example: Add "Department Code" to employees

### 5. Workflows

**Settings** → **Workflows**

Define approval workflows:
- Sales Order approval (amount threshold)
- Purchase Order approval
- Expense claim workflow
- Leave approval hierarchy

---

## Theme Customization (Advanced)

### Color Scheme

Edit `frontend/css/theme.css` for custom colors:

```css
:root {
  --primary: #1d4ed8;
  --accent: #0f766e;
  --success: #10b981;
  --warning: #f59e0b;
  --danger: #ef4444;
}
```

### Logo

Replace `frontend/favicon.svg` with your logo:

1. Prepare logo as SVG or PNG (200x50px recommended)
2. Save as `frontend/favicon.svg`
3. Restart application

### Email Template

Customize email notifications in `backend/app/services/email.py`

---

## Multi-Tenant Setup (Advanced)

For multiple clients with separate databases:

### Database per Client

```bash
# Create separate database
psql -U postgres
CREATE DATABASE client1_erp;
CREATE USER client1 WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE client1_erp TO client1;
```

### Configuration per Client

Create separate `.env` files:

```bash
.env.client1
.env.client2
```

Start instances:

```bash
# Client 1 on port 8001
env $(cat .env.client1) uvicorn app.main:app --port 8001

# Client 2 on port 8002
env $(cat .env.client2) uvicorn app.main:app --port 8002
```

Use nginx to route by domain:

```nginx
server {
    server_name client1.erp.com;
    location / {
        proxy_pass http://127.0.0.1:8001;
    }
}

server {
    server_name client2.erp.com;
    location / {
        proxy_pass http://127.0.0.1:8002;
    }
}
```

---

## Deployment Scenarios

### Scenario 1: Single Company, Single Server

- One `.env` file
- One database
- One application instance
- One domain

### Scenario 2: Multiple Branches (Same Company)

- One `.env` file
- One database (with branch column in tables)
- One application instance
- Configure branches in **Settings** → **Branches**

### Scenario 3: Multiple Clients (Different Companies)

- Separate `.env` for each client
- Separate database per client
- Separate application instances (different ports)
- Reverse proxy (nginx) to route by domain

---

## Customization Checklist

- [ ] Update company name and GST
- [ ] Upload logo
- [ ] Set brand colors
- [ ] Configure admin email
- [ ] Create user roles
- [ ] Add custom fields
- [ ] Set up approval workflows
- [ ] Create chart of accounts
- [ ] Add warehouses
- [ ] Import product master
- [ ] Import customer/vendor list
- [ ] Configure integrations (WhatsApp, Razorpay, etc.)
- [ ] Set up email templates
- [ ] Test all workflows
- [ ] Train staff
- [ ] Set up backups

---

## Common Customizations

### Add Custom Field to Invoice

1. **Settings** → **Custom Fields**
2. Click **+ Add Field**
3. Entity: "Invoice"
4. Field name: "Project Code"
5. Type: "Text"
6. Click **Save**
7. Field appears in invoice form

### Create Sales Manager Role

1. **Settings** → **Roles**
2. Click **+ Add Role**
3. Name: "Sales Manager"
4. Permissions:
   - ✓ Create/Edit Sales Orders
   - ✓ Create/Edit Invoices
   - ✓ View Reports
   - ✓ View Payments
5. Click **Save**

### Set Approval Workflow

1. **Settings** → **Workflows**
2. Click **+ Add Workflow**
3. Name: "PO Approval"
4. Entity: "Purchase Order"
5. Add steps:
   - Step 1: Purchase Manager approval
   - Step 2: Finance Manager approval
6. Click **Save**

---

## Support

- Configuration help: See `ACTIVATION.md`
- Deployment: See `GO_LIVE.md`
- User guide: See `USER_GUIDE.md`

---

**Last Updated:** August 2, 2026
