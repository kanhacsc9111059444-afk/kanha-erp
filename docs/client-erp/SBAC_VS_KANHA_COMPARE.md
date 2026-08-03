# SBAC → KanhaERP Compare Guide

**Kaise use karein:** Do browsers / do windows kholo — left pe SBAC live ERP, right pe KanhaERP. Same module open karo, neeche table me field-by-field match dekho. Fresh entry only (client data import nahi). Look/UI alag rahega — fields + flow same hone chahiye.

| System | URL |
|--------|-----|
| **SBAC Digital ERP** | https://erp.sbacindia.in |
| **KanhaERP** | https://kanha-erp.onrender.com |
| **Kanha login** | `admin@kanhaerp.com` / `admin123` |

**Status legend**

| Mark | Meaning |
|------|---------|
| ✅ same | Field + working Kanha me present (same logic) |
| 🟡 partial | Hai, lekin UX/master-list/upload alag (text vs live dropdown, URL vs file, etc.) |
| ❌ not yet | Deepen docs / Kanha UI me abhi nahi / optional later |

---

## Quick nav map

| # | SBAC menu / screen | SBAC path (approx) | Kanha hash route | Kanha screen / kaise kholo |
|---|--------------------|--------------------|------------------|----------------------------|
| 1 | Master → Party Master | `/Balaji/BalajiPartymaster.aspx` | `#/crm` | CRM → **+ Party** |
| 2 | Master → Item Master | `/Master/ItemMasterConfig.aspx` | `#/inventory` | Inventory → **+ Item** |
| 3 | Sales → Create Sales Order | `/Balaji/CreateNewSaleOrder.aspx` | `#/sales` | Sales → **+ Sales Order** |
| 4 | SO → Delivery Challan (pending) | `/SalesOrder/PendingSalesOrderForDeliveryChallan.aspx` | `#/sales` | Pending SO → **Create Challan** |
| 5 | Create Delivery Challan | `/Balaji/CreateNewDeliveryChallan.aspx` | `#/sales` | Challan drawer (SO se) |
| 6 | Direct Sales Invoice | `/Balaji/CreateNewSalesInvoice.aspx` | `#/sales` | **+ Direct Invoice** |
| 7 | Pending Challan → Invoice | `/SalesOrder/PendingChallanForSalesInvoice.aspx` | `#/sales` | Pending challan → **Create Invoice** |
| 8 | Create PO | `/Purchase/PurchaseOrderNew.aspx` | `#/purchase` | Purchase → **+ Purchase Order** |
| 9 | Create MRN (multi-PO) | `/Balaji/CreateMaterialReceiptwithmultiplepo.aspx` | `#/purchase` | Pending PO → **Create MRN** |
| 10 | MRN Cash / Direct | `/Balaji/CreateMaterialReceiptCash.aspx` | `#/purchase` | Direct path / PI family |
| 11 | Purchase Invoice For Po | `/Purchase/CreateMaterialReceipt.aspx` *(SBAC error)* | `#/purchase` | Pending MRN → **Create PI** / **PI (RCM)** · **+ Direct PI** |
| 12 | Store → Issue Items | `/Balaji/IssueItemBalaji.aspx` | `#/store` | Store → Material Issue |
| 13 | Store → Receive Items | `/Balaji/ReceiveItemBalaji.aspx` | `#/store` | Store → Material Receive |
| 14 | Physical Stock | `/Store/PhysicalStock.aspx` | `#/store` | Physical Stock (+ Approve) |
| 15 | Godown Transfer | (stock ops) | `#/store` | Godown Transfer |
| 16 | Accounts → Create Ledger | `/Account/LedgerSub.aspx` | `#/books` | Kanha Books → Create Ledger |
| 17 | Payment / Receipt / Contra / Journal / CN / DN | `/Account/Voucherdenominations.aspx?Vtype=…` | `#/books` | Voucher drawers |
| 18 | Day Book / TB / P&L / BS | `/Account/rptDayBook…` | `#/books` · `#/accounting` | Reports / period lock |
| 19 | HR → Employee Master | `/Master/EmployeeMaster.aspx` | `#/hrms` | HRMS → Employee |
| 20 | Leave Application | `/HR/LeaveApplication.aspx` | `#/hrms` | Leaves |
| 21 | Process Salary Attendance | `/Master/ProcessSalaryAttendance.aspx` | `#/hrms` | Attendance process |
| 22 | Employee Loan | `/hr/employeewiseloandetail.aspx` | `#/hrms` | Loans |
| 23 | Salary Confirmation | `/Balaji/BalajiSalaryConfirmation.aspx` | `#/hrms` · `#/hr-flow` | Payroll run → Confirm → Approve |
| 24 | MIS Report | `/MIS/FrmmisReport.aspx` | `#/mis` | MIS Analytics |
| 25 | Tally Parent Mapping / Errors / Inactive | Master + Salesorder Tally pages | `#/bridges` | Connected Apps / Bridges |
| 26 | WhatsApp Login | `/user/whatsappset.aspx` | `#/extras` · `#/whatsapp` | Extras / WhatsApp OS |
| 27 | Admin / Marketing / Production / Visit / Task / Service | many `.aspx` | various | See **Still later** |

**Core flow (dono systems):**

```
Lead → Sales Order → Delivery Challan → Sales Invoice → Receipt / Outstanding
Indent/PR/RFQ → PO → MRN → Store → Purchase Invoice → Vendor Payment
Accounts: Ledger + Vouchers → Day Book / TB / P&L / BS → Tally bridge
HR: Employee → Leave/Attendance → Loan → Salary Confirm/Approve/Slip
```

---

## Module-by-module field compare

### 1) Party Master

- **SBAC URL(s):** https://erp.sbacindia.in/Balaji/BalajiPartymaster.aspx — tabs: Add Party | View Party  
- **Kanha:** `#/crm` → **+ Party** (Party Master drawer)  
- **APIs:** `POST/PUT /api/crm/customers` · `POST /api/crm/gst-lookup` · `custom` JSON: `addresses[]`, `banks[]`, `contacts[]`, `employee`, `company`, `export`

#### Primary

| # | SBAC field / option / section | SBAC where | Kanha where | Status |
|---|--------------------------------|------------|-------------|--------|
| 1 | GST Number (`txtTINNO`) + **GST Search** (`btnsrch`) | Primary | Primary → GST Number + GST Search | ✅ same |
| 2 | Party Code (`txtfinalpartycode`) — auto | Primary | Auto code on save / list | ✅ same |
| 3 | Domestic / Export (`ddlpartynature`) — Domestic, Export | Primary | Domestic / Export select | ✅ same |
| 4 | Party Name (`txtPartyName`) *required* | Primary | Party Name *required* | ✅ same |
| 5 | Under Account (`ddlunderaccount`) — ledger list (Agent/Salesman, Bank Accounts, Sundry Debtors, …) | Primary | Under Account select | ✅ same |
| 6 | File As (`txtfileas`) | Primary | File As | ✅ same |
| 7 | Whatsapp Number (`txtWhatsappNumber`) *required* | Primary | Whatsapp Number *required* | ✅ same |
| 8 | Joinning Date (`dtpjoinning_*`) d/m/y | Primary | Joinning Date | ✅ same |
| 9 | W. Area (`txtwarea`) | Primary | W. Area | ✅ same |
| 10 | Repeat Order Days (`txtrepeatdays`) | Primary | Repeat Order Days | ✅ same |
| 11 | Branch List (`chkbranchlist_*`) multi-checkbox | Primary | Branch List checkboxes | ✅ same |
| 12 | Show in Order followup (`ddlshoworderfollowup`) Yes/No | Primary | Show in Order followup | ✅ same |
| 13 | Transport (`ddltransportname`) live transporter list | Primary | Transport master select + Add | ✅ same |
| 14 | Agent Name (`ddlagentname`) live agent list | Primary | Agent master select + Add | ✅ same |
| 15 | Actions: Submit / Delete / Reset | Primary | Submit / Delete (soft) / Reset | ✅ same |

