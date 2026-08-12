# KanhaERP — User Guide

Complete guide for end-users. Simple, step-by-step instructions.

---

## Getting Started

### Login

1. Open your browser: `https://yourdomain.com` (or `http://127.0.0.1:8080` for local)
2. Select your role icon or enter email
3. Enter password
4. Click **Login**

### Demo Credentials

| Role | Email | Password |
|------|--------|----------|
| Admin | admin@kanhaerp.com | admin123 |
| Sales | sales@kanhaerp.com | sales123 |
| Accounts | accounts@kanhaerp.com | accounts123 |

> **Production Note:** Passwords are changed during setup.

---

## Main Dashboard

After login, you see:

- **Quick Stats:** Orders, Invoices, Payments pending
- **Module Links:** Quick access to CRM, Sales, Purchase, etc.
- **Notifications:** System alerts
- **User Menu:** Top-right corner

---

## CRM Module

### Add Party (Customer/Vendor)

1. Navigate: **CRM** → **Parties**
2. Click **+ Add Party**
3. Fill in:
   - Name
   - Email
   - Phone
   - GST Number (if applicable)
   - Address
4. Click **Save**

### Create Lead

1. **CRM** → **Leads**
2. Click **+ Add Lead**
3. Enter lead details
4. Click **Save**

---

## Sales Module

### Create Sales Order

1. **Sales** → **Sales Orders**
2. Click **+ New Order**
3. Select customer
4. Add line items (products, qty, rate)
5. Review total amount
6. Click **Save**
7. For approval-required orders, submit for approval

### Create Invoice

1. **Sales** → **Invoices**
2. Click **+ New Invoice**
3. Select customer
4. Link to sales order (optional)
5. Add items
6. Click **Save**
7. Use **Print** to generate PDF

### Track Payment

1. **Sales** → **Invoices**
2. Click on invoice
3. Click **+ Add Payment**
4. Enter amount, date, method
5. Click **Save**

---

## Purchase Module

### Create Purchase Order

1. **Purchase** → **Purchase Orders**
2. Click **+ New PO**
3. Select vendor
4. Add items with quantity
5. Click **Save**

### Record Material Receipt (GRN)

1. **Purchase** → **Material Receipts**
2. Click **+ New Receipt**
3. Link to PO (if available)
4. Enter received quantities
5. Click **Save**

---

## Inventory Module

### Check Stock

1. **Inventory** → **Stock Ledger**
2. Select warehouse
3. Search product
4. View available quantity, value, batch details

### Transfer Stock Between Warehouses

1. **Inventory** → **Transfers**
2. Click **+ New Transfer**
3. Select from warehouse and to warehouse
4. Add items with quantities
5. Click **Save**

### Physical Stock Count

1. **Inventory** → **Physical Count**
2. Click **+ New Count**
3. Select warehouse and date
4. Scan/enter actual quantities
5. Review variance
6. Click **Submit**

---

## Accounting Module

### View General Ledger

1. **Accounts** → **Ledger**
2. Select account from chart
3. View debit/credit entries
4. Filter by date range

### Create Journal Entry

1. **Accounts** → **Journal Entries**
2. Click **+ New Entry**
3. Add line items:
   - Account (debit/credit)
   - Amount
4. Click **Save**

### Bank Reconciliation

1. **Accounts** → **Bank Reconciliation**
2. Import bank statement (CSV)
3. Match transactions
4. Mark reconciled
5. Click **Complete**

---

## HRMS Module

### Mark Attendance

1. **HRMS** → **Attendance**
2. Select date and employee
3. Mark: Present, Absent, Leave, etc.
4. Click **Save**

### Request Leave

1. **HRMS** → **Leave Requests**
2. Click **+ New Request**
3. Select leave type
4. Enter dates
5. Add reason (optional)
6. Click **Submit**

### View Payroll

1. **HRMS** → **Payroll**
2. Select month/year
3. View salary components
4. Approve if needed
5. Generate salary slips

---

## Reports

### Generate Report

1. Click **Reports** in main menu
2. Select report type (Sales, Purchase, Inventory, etc.)
3. Set date range and filters
4. Click **Generate**
5. Click **Export** for Excel/PDF

### Schedule Email Report

1. **Reports** → **Scheduled Reports**
2. Click **+ Add**
3. Select report
4. Set frequency (daily, weekly, monthly)
5. Enter email recipients
6. Click **Save**

---

## Settings

### Change Password

1. Click user icon (top-right)
2. Click **Settings**
3. Click **Change Password**
4. Enter old and new password
5. Click **Save**

### Company Configuration

1. **Settings** → **Company**
2. Update company details
3. Update GST configuration
4. Click **Save**

### Custom Branding

1. **Settings** → **Brand**
2. Upload logo
3. Change colors
4. Update tagline
5. Click **Save**

---

## Print & Export

### Print Document

1. Open document (invoice, PO, etc.)
2. Click **Print** button
3. Adjust layout in print preview
4. Click **Print** or **Save as PDF**

### Export Data

1. Open list (invoices, purchases, etc.)
2. Click **Export** button
3. Select format: Excel or CSV
4. File downloads to your computer

---

## Common Tasks

### "How do I add a new customer?"
**Answer:** CRM → Parties → + Add Party

### "How do I create an invoice?"
**Answer:** Sales → Invoices → + New Invoice → Fill details → Save

### "How do I check stock?"
**Answer:** Inventory → Stock Ledger → Select product

### "How do I mark attendance?"
**Answer:** HRMS → Attendance → Mark status → Save

### "How do I approve a purchase order?"
**Answer:** Purchase → POs → Click PO → Approve (if you have permission)

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + S` | Save current form |
| `Ctrl + P` | Print |
| `Ctrl + E` | Export |
| `Esc` | Close dialog |
| `/` | Search bar |

---

## Tips & Tricks

✓ Use search (Ctrl+F or /) to find transactions quickly  
✓ Filters help narrow down large lists  
✓ Export to Excel for further analysis  
✓ Use print preview before printing  
✓ Check notifications for pending approvals  
✓ Archive old data to keep system fast  

---

## Getting Help

- **Within app:** Click **Help** icon or **?** button
- **Email:** support@yourcompany.com
- **Admin:** Contact your system administrator

---

**Last Updated:** August 2, 2026
