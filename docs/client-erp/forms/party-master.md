# Form: Party Master (Add Party) — field-level parity

**Source:** https://erp.sbacindia.in/Balaji/BalajiPartymaster.aspx  
**Tabs:** Add Party | View Party  
**Kanha UI:** `#/crm` → + Party  
**Status:** ✅ Complete — live expand scan 2026-08-02 (all section checkboxes opened)

## Locked
- Fresh entry only — no SBAC data import  
- Same fields + same working (GST Search, Under Account, Branch multi, Address/Bank/Contact Add)  
- Kanha design  
- Extras separate (`Kanha Role`)

## Primary (live)
| Field | Control | Notes |
|-------|---------|-------|
| GST Number | `txtTINNO` | + **GST Search** (`btnsrch`) |
| Party Code | `txtfinalpartycode` | auto |
| Domestic / Export | `ddlpartynature` | |
| Party Name | `txtPartyName` | required |
| Under Account | `ddlunderaccount` | ledger list |
| File As | `txtfileas` | |
| Whatsapp Number | `txtWhatsappNumber` | required |
| Joinning Date | `dtpjoinning_*` | d/m/y |
| W. Area | `txtwarea` | |
| Repeat Order Days | `txtrepeatdays` | |
| Branch List | `chkbranchlist_*` | multi-checkbox |
| Show in Order followup | `ddlshoworderfollowup` | Yes/No |
| Transport | `ddltransportname` | |
| Agent Name | `ddlagentname` | |
| Actions | Submit / Delete / Reset | |

### Section checkboxes
| Section | Checkbox |
|---------|----------|
| Employee Details | `CheckBox1` |
| Address Details | `CheckBox3` |
| Account Details | `CheckBox2` |
| Company Details | `chkAcd` |
| Bank Details | `CheckBox4` |
| Contact Details | `CheckBox5` |
| Export Details | `chkexport` |

## Employee Details (`e1` / `emid`)
Department · Designation · Email · Mobile No. · Reporting Person

## Address Details (`add1`) — multi via Add / Reset
Address Type* · Country* (`ddlregion`) · State* · City* · Area* · Address · Pin Code · Telephone · Email · Mobile · Website · Fax No.  
*(Shipping = Address Type “Shiping Address” — no separate Shipping section)*

## Account Details (`acc`)
Opening Balance · Cr/Dr · Currency · Credit Limit · Credit Limit(Days) · Grade (A–D) · Pan No. · CTS No. · Pvt Marka · Sales Target · Ecc No. · Status (Active/NonActive) · Tcs Allow · Tds Allow

## Company Details (`d1`)
Company type · Customer Type · Head Quarter · Area · Discount Percente · Discount Name · Alias · Remarks · Show Remarks

## Bank Details (`b1`) — multi via Add / Reset
Bank Name* · Account Holder* · Account No.* · Swift Code · IFSC Code · Region/Country* · State · City · Address · Pin Code · Telephone · Email · Mobile · Website · Fax No.

## Contact Details (`c`) — multi via Add / Reset
Contact Person* · Job Title · Designation* · Mobile · Whatsapp Number · Telephone · DOB · Associate Date · Email · Commission %

## Export Details (`exportdiv`)
Packing Charge · Pre-Carriage by · Place of Receipt by Pre-Carrier · Port of Discharge · Port of Loading · LUT/Bond No · Final Destination

## Kanha APIs
- `POST /api/crm/customers` · `PUT /api/crm/customers/{id}`
- `POST /api/crm/gst-lookup`
- Storage: columns + `custom` JSON (`addresses[]`, `banks[]`, `contacts[]`, `employee`, `company`, `export`)

## Next
Sales Order deep fields — live expand + one-pass implement