#### Section toggles (SBAC checkboxes → Kanha always-visible sections)

| # | SBAC section | Checkbox | Kanha where | Status |
|---|--------------|----------|-------------|--------|
| 16 | Employee Details | `CheckBox1` | Section: Employee Details | ✅ same |
| 17 | Address Details | `CheckBox3` | Section: Address Details | ✅ same |
| 18 | Account Details | `CheckBox2` | Section: Account Details | ✅ same |
| 19 | Company Details | `chkAcd` | Section: Company Details | ✅ same |
| 20 | Bank Details | `CheckBox4` | Section: Bank Details | ✅ same |
| 21 | Contact Details | `CheckBox5` | Section: Contact Details | ✅ same |
| 22 | Export Details | `chkexport` | Section: Export Details | ✅ same |

#### Employee Details

| # | SBAC field | SBAC where | Kanha where | Status |
|---|------------|------------|-------------|--------|
| 23 | Department | Employee Details | emp_department | ✅ same |
| 24 | Designation | Employee Details | emp_designation | ✅ same |
| 25 | Email | Employee Details | emp_email | ✅ same |
| 26 | Mobile No. | Employee Details | emp_mobile | ✅ same |
| 27 | Reporting Person | Employee Details | emp_reporting_person | ✅ same |

#### Address Details (multi via Add / Reset)

| # | SBAC field | SBAC where | Kanha where | Status |
|---|------------|------------|-------------|--------|
| 28 | Address Type * (incl. “Shiping Address”) | Address | addr_type | ✅ same |
| 29 | Country * (`ddlregion`) | Address | addr_country | ✅ same |
| 30 | State * | Address | addr_state | ✅ same |
| 31 | City * | Address | addr_city | ✅ same |
| 32 | Area * | Address | addr_area | ✅ same |
| 33 | Address | Address | addr_address | ✅ same |
| 34 | Pin Code | Address | addr_pincode | ✅ same |
| 35 | Telephone | Address | addr_telephone | ✅ same |
| 36 | Email | Address | addr_email | ✅ same |
| 37 | Mobile | Address | addr_mobile | ✅ same |
| 38 | Website | Address | addr_website | ✅ same |
| 39 | Fax No. | Address | addr_fax | ✅ same |
| 40 | Add / Reset multi-address | Address | Add → Saved addresses list | ✅ same |

#### Account Details

| # | SBAC field | SBAC where | Kanha where | Status |
|---|------------|------------|-------------|--------|
| 41 | Opening Balance | Account | opening_balance | ✅ same |
| 42 | Cr/Dr | Account | Dr / Cr | ✅ same |
| 43 | Currency | Account | Currency select | ✅ same |
| 44 | Credit Limit | Account | credit_limit | ✅ same |
| 45 | Credit Limit(Days) | Account | credit_days | ✅ same |
| 46 | Grade A–D | Account | Grade A/B/C/D | ✅ same |
| 47 | Pan No. | Account | pan | ✅ same |
| 48 | CTS No. | Account | cts_no | ✅ same |
| 49 | Pvt Marka | Account | pvt_marka | ✅ same |
| 50 | Sales Target | Account | sales_target | ✅ same |
| 51 | Ecc No. | Account | ecc_no | ✅ same |
| 52 | Status Active/NonActive | Account | status_active radio | ✅ same |
| 53 | Tcs Allow Yes/No | Account | tcs_allow | ✅ same |
| 54 | Tds Allow Yes/No | Account | tds_allow | ✅ same |

#### Company Details

| # | SBAC field | SBAC where | Kanha where | Status |
|---|------------|------------|-------------|--------|
| 55 | Company type | Company | company_type | ✅ same |
| 56 | Customer Type | Company | customer_type | ✅ same |
| 57 | Head Quarter | Company | head_quarter | ✅ same |
| 58 | Area | Company | company_area | ✅ same |
| 59 | Discount Percente | Company | discount_pct | ✅ same |
| 60 | Discount Name | Company | discount_name | ✅ same |
| 61 | Alias | Company | alias | ✅ same |
| 62 | Remarks | Company | remarks | ✅ same |
| 63 | Show Remarks | Company | show_remarks checkbox | ✅ same |

#### Bank Details (multi via Add / Reset)

| # | SBAC field | SBAC where | Kanha where | Status |
|---|------------|------------|-------------|--------|
| 64 | Bank Name * | Bank | bank_name | ✅ same |
| 65 | Account Holder * | Bank | bank_holder | ✅ same |
| 66 | Account No. * | Bank | bank_account | ✅ same |
| 67 | Swift Code | Bank | bank_swift | ✅ same |
| 68 | IFSC Code | Bank | bank_ifsc | ✅ same |
| 69 | Region/Country * | Bank | bank_country | ✅ same |
| 70 | State | Bank | bank_state | ✅ same |
| 71 | City | Bank | bank_city | ✅ same |
| 72 | Address | Bank | bank_address | ✅ same |
| 73 | Pin Code | Bank | bank_pincode | ✅ same |
| 74 | Telephone | Bank | bank_telephone | ✅ same |
| 75 | Email | Bank | bank_email | ✅ same |
| 76 | Mobile | Bank | bank_mobile | ✅ same |
| 77 | Website | Bank | bank_website | ✅ same |
| 78 | Fax No. | Bank | bank_fax | ✅ same |
| 79 | Add / Reset multi-bank | Bank | Saved bank accounts | ✅ same |

#### Contact Details (multi via Add / Reset)

| # | SBAC field | SBAC where | Kanha where | Status |
|---|------------|------------|-------------|--------|
| 80 | Contact Person * | Contact | contact_person | ✅ same |
| 81 | Job Title | Contact | contact_job_title | ✅ same |
| 82 | Designation * | Contact | contact_designation | ✅ same |
| 83 | Mobile | Contact | contact_mobile | ✅ same |
| 84 | Whatsapp Number | Contact | contact_whatsapp | ✅ same |
| 85 | Telephone | Contact | contact_telephone | ✅ same |
| 86 | DOB | Contact | contact_dob | ✅ same |
| 87 | Associate Date | Contact | contact_associate_date | ✅ same |
| 88 | Email | Contact | contact_email | ✅ same |
| 89 | Commission % | Contact | contact_commission | ✅ same |
| 90 | Add / Reset multi-contact | Contact | Saved contacts | ✅ same |

#### Export Details

| # | SBAC field | SBAC where | Kanha where | Status |
|---|------------|------------|-------------|--------|
| 91 | Packing Charge | Export | export_packing_charge | ✅ same |
| 92 | Pre-Carriage by | Export | export_carriage_by | ✅ same |
| 93 | Place of Receipt by Pre-Carrier | Export | export_receipt_by | ✅ same |
| 94 | Port of Discharge | Export | export_port_discharge | ✅ same |
| 95 | Port of Loading | Export | export_port_loading | ✅ same |
| 96 | LUT/Bond No | Export | export_lut_bond | ✅ same |
| 97 | Final Destination | Export | export_final_dest | ✅ same |

#### Kanha-only (Party)

| Extra | Where |
|-------|--------|
| **Kanha Role** — Customer / Vendor / Dealer / Transport / Agent / Employee | Primary → `party_type` |
| Dealers portal link (`#/dealers`) | Separate CRM-adjacent |

---

### 2) Item Master

- **SBAC URL(s):** https://erp.sbacindia.in/Master/ItemMasterConfig.aspx — Add Item | View Item  
- **Kanha:** `#/inventory` → **+ Item**  
- **APIs:** `POST/GET /api/inventory/products` · `custom`: `other`, `conversions[]`, `classification`, `tax_duty`, `dimension`, `stock`, `rate_list`, `country_list`, `vendors[]`, `packings[]`

#### Primary

| # | SBAC field / option | SBAC where | Kanha where | Status |
|---|---------------------|------------|-------------|--------|
| 1 | Branch Name (`ddlBranchName`) — RPR, FARM, HYD, DGP, IND, MANDAWA, … | Primary | Branch Name / branch list | ✅ same |
| 2 | Item Code * (`PartNoTextBox`) auto if blank | Primary | SKU / Item Code | ✅ same |
| 3 | Item Name * (`PartNAmeTextBox`) | Primary | Item Name | ✅ same |
| 4 | Part Image (`FileUpload1`) | Primary | Image URL (file upload later) | 🟡 partial |
| 5 | Select Brand (`ddlbrand`) + add/refresh — MS PIPE, ASTRAL, JSW, JINDAL, … | Primary | Brand select (masters lighter) | 🟡 partial |
| 6 | Base Unit * — BAG, NOS, BOX, MTR, PCS, MT, BUNDLE, KGS, COIL, QTL, PACKET, TIN, SQF, LTR | Primary | Base Unit | ✅ same |
| 7 | Main Group * — BAJRI, BRICKS, CEMENT, CPVC, ELECTRODES, … | Primary | Main Group | 🟡 partial |
| 8 | Sub Group | Primary | Sub Group | 🟡 partial |
| 9 | Category/Make — HARD FACING, Mild Steel, LOCAL, … | Primary | Category/Make | 🟡 partial |
| 10 | HSN Code | Primary | HSN | ✅ same |
| 11 | Item Description | Primary | Description | ✅ same |
| 12 | Purchase Default Unit | Primary | Purchase Default Unit | ✅ same |
| 13 | Sale Default Unit | Primary | Sale Default Unit | ✅ same |
| 14 | Color | Primary | Color | ✅ same |
| 15 | Size (e.g. 3.15x450MM, …) | Primary | Size | ✅ same |
| 16 | Branch list multi-checkbox | Primary | Branch list checkboxes | ✅ same |
| 17 | SBAC inline Add Unit / Brand / Group / Category refresh icons | Primary chrome | Masters via Inventory / Settings (alag) | 🟡 partial |

#### Section checkboxes

| # | Section | SBAC checkbox | Kanha section | Status |
|---|---------|---------------|---------------|--------|
| 18 | Other Section | `chkotherdiv` | Other Section | ✅ same |
| 19 | Conversion Factor | `chkConversion` | Conversion Factor | ✅ same |
| 20 | Item Specification | `chkbox` | Item Specification | ✅ same |
| 21 | Item Classification | `chkitemclass` | Item Classification | ✅ same |
| 22 | Tax Duty Details | `chktaxduty` | Tax Duty Details | ✅ same |
| 23 | Dimension | `chkdimension` | Dimension | ✅ same |
| 24 | Stock Value | `chkstokevalue` | Stock Value | ✅ same |
| 25 | Rate List | `chkratelist` | Rate List | ✅ same |
| 26 | Country List | `chkcountrylist` | Country List | 🟡 partial |
| 27 | Vendor Details | `chkvendorlist` | Vendor Details | ✅ same |
| 28 | Packing Instruction | `PackingInstruction` | Packing Instruction | ✅ same |
| 29 | Sub Item | `chkSubItem` | Sub Item (Other Section) | ✅ same |

#### Other Section

| # | SBAC field | Kanha where | Status |
|---|------------|-------------|--------|
| 30 | Same as Item Name | same_as_item_name | ✅ same |
| 31 | Parent Item Code / Parent name | parent_item_code / parent_item_name | ✅ same |
| 32 | Gross Weight | gross_weight | ✅ same |
| 33 | Net Weight | net_weight | ✅ same |
| 34 | Cartoon Weight | cartoon_weight | ✅ same |
| 35 | Standard Packaging Quantity | std_pack_qty | ✅ same |
| 36 | Sub Item | sub_item | ✅ same |
| 37 | Subitem Required* Yes/No | subitem_required | ✅ same |
| 38 | Area calculationrequired Yes/No | area_calc_required | ✅ same |
| 39 | Formula Reqd* No/Yes | formula_required | ✅ same |
| 40 | Formula | formula | ✅ same |
| 41 | Upload Image (`FileUpload2`) in Other | Image URL / primary image | 🟡 partial |

#### Conversion Factor (multi Add)

| # | SBAC field | Kanha where | Status |
|---|------------|-------------|--------|
| 42 | Base Unit | conv_base_unit | ✅ same |
| 43 | Conversion Unit | conv_unit | ✅ same |
| 44 | Value | conv_value | ✅ same |
| 45 | Add Conversion | Saved conversions list | ✅ same |

#### Item Specification / Classification / Tax / Dimension

| # | SBAC field | Kanha where | Status |
|---|------------|-------------|--------|
| 46 | Item Specification (textarea) | specification | ✅ same |
| 47 | Rack No | rack_no | ✅ same |
| 48 | Bin No | bin_no | ✅ same |
| 49 | Purchase Name | purchase_name | ✅ same |
| 50 | Purchase Code | purchase_code | ✅ same |
| 51 | Bar Code | barcode | ✅ same |
| 52 | Finished Goods / Raw Material / Semi finished / Powder coated | item_class radio | ✅ same |
| 53 | Tarrif Classification | tariff_classification | ✅ same |
| 54 | Duty | duty | ✅ same |
| 55 | Commodity Code | commodity_code | ✅ same |
| 56 | Length / Width / Height / Weight | dim_* | ✅ same |
| 57 | Dimension Unit | dim_unit | ✅ same |
| 58 | Volumetric Weight | volumetric_weight | ✅ same |

#### Stock Value

| # | SBAC field | Kanha where | Status |
|---|------------|-------------|--------|
| 59 | Unit | stock_unit | ✅ same |
| 60 | Closing Stock | closing_stock | ✅ same |
| 61 | Opening Stock | opening_stock | ✅ same |
| 62 | Monthly Consumption | monthly_consumption | ✅ same |
| 63 | Re order level | reorder_level | ✅ same |
| 64 | Minimum Stock | min_stock | ✅ same |
| 65 | Maximum Stock | max_stock | ✅ same |
| 66 | Minimum Order Quantity | min_order_qty | ✅ same |

#### Rate List

| # | SBAC field | Kanha where | Status |
|---|------------|-------------|--------|
| 67 | Purchase | cost_price | ✅ same |
| 68 | MRP | mrp | ✅ same |
| 69 | GST(%) | gst_rate | ✅ same |
| 70 | GST Include | gst_include | ✅ same |
| 71 | Date | rate_date | ✅ same |
| 72 | Exporter GST(%) | exporter_gst | ✅ same |
| 73 | Exporter GST Include | exporter_gst_include | ✅ same |
| 74 | Bom Rate | bom_rate | ✅ same |
| 75 | Active / NonActive | status_active | ✅ same |

#### Country List / Vendor / Packing

| # | SBAC field / option | Kanha where | Status |
|---|---------------------|-------------|--------|
| 76 | Multi-country checkboxes (full SBAC world list: Oman, Tanzania, India, UAE Dubai, …) | Common export set + **Other countries** text | 🟡 partial |
| 77 | Vendor Name + Contact No. + Add | vendor_name, vendor_contact, Saved vendors | ✅ same |
| 78 | Packing Unit | pack_unit | ✅ same |
| 79 | Serial No | pack_serial | ✅ same |
| 80 | Qty + Qty unit | pack_qty / pack_qty_unit | ✅ same |
| 81 | Weight / Height / Width / Length + units | pack_* + units | ✅ same |
| 82 | From Unit | pack_from_unit | ✅ same |
| 83 | Add Packing | Saved packing lines | ✅ same |
| 84 | Submit (`SubmitButton`) | Save Item | ✅ same |

#### Kanha-only (Item)

| Extra | Where |
|-------|--------|
| **Sale Price (Kanha)** — defaults from MRP if blank | Rate List |
| RFID / Scan Billing hooks | `#/rfid`, `#/pos` (related, not Item form clone) |

---

### 3) Sales Order

- **SBAC URL(s):** https://erp.sbacindia.in/Balaji/CreateNewSaleOrder.aspx  
- **Kanha:** `#/sales` → **+ Sales Order**  
- **APIs:** `POST/GET /api/sales/orders` · lines + `charges[]` + `custom` (terms, executive, cc, exemption, amc_status, quotation_ref, …)

#### Header

| # | SBAC field / option | SBAC where | Kanha where | Status |
|---|---------------------|------------|-------------|--------|
| 1 | Entry Type (`ddlentrytype`) Lead / Quotation / Order / Direct Entry Type | Header | Entry Type | ✅ same |
| 2 | Series Type (`ddlseriestype`) Main / Export | Header | Series Type | ✅ same |
| 3 | Order No (`txtorderno`) auto | Header | Order No auto | ✅ same |
| 4 | Order Date | Header | Order Date | ✅ same |
| 5 | Delivery Date | Header | Delivery Date | ✅ same |
| 6 | Quotation No / Ref | Header | Quotation Ref | ✅ same |
| 7 | Party Name lookup | Header | Party select | ✅ same |
| 8 | File attach + Upload | Header | File upload → `attachment_url` | ✅ same |
| 9 | Customer Order No | Header | Customer Order No | ✅ same |
| 10 | Delivery Type CIF / PAID / TO PAY / CC | Header | Delivery Type | ✅ same |
| 11 | Transport Name | Header | Transport | ✅ same |

#### Party Details (`chkparty`)

| # | SBAC field | Kanha where | Status |
|---|------------|-------------|--------|
| 12 | Bill To Address | Party Details | ✅ same |
| 13 | Ship To Address | Party Details | ✅ same |
| 14 | Mobile No | Party Details | ✅ same |
| 15 | GST No | Party Details | ✅ same |
| 16 | Order Remarks | Party Details / Remarks | ✅ same |

#### Item Details (line Add)

| # | SBAC field | Kanha line grid | Status |
|---|------------|-----------------|--------|
| 17 | Item name/Code (`ddlitem`) | Item | ✅ same |
| 18 | Quantity | Qty | ✅ same |
| 19 | MRP (`txtrate`) | MRP | ✅ same |
| 20 | GST% | GST% | ✅ same |
| 21 | Sale Rate | Sale Rate | ✅ same |
| 22 | Billing Unit | Unit | ✅ same |
| 23 | Discount (%) | Disc% | ✅ same |
| 24 | Convert Value | Convert Value | ✅ same |
| 25 | Special Rate | Special Rate | ✅ same |
| 26 | Item Description | Desc | ✅ same |
| 27 | Add (`btnadd`) | Add line | ✅ same |
| 28 | Totals: Total Qty · Total Amount · Grand Total | Footer totals | ✅ same |

#### Other Values (`chkothervalues`) multi Add

| # | SBAC field / option | Kanha where | Status |
|---|---------------------|-------------|--------|
| 29 | Nature Less/Add | charges[] Nature | ✅ same |
| 30 | Other Type Discount/Freight/Insurance/IGST… | Other Type | ✅ same |
| 31 | Tax Percent (%) | Tax% | ✅ same |
| 32 | Amount | Amount | ✅ same |
| 33 | Other Tax | Other Tax | ✅ same |
| 34 | Add | Add charge | ✅ same |

#### Terms / Other Details / Actions

| # | SBAC field | Kanha where | Status |
|---|------------|-------------|--------|
| 35 | Term And Condition rich text (default: *100% Payment Against Proforma Invoice.*) | Terms | ✅ same |
| 36 | Add term | Terms | ✅ same |
| 37 | Executive | Other Details | ✅ same |
| 38 | CC | Other Details | ✅ same |
| 39 | Exemption Yes/No | Other Details | ✅ same |
| 40 | AMC Status Active/Inactive | Other Details | ✅ same |
| 41 | Submit · Reset | Save | ✅ same |
| 42 | Godown / warehouse on flow | Kanha warehouse mapping | ✅ same (Kanha keeps godown) |

---

### 4) Delivery Challan

- **SBAC URL(s):**  
  - List: https://erp.sbacindia.in/SalesOrder/PendingSalesOrderForDeliveryChallan.aspx  
  - Create: https://erp.sbacindia.in/Balaji/CreateNewDeliveryChallan.aspx?orderid=…  
  - Edit list: `/SalesOrder/EditFrmEntry.aspx?type=Challan`  
- **Kanha:** `#/sales` → Pending SO → **Create Challan**  
- **APIs:** `GET /api/sales/orders/pending-challan` · `POST /api/sales/flow/order-to-challan/{order_id}`

#### A) Pending SO list filters / grid

| # | SBAC field | Kanha where | Status |
|---|------------|-------------|--------|
| 1 | Order From / To Date | Pending SO filters | ✅ same |
| 2 | Party Name filter | Pending SO | ✅ same |
| 3 | Order No filter | Pending SO | ✅ same |
| 4 | Search | Search / refresh | ✅ same |
| 5 | Grid: Order No · Order Date · Party · Total Qty · Bal Qty · Total Amt · **Create Challan** | Pending SO table + button | ✅ same |

#### B) Create Delivery Challan header

| # | SBAC field / option | Kanha where | Status |
|---|---------------------|-------------|--------|
| 6 | Series Type * Main / Export | Header | ✅ same |
| 7 | Challan No * auto | Header | ✅ same |
| 8 | Challan Date * | Header | ✅ same |
| 9 | Party Name (from SO) | Header | ✅ same |
| 10 | Transporter | Header | ✅ same |
| 11 | Godown | Header | ✅ same |
| 12 | Remarks | Header | ✅ same |
| 13 | Delivery Boy | Header | ✅ same |
| 14 | Destination | Header | ✅ same |
| 15 | No of Cart | Header | ✅ same |
| 16 | Delivery Type CIF / PAID / TO PAY / CC | Header | ✅ same |

#### Export Details (on challan)

| # | SBAC field | Kanha `Delivery.custom` | Status |
|---|------------|-------------------------|--------|
| 17 | Packing Charge | export fields | ✅ same |
| 18 | Pre-Carriage by | export | ✅ same |
| 19 | Place of Receipt by Pre-Carrier | export | ✅ same |
| 20 | Port of Discharge | export | ✅ same |
| 21 | Port of Loading | export | ✅ same |
| 22 | LUT/Bond No | export | ✅ same |
| 23 | Final Destination | export | ✅ same |

#### Item grid (`gvadditem`)

| # | SBAC column | Kanha line | Status |
|---|-------------|------------|--------|
| 24 | ItemName | Item | ✅ same |
| 25 | Balance Qty | Bal Qty | ✅ same |
| 26 | Issued Qty | Issued Qty | ✅ same |
| 27 | Godown | Godown | ✅ same |
| 28 | No Of Packing | no_of_packing | ✅ same |
| 29 | SaleRate | Sale Rate | ✅ same |
| 30 | Amount | Amount | ✅ same |
| 31 | Discount | Discount | ✅ same |
| 32 | Billing Unit | Unit | ✅ same |
| 33 | Totals: Total Qty · Total Amt · Total Tax · Grand Total | Footer | ✅ same |

#### Terms / Actions / Edit

| # | SBAC field | Kanha where | Status |
|---|------------|-------------|--------|
| 34 | Term And Condition (`CheckTerm`) | Terms in custom | ✅ same |
| 35 | Save · Reset | Save Challan (stock out) | ✅ same |
| 36 | Edit/Search list (Entry From/To, Party, Entry No) | Sales challan list / edit | 🟡 partial |

---

### 5) Sales Invoice

- **SBAC URL(s):**  
  - Direct: https://erp.sbacindia.in/Balaji/CreateNewSalesInvoice.aspx  
  - Pending Challan: `/SalesOrder/PendingChallanForSalesInvoice.aspx`  
- **Kanha:** `#/sales` → **+ Direct Invoice** · Pending challan → **Create Invoice**  
- **APIs:** `POST /api/sales/invoices/direct` · `POST /api/sales/flow/delivery-to-invoice/{id}`

#### A) Direct Sales Invoice — header

| # | SBAC field / option | Kanha where | Status |
|---|---------------------|-------------|--------|
| 1 | Type Direct / DeliveryChallan | Entry type | ✅ same |
| 2 | Series Type Main / Export | Series | ✅ same |
| 3 | Invoice No auto | Invoice No | ✅ same |
| 4 | Invoice Date | Date | ✅ same |
| 5 | Party Name lookup | Party | ✅ same |
| 6 | Godown | Godown | ✅ same |
| 7 | Invoice Remarks | Remarks | ✅ same |
| 8 | Agent | Agent | ✅ same |
| 9 | Transport | Transport | ✅ same |
| 10 | No of Cartoon | No of Cartoon | ✅ same |
| 11 | Delivery Type CIF / PAID / TO PAY / CC | Delivery Type | ✅ same |
| 12 | Freight Mode FOR / PAID / TO PAY | Freight Mode | ✅ same |
| 13 | E-way Bill No | E-way Bill No | ✅ same |
| 14 | Invoice Type Domestic / Export | Invoice Type | ✅ same |
| 15 | GR No / GR Date | GR No / Date | ✅ same |
| 16 | Truck No | Truck No | ✅ same |
| 17 | Pay Mode ADVANCE / CASH / NEFT / UPI… | Pay Mode | ✅ same |
| 18 | Transaction Type Regular / Bill To-Ship To… | Transaction Type | ✅ same |
| 19 | Transport Mode Road / Rail / Air / Ship | Transport Mode | ✅ same |
| 20 | E-way Bill Type TransportId / Vehicle | E-way Bill Type | ✅ same |
| 21 | Dispatch Place | Dispatch Place | ✅ same |

#### Party / Items / Other Values

| # | SBAC field | Kanha where | Status |
|---|------------|-------------|--------|
| 22 | Bill To · Ship To · Mobile · GST No | Party Details | ✅ same |
| 23 | Item · Qty · MRP · GST% · Godown · Sale Rate · Rate With Tax · Batch No · Billing Unit · Desc/Packing · Discount% · Convert Value · Add | Line grid | ✅ same |
| 24 | Other Values: Nature · Other Type · Tax% · Amount · Other Tax · Add | charges[] | ✅ same |

#### Payment (`chkpayment`) / Terms

| # | SBAC field | Kanha where | Status |
|---|------------|-------------|--------|
| 25 | Mode · Amount · Transaction No · Transaction Date · Narration · Add | Payment section | ✅ same |
| 26 | Total Payable · Advance Adjust | Payment | ✅ same |
| 27 | JV Account / Debit-Credit / Amount | JV adjust | ✅ same |
| 28 | Term And Condition · Add · Save / Reset | Terms | ✅ same |

#### B) Pending Challan → Invoice

| # | SBAC field | Kanha where | Status |
|---|------------|-------------|--------|
| 29 | Grid: Challan No · Date · Party · Qty · Amt · **Create Invoice** | Pending challan table | ✅ same |
| 30 | Header form Series/Transport/E-way/Payment then post | Invoice-from-challan drawer | ✅ same |

#### Related SBAC (nav map, deepen later / partial elsewhere)

| Screen | Kanha hint | Status |
|--------|------------|--------|
| Cash Invoice | `#/sales` / POS `#/pos` | 🟡 partial |
| Sales Return | Sales return (existed) | 🟡 partial |
| Create E-invoice | `#/logistics` / compliance | 🟡 partial |

---

### 6) Purchase Order

- **SBAC URL(s):** https://erp.sbacindia.in/Purchase/PurchaseOrderNew.aspx  
- **Kanha:** `#/purchase` → **+ Purchase Order**  
- **APIs:** `POST/GET /api/purchase/orders` · `GET …/pending-grn` · `custom` series/freight/party/other/terms/round_off

#### Header

| # | SBAC field / option | Kanha where | Status |
|---|---------------------|-------------|--------|
| 1 | Series Type Main / RFQ | Header | ✅ same |
| 2 | Order_No * (auto on Kanha) | Header | ✅ same |
| 3 | Order_Date * | Header | ✅ same |
| 4 | Party Type Sundry Creditors / Sundry Debtors | Header | ✅ same |
| 5 | Party Name lookup → vendor | Vendor select | ✅ same |
| 6 | Freight Mode FOR / PAID / TO PAY | Freight Mode | ✅ same |
| 7 | Narration | Narration | ✅ same |
| 8 | Delivery Date | Delivery Date | ✅ same |

#### Party Details (`chkparty`)

| # | SBAC field | Kanha where | Status |
|---|------------|-------------|--------|
| 9 | Delivery Branch | Party Details | ✅ same |
| 10 | Booked Station | Party Details | ✅ same |
| 11 | Ship Branch | Party Details | ✅ same |
| 12 | Ship / Shipping Address | Party Details | ✅ same |

#### Other Section (`chkothersection`)

| # | SBAC field | Kanha where | Status |
|---|------------|-------------|--------|
| 13 | State | Other Section | ✅ same |
| 14 | Agent | Other Section | ✅ same |
| 15 | Payment Mode | Other Section | ✅ same |
| 16 | Currency | Other Section | ✅ same |
| 17 | Transporter Mode | Other Section | ✅ same |
| 18 | Transporter | Other Section | ✅ same |
| 19 | Godown | Other Section / warehouse | ✅ same |
| 20 | Supplier Contact | Other Section | ✅ same |
| 21 | Delivery Per | Other Section | ✅ same |
| 22 | Delivery Contact No | Other Section | ✅ same |
| 23 | Ref No | Other Section | ✅ same |
| 24 | Behalf Of | Other Section | ✅ same |
| 25 | Order Duration | Other Section | ✅ same |
| 26 | Declaration | Other Section | ✅ same |

#### Item Details / Other Item / Tax / Terms

| # | SBAC field | Kanha where | Status |
|---|------------|-------------|--------|
| 27 | Classification · Sub Classification · Category | Line extras | ✅ same |
| 28 | Item Code · Item · Qty · MRP · Disc value · CD% · Add Tax% · Unit · Make · Model · Specification · Item Specification · Inspection Instr · Convert · Add/Reset | Line grid | ✅ same |
| 29 | Other Item: Discount · Add Tax Amt · Sale Amt · Description · Remarks · Due Date · Discount Type · Item Tax | Other Item Details | ✅ same |
| 30 | Totals: Total Qty · Total · Round Off · Grand Total | Footer | ✅ same |
| 31 | Other/Tax AddTax: Nature Add/Less · Tax Type · Value % · Tax Amount | charges[] | ✅ same |
| 32 | Term And Condition · Save / Reset | Terms | ✅ same |

---

### 7) MRN (Material Receipt / GRN)

- **SBAC URL(s):**  
  - https://erp.sbacindia.in/Balaji/CreateMaterialReceiptwithmultiplepo.aspx  
  - Cash: `/Balaji/CreateMaterialReceiptCash.aspx`  
  - Edit: `/SalesOrder/EditFrmEntry.aspx?type=MRN`  
- **Kanha:** `#/purchase` → Pending PO → **Create MRN**  
- **APIs:** `GET …/orders/pending-grn` · `POST /api/purchase/flow/po-to-grn/{po_id}` · `GoodsReceipt.custom`

#### Header

| # | SBAC field / option | Kanha where | Status |
|---|---------------------|-------------|--------|
| 1 | Type Direct / PO | Type | ✅ same |
| 2 | PO No + Search | From pending PO | ✅ same |
| 3 | Series Type Main | Series | ✅ same |
| 4 | Receipt No auto | MRN No | ✅ same |
| 5 | Receipt Date | Date | ✅ same |
| 6 | Party Name (vendor from PO) | Vendor | ✅ same |
| 7 | Bill No | Bill No | ✅ same |
| 8 | Bill Date | Bill Date | ✅ same |
| 9 | Godown | Godown | ✅ same |
| 10 | Freight Mode FOR / PAID / TO PAY | Freight Mode | ✅ same |
| 11 | QC Status No / Yes | QC Status | ✅ same |
| 12 | Received By | Received By | ✅ same |
| 13 | Invoice Remarks | Remarks | ✅ same |

#### Other Details / Lines / Tax / Payment / JV

| # | SBAC field | Kanha where | Status |
|---|------------|-------------|--------|
| 14 | Lot No · GR No · GR Date · Total Wt · Description · Order No · Trans Id · Process (merge) | Other Details / custom | ✅ same |
| 15 | Lines: Bal Qty · **Receive Qty** · Godown · Batch/Lot · Packing · Rate · Disc% · Unit | Line grid | ✅ same |
| 16 | Other/Tax AddTax Nature · Tax Type · Value% · Tax Amount | charges[] | ✅ same |
| 17 | Totals Total Qty · Total Amount · Grand Total | Footer | ✅ same |
| 18 | Payment Method optional: Mode · Amount · Txn No · Date · Narration · Total Payable | Payment | ✅ same |
| 19 | Bill Adjustment: Advance Adjust · Adjust Amount · Bill Adjusted | Bill Adjustment | ✅ same |
| 20 | Journal Voucher optional: Account · Dr/Cr · Amount · Txn No · Date · Narration | JV | ✅ same |
| 21 | Save · Reset · Edit/Search | Save MRN (stock in) | ✅ same |

#### Pending PO grid (purchase-chain)

| # | Column / action | Kanha where | Status |
|---|-----------------|-------------|--------|
| 22 | PO No, Date, Vendor, Total Qty, Bal Qty, Amt · **Create MRN** (partial bal) | Pending PO table | ✅ same |

---

### 8) Purchase Invoice

- **SBAC URL(s):** Material Receipt family (Cash + Multi-PO).  
  **Note:** `/Purchase/CreateMaterialReceipt.aspx` (PI For Po) — **SBAC server error** on load; fields Material Receipt controls se liye.  
- **Kanha:** `#/purchase` → Pending MRN → **Create PI** / **PI (RCM)** · **+ Direct PI**  
- **APIs:** `GET …/grn/pending-invoice` · `POST …/flow/grn-to-invoice/{id}` · `POST /api/purchase/invoices/direct`

#### Header / Other / Items

| # | SBAC field / option | Kanha where | Status |
|---|---------------------|-------------|--------|
| 1 | Type Direct / PO | Type | ✅ same |
| 2 | PO No + Search | From pending MRN | ✅ same |
| 3 | Series Type Main | Series | ✅ same |
| 4 | Receipt / Invoice No auto | PI No | ✅ same |
| 5 | Receipt / Invoice Date | Date | ✅ same |
| 6 | Party Name vendor | Vendor | ✅ same |
| 7 | Bill No · Bill Date | Bill fields | ✅ same |
| 8 | Godown (Direct PI stock in) | Godown | ✅ same |
| 9 | Freight Mode FOR / PAID / TO PAY | Freight | ✅ same |
| 10 | QC Status No / Yes | QC | ✅ same |
| 11 | Received By | Received By | ✅ same |
| 12 | Invoice Remarks | Remarks | ✅ same |
| 13 | **RCM Yes/No** (AP = taxable when Yes) | Kanha RCM on PI | ✅ same *(Kanha explicit; SBAC PI page broken)* |
| 14 | Other Details: Lot No · GR No · GR Date · Total Wt · Description | Other Details | ✅ same |
| 15 | From MRN: lines locked qty/rate/GST | Locked lines | ✅ same |
| 16 | Direct/Cash lines: Item · Qty · Rate · Discount · GST% · Godown · Make · Unit · Convert · Remarks · Batch · Add | Direct PI lines | ✅ same |
| 17 | Other/Tax AddTax + Totals + Round Off | charges + footer | ✅ same |
| 18 | Payment Method optional | Payment | ✅ same |
| 19 | Bill Adjustment | Bill Adjustment | ✅ same |
| 20 | Journal Voucher optional | JV | ✅ same |
| 21 | Save · Reset · Edit/Search | Save PI | ✅ same |
| 22 | Pending MRN grid → Create PI / PI (RCM) | Pending MRN table | ✅ same |

---

### 9) Store (Issue / Receive / Physical / Transfer)

- **SBAC URL(s):**  
  - Issue: https://erp.sbacindia.in/Balaji/IssueItemBalaji.aspx  
  - Receive: https://erp.sbacindia.in/Balaji/ReceiveItemBalaji.aspx  
  - Physical: https://erp.sbacindia.in/Store/PhysicalStock.aspx  
- **Kanha:** `#/store`  
- **APIs:** `/api/store/issues` · receives · physical · approve · godown-transfer · indent-to-issue

#### Material Issue

| # | SBAC field / option | Kanha where | Status |
|---|---------------------|-------------|--------|
| 1 | Issue No auto | Issue No | ✅ same |
| 2 | Issue Date | Date | ✅ same |
| 3 | Issue Type | Issue Type | ✅ same |
| 4 | Bill No | Bill No | ✅ same |
| 5 | Party | Party | ✅ same |
| 6 | Godown | Godown | ✅ same |
| 7 | Issued By | Issued By | ✅ same |
| 8 | Remarks | Remarks | ✅ same |
| 9 | Item Issue Type Consumable / Returnable | Item Issue Type | ✅ same |
| 10 | Item · Qty · Rate · Amt + Add | Lines | ✅ same |
| 11 | Advance · Total Qty · Total Amt · Grand | Totals | ✅ same |
| 12 | Save and Print · Edit/Search · Reset | Save and Print (`/api/print/issue|receive`) | ✅ same |
| 13 | Department · Purpose · Indent → Issue | Kanha extra / indent flow `#/indents` | ✅ same (Kanha) |

#### Material Receive

| # | SBAC field | Kanha where | Status |
|---|------------|-------------|--------|
| 14 | Receive No auto | Receive No | ✅ same |
| 15 | Received Date | Date | ✅ same |
| 16 | Receive Type | Type | ✅ same |
| 17 | Bill No · Party · Godown · Remarks | Header | ✅ same |
| 18 | Item · Qty · Thaan · Rate · Disc% · Amt · Disc Amt · Elongation · Gauge + Add | Lines | ✅ same |
| 19 | Advance · GST Amt · Totals | Totals | ✅ same |
| 20 | Save · Edit/Search · Reset | Save | ✅ same |

#### Physical Stock

| # | SBAC field | Kanha where | Status |
|---|------------|-------------|--------|
| 21 | Physical Stock No * auto | Physical No | ✅ same |
| 22 | Store Name * | Store / Godown | ✅ same |
| 23 | Branch | Branch | ✅ same |
| 24 | Date | Date | ✅ same |
| 25 | Store Keeper | Store Keeper | ✅ same |
| 26 | Project Manager | Project Manager | ✅ same |
| 27 | Item · Item Code · Unit · Current Stock · Stock Entry · Entry Unit · Physical Stock · Item Desc + Add | Lines | ✅ same |
| 28 | Search · Save · Search/Edit | Save draft | ✅ same |
| 29 | Draft → Approve (SBAC ApprovalMaster) | **Approve** applies variance | ✅ same |

#### Godown Transfer

| # | Field | Kanha where | Status |
|---|-------|-------------|--------|
| 30 | From Godown · To Godown · multi-line qty · Notes | Godown Transfer voucher | ✅ same |

---

### 10) Accounts (Ledger + Vouchers)

- **SBAC URL(s):**  
  - Ledger: https://erp.sbacindia.in/Account/LedgerSub.aspx  
  - Vouchers: https://erp.sbacindia.in/Account/Voucherdenominations.aspx?Vtype=Payment&Etype=Cr (+ Receipt/Contra/Journal/CN/DN)  
- **Kanha:** `#/books` (+ `#/accounting` reports / period lock)  
- **APIs:** `/api/books/ledgers` · vouchers · daybook · cash/bank · trial-balance · pnl · balance-sheet · `/api/outstanding/summary`

#### Create Ledger

| # | SBAC field / option | Kanha where | Status |
|---|---------------------|-------------|--------|
| 1 | Ledger Name | Create Ledger | ✅ same |
| 2 | Under Group (Parent) | parent_code | ✅ same |
| 3 | Opening Date | Opening Date | ✅ same |
| 4 | Opening Balance | Opening Balance | ✅ same |
| 5 | Bal Type Debit / Credit | Dr/Cr | ✅ same |
| 6 | Currency | Currency | ✅ same |
| 7 | Other Value % | Other Value % | ✅ same |
| 8 | Other Value Status Yes/No | Other Value Status | ✅ same |
| 9 | Bill-wise Add grid | Create Ledger bill-wise grid → `custom.bill_wise` | ✅ same |
| 10 | Code · Type · Is Group (Kanha COA asset/liability/equity/income/expense) | Kanha COA | ✅ same |
| 11 | Submit / Reset / Search | Save | ✅ same |
| 12 | OB > 0 → journal vs equity `3100` | Auto OB post | ✅ same |

#### Voucher family

| # | SBAC field / option | Kanha where | Status |
|---|---------------------|-------------|--------|
| 13 | Voucher Type Payment / Receipt / Contra / Journal / CN / DN | Voucher drawers | ✅ same |
| 14 | Voucher No auto | Auto | ✅ same |
| 15 | Voucher Date | Date | ✅ same |
| 16 | Bill / On Account (`receipt_type`) | Bill / On Account | ✅ same |
| 17 | Cost Centre | Cost Centre | ✅ same |
| 18 | Bank/Cash · Party accounts (from/to) | from_account / to_account | ✅ same |
| 19 | Party Name | Party | ✅ same |
| 20 | Amount · Adjust Amount | Amounts | ✅ same |
| 21 | Currency · Exchange Rate · Convert Amount | FX fields | ✅ same |
| 22 | Cheque No · Cheque Date | Cheque fields | ✅ same |
| 23 | Sub Narration · Narration · Remarks | Narration | ✅ same |
| 24 | ADD · Debit/Credit totals · Submit / Search / Print | Balanced lines + save | ✅ same |

#### Reports / Outstanding (flow)

| # | SBAC screen | Kanha where | Status |
|---|-------------|-------------|--------|
| 25 | Day Book / Cash / Bank | `#/books` | ✅ same |
| 26 | Trial Balance / P&L / Balance Sheet | `#/books` · `#/accounting` | ✅ same |
| 27 | Party Outstanding Buyer/Vendor/All | Outstanding summary | ✅ same |
| 28 | Payment Request A3M flow | `#/payments-ops` | 🟡 partial |
| 29 | Voucher Approval / Delete | `#/books` Send Approval · Approve/Reject · Delete/Reverse | ✅ same |

---

### 11) HR (Employee + Leave + Attendance + Salary + Loans)

- **SBAC URL(s):** EmployeeMaster, LeaveApplication, EmpWiseLeaveEntry, ProcessSalaryAttendance, employeewiseloandetail, BalajiSalaryConfirmation (+ Approval / Slip)  
- **Kanha:** `#/hrms` (+ `#/hr-flow`)  
- **APIs:** `/api/hrms/employees` · attendance · leaves · loans · payroll run/confirm/approve/payslips/disbursements

#### Employee Master

| # | SBAC field / option | Kanha where | Status |
|---|---------------------|-------------|--------|
| 1 | Photo / Sign upload | Skip binary; refs in custom later | 🟡 partial |
| 2 | Gender Male/Female | Gender | ✅ same |
| 3 | First Name · Emp ID (Kanha auto EMP…) | Name / Emp ID | ✅ same |
| 4 | Department · Designation | Dept / Desig | ✅ same |
| 5 | PF No · ESI No | PF / ESI | ✅ same |
| 6 | Company Email · Personal Email | Emails | ✅ same |
| 7 | Biometric ID · Phone | Biometric / Phone | ✅ same |
| 8 | DOB · Joining Date | DOB / Join | ✅ same |
| 9 | User Name · SMTP Type Self/Department | User / SMTP | ✅ same |
| 10 | Father Name / Phone / Profession | Father block | ✅ same |
| 11 | Mother Name / Phone / Profession | Mother block | ✅ same |
| 12 | Status Active/Inactive · Status Date | Status | ✅ same |
| 13 | Experience / Fresher checkboxes | Experience flags | ✅ same |
| 14 | Salary / Imprest · Salary amt · Month | Salary mode block | ✅ same |
| 15 | Grade A–E · Increment · Inc. Month | Grade / Increment | ✅ same |
| 16 | Latitude · Longitude · Distance (geo fence) | GPS fields | ✅ same |
| 17 | Docs: Aadhaar / PAN / Licence / Voter nos + file uploads | Doc nos; files light | 🟡 partial |
| 18 | Bank · IFSC · A/c · Holder · Branch · Type | Bank block | ✅ same |
| 19 | Address 1 (State/City/Pin/Contact) · Address 2 | Addresses | ✅ same |
| 20 | Owner Name · Owner Phone | Owner | ✅ same |
| 21 | Save · Reset · Edit | Save | ✅ same |
| 22 | GPS consent on hire | Kanha extra | ✅ same (Kanha) |

#### Leave

| # | SBAC field | Kanha where | Status |
|---|------------|-------------|--------|
| 23 | Employee · From · To · Reason · Save | Leave Application | ✅ same |
| 24 | Emp-wise: Month · EL/CL grid | Leave balances / types | 🟡 partial |
| 25 | leave_type casual/sick/earned/unpaid/comp_off + approve/reject | Kanha leave decide | ✅ same (Kanha richer types) |

#### Attendance process

| # | SBAC field / option | Kanha where | Status |
|---|---------------------|-------------|--------|
| 26 | Month · From · To · Employee optional | Process month | ✅ same |
| 27 | Status Pending / Processed | Status | ✅ same |
| 28 | Search · Reset | Process | ✅ same |
| 29 | Fill missing weekdays | Kanha process | ✅ same |

#### Employee Loan

| # | SBAC field | Kanha where | Status |
|---|------------|-------------|--------|
| 30 | Employee · Loan Date · Loan Amount · EMI Amount · EMI Start Date · Remarks | Loan entry | ✅ same |
| 31 | Save → Loan Approval | decide approve | ✅ same |

#### Salary Confirmation / Payroll

| # | SBAC field | Kanha where | Status |
|---|---------------------|-------------|--------|
| 32 | Filters: Grade · Dept · Employee | Payroll filters | ✅ same |
| 33 | Qualification · Pay scale · Basic · Grade pay | Salary components | ✅ same |
| 34 | Salary mode Bank/Cash · Month · A/c No · Status Confirmed/Pending | Confirm | ✅ same |
| 35 | DA · HRA · Incentive · Allowance · OT · Gross | Earnings | ✅ same |
| 36 | Loan · Advance · ESI · PF · Tax · Leave DD · Deduct · Net | Deductions | ✅ same |
| 37 | Paid leave · Save | Confirm save | ✅ same |
| 38 | Flow: Run Payroll (draft) → Confirm → Approve → Disburse + payslip / NEFT demo · Active loan EMI | `#/hrms` / `#/hr-flow` | ✅ same |

---

### 12) MIS / Bridges (Tally + other ERPs)

- **SBAC URL(s):** FrmmisReport, TallyErpparentmapping, Tallyerror, InactiveLedgerForTally, InactiveItemForTally (+ BIMISPANEL)  
- **Kanha:** `#/mis` · `#/bridges` · `#/bi` · `#/books`  
- **APIs:** `/api/mis/*` · `/api/bridges` · tally parent-mapping / inactive / errors / export-import · `erp/{target}/export`

#### MIS Report filters

| # | SBAC field / option | Kanha where | Status |
|---|---------------------|-------------|--------|
| 1 | View Summary / Detail | MIS filter strip | ✅ same |
| 2 | Doc type radios: Lead · Quotation · Order · Dispatch · Challan · Invoice · PO · MRN · Purchase Invoice · Executive · Follow · Issue · Receive | Doc filters / charts | ✅ same |
| 3 | Date kind · From · To | Date filters | ✅ same |
| 4 | Vendor · Buyer · Executive | Party / executive filters | ✅ same |
| 5 | Main group · Item code · Item | Item filters | ✅ same |
| 6 | Status Pending / Running / Confirmed / Closed Won/Lost | Status | ✅ same |
| 7 | Sale type Cash / Tax | Sale type | ✅ same |
| 8 | Export · Reset | CSV export / reset | ✅ same |
| 9 | Sales analysis · Party OS · Attendance · Stock ageing | MIS desk panels | ✅ same |

#### Tally / bridge fields

| # | SBAC field | Kanha where | Status |
|---|------------|-------------|--------|
| 10 | ERP Parent (Sundry Debtors, Bank Accounts, …) · Tally Name · Submit | `#/bridges` Parent mapping → `settings_json.tally_sync.parent_mappings` | ✅ same |
| 11 | Tally Error: From · To · Doc type Contra/Journal/Payment/Purchase/Receipt/Sale · Search | Error queue filter | ✅ same |
| 12 | Inactive Ledger: party search → mark inactive for Tally | Inactive ledgers | ✅ same |
| 13 | Inactive Item: item search → mark inactive | Inactive items | ✅ same |
| 14 | Tally export/import packs kept | Tally pack `kanha_tally_pack_v1` | ✅ same |

#### Kanha-only (Bridges)

| Extra | Where |
|-------|--------|
| Marg / Busy / Vyapar / Other ERP packs + hooks | `#/bridges` |
| Dual-mode channels · Outbox · Bridge Intelligence · Third-party hooks | `#/bridges` |
| BI Panel | `#/bi` |

---

### 13) Extras (WhatsApp Login · Meta · OCR · Chase · PWA)

- **SBAC URL(s):** https://erp.sbacindia.in/user/whatsappset.aspx (WhatsApp Login). Baaki extras = Kanha layer (MAP #8), SBAC clone nahi.  
- **Kanha:** `#/extras` · `#/whatsapp` · `#/automation` · `#/ai` · `#/apps` · `#/documents`

#### WhatsApp Login (SBAC parity)

| # | SBAC field / option | Kanha where | Status |
|---|---------------------|-------------|--------|
| 1 | Mobile No | WhatsApp Login | ✅ same |
| 2 | Type Default / User | Type | ✅ same |
| 3 | Create Instance | Create Instance | ✅ same |
| 4 | Get QR | Get QR | ✅ same |
| 5 | Reset | Reset | ✅ same |
| 6 | User grid checkboxes / session list | User-wise sessions + enable/remove | ✅ same |

#### Kanha-only extras (global on top of parity)

| # | Extra | Where / API | Status |
|---|-------|-------------|--------|
| 7 | Meta Cloud webhook (no QR when keys set) | `GET/POST /api/meta/whatsapp/webhook` | Kanha-only ✅ |
| 8 | Bill OCR demo (GSTIN · Invoice No · Amount · Date · Party · Phone) | `#/extras` · `POST /api/extras/ocr/parse` | Kanha-only ✅ |
| 9 | Android / iOS store URL slots | `#/apps` · `/api/extras/store-slots` | Kanha-only ✅ |
| 10 | PWA Install (Add to Home Screen) | Browser / `#/apps` | Kanha-only ✅ |
| 11 | Ops Chase Pack — Overdue AR → WhatsApp draft → Send one/all | `#/extras` · `#/whatsapp` · `#/payments-ops` | Kanha-only ✅ |
| 12 | AI dock “Chase overdue” | `#/ai` | Kanha-only ✅ |
| 13 | Hub tiles: Chase · WhatsApp · OCR · AI/Agents · Automation · PWA · Bridges · e-Invoice · Compliance · MIS · GPS · Documents | `#/extras` | Kanha-only ✅ |
| 14 | Native store publish / cloud OCR vendor | Optional go-live | ❌ not yet (optional) |

---

## Still later / not deepened (from MAP)

Ye SBAC screens menu me hain, lekin **field-level compare docs abhi deep nahi** (ya optional polish):

| Area | SBAC screens (short) | Kanha hint |
|------|----------------------|------------|
| **Admin** | Create User, User Rights, Branch, Company Edit, Approvals, Delete SO/DC/Invoice, B2B Portal, Assign App Menu | `#/settings`, `#/approvals`, `#/dealers` |
| **Master extras** | Unit/Category/Group masters standalone, Godown Master page, Country/State/City/Area, Vehicle, Holiday, SMTP, Template, Currency, Discount/Party-wise rate/MRP masters, Back Date Entry, Alert Master | `#/inventory` / `#/settings` (partial) |
| **Marketing** | Lead Source, Lead Entry, Lead Management, Lead Report, Pending Lead→SO, Visit Planner, Cost Center | `#/crm`, `#/visit`, `#/followup` |
| **Sales extras** | Cash Invoice deep, Sales Return deep, E-invoice create, Order/Payment Followup deep, Commission process, DSR reports | `#/sales`, `#/pos`, `#/logistics`, `#/followup` |
| **Purchase extras** | Purchase Requisition, RFQ rate → PO deep, Purchase Return deep, PO Report | `#/purchase`, `#/rfq`, `#/indents` |
| **Production / Indents** | Indent create/approval, Production Challan, Job Work Order | `#/indents`, `#/manufacturing` |
| **Accounts extras** | Payment Request A3M full, Voucher delete admin | `#/payments-ops`, `#/approvals` |
| **HR extras** | Grade Pay / Leave / Salary heads masters standalone, Print Salary Slip polish | `#/hrms` |
| **MIS Panel / Visit / Task / Service** | Sales Pipeline, Map Tracking, Module MIS Panels, Visit, Task Assignment, Complaint generate | `#/bi`, `#/mis`, `#/visit`, `#/tasks`, `#/service` |
| **Optional go-live** | Native Play/App Store publish, cloud OCR vendor | `#/apps`, `#/extras` |

---

## How to compare checklist (step-by-step)

1. **Do windows:** SBAC `https://erp.sbacindia.in` + Kanha `https://kanha-erp.onrender.com` (login `admin@kanhaerp.com` / `admin123`).
2. **Rule yaad rakho:** Client ka data copy mat karo — dono pe **fresh entry** se compare.
3. **Party:** SBAC Master → Party Master (Add Party, saari section checkboxes open) ↔ Kanha `#/crm` → + Party. GST Search try karo. Address/Bank/Contact Add multi-line check.
4. **Item:** SBAC Item Master (saari sections) ↔ `#/inventory` → + Item. Rate List + Conversion + Packing Add check. Note: Country list Kanha pe common set + Other.
5. **Sales chain:** SBAC Create SO → Pending SO→Challan → Pending Challan→Invoice ↔ `#/sales` same flow buttons. Direct Invoice bhi compare.
6. **Purchase chain:** Vendor/Party as vendor → PO → Pending PO→MRN → Pending MRN→PI (+ RCM) ↔ `#/purchase`. SBAC PI-for-PO page error pe Material Receipt / Cash form se fields match karo.
7. **Store:** Issue / Receive / Physical (+ Approve) / Transfer ↔ `#/store`.
8. **Accounts:** Create Ledger + ek Payment + ek Receipt + Day Book / Outstanding ↔ `#/books`.
9. **HR:** Employee → Leave → Attendance process → Loan → Payroll Confirm/Approve ↔ `#/hrms` (tour `#/hr-flow` pe dekh sakte ho).
10. **MIS / Tally:** MIS filters ↔ `#/mis`; Parent mapping / Inactive / Errors ↔ `#/bridges`.
11. **Extras:** SBAC WhatsApp Login ↔ `#/extras` / `#/whatsapp`; baaki Chase/OCR/PWA/AI = Kanha bonus.
12. **Mark status:** Jo field SBAC pe dikhta hai lekin Kanha pe missing/alag feel → note 🟡/❌ — ye client review list ban jaati hai.
13. **UI confuse mat ho:** Look alag hoga (Kanha design). Compare **fields + working + flow**, pixel copy nahi.

---

*Source: `docs/client-erp/MAP.md` + `docs/client-erp/forms/*.md` (live deepen 2026-08-02) · Kanha routes from `frontend/js/app.js`.*
