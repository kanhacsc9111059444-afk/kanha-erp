# Form: HR (Employee + Leave + Attendance + Salary + Loans) — field-level parity

**Sources (live 2026-08-02):**
- Employee Master: https://erp.sbacindia.in/Master/EmployeeMaster.aspx  
- Leave Application: https://erp.sbacindia.in/HR/LeaveApplication.aspx  
- Emp-wise Leave Entry: https://erp.sbacindia.in/HR/EmpWiseLeaveEntry.aspx  
- Process Salary Attendance: https://erp.sbacindia.in/Master/ProcessSalaryAttendance.aspx  
- Employee Loan Entry: https://erp.sbacindia.in/hr/employeewiseloandetail.aspx  
- Salary Confirmation: https://erp.sbacindia.in/Balaji/BalajiSalaryConfirmation.aspx  
- Related: Salary Approval · Print Salary Slip · Loan Approval  

**Kanha UI:** `#/hrms` (+ `#/hr-flow`)  
**Status:** ✅ Complete — live scan 2026-08-02

## Locked
- Fresh entry only — no SBAC employee/salary import  
- Same fields + same working  
- Kanha design · HRMS desk  

## Employee Master (`EmployeeMaster.aspx`)
| Field | Control |
|-------|---------|
| Photo / Sign upload | `photoupload` · `FileUpload10` (Kanha: skip binary; refs in custom later) |
| Gender | `ddlgender` Male/Female |
| First Name · Emp ID | `txtfirstname` · `txtempid` (Kanha auto EMP…) |
| Department · Designation | `ddldept` · `ddldesig` |
| PF No · ESI No | `txtpfno` · `txtesino` |
| Company Email · Personal Email | `txtcompemail` · `txtemail` |
| Biometric ID · Phone | `txtBiometricID` · `txtphone` |
| DOB · Joining Date | `dtpdob_*` · `dtpjoining_*` |
| User Name · SMTP Type | `txtuser` · `ddlsmtptype` Self/Department |
| Father Name / Phone / Profession | `txtffirstname` · `txtfphone` · `txtfprof` |
| Mother Name / Phone / Profession | `txtmfirstname` · `txtmphone` · `txtmprof` |
| Status · Status Date | `ddlStatus` Active/Inactive · `dtpStatusDate_*` |
| Experience / Fresher | `chkexperience` · `chkfresher` |
| Salary / Imprest · Salary amt · Month | `rdosalary` · `rdoimprest` · `txtsalary` · `ddlmonth` |
| Grade · Increment · Inc. Month | `ddlgrade` A–E · `txtincrement` · `ddlincrementmonth` |
| Latitude · Longitude · Distance | GPS geo fence |
| Docs: Aadhaar / PAN / Licence / Voter | nos + file uploads |
| Bank · IFSC · A/c · Holder · Branch · Type | Salary/Personal Account |
| Address 1 (State/City/Pin/Contact) · Address 2 | |
| Owner Name · Owner Phone | |
| Save · Reset · Edit | |

Kanha: extras → `employees.custom` · GPS consent on hire (Kanha extra).

## Leave Application (`LeaveApplication.aspx`)
| Field | Control |
|-------|---------|
| Employee | `ddlempname` |
| From · To | `dtpfromdate_*` · `dtptodate_*` |
| Reason | `txtreason` |
| Save | `btnsave` |

Emp-wise Leave Entry: Employee · Month · EL/CL grid (`txtel`/`txtcl`).  
Kanha: leave_type casual/sick/earned/unpaid/comp_off + approve/reject.

## Process Salary Attendance
| Field | Control |
|-------|---------|
| Month | `ddlMonth` |
| From · To | `DTP_From_*` · `DTP_To_*` |
| Employee | `ddlEmployee` (optional) |
| Status | `ddlstatus` Pending / Processed |
| Search · Reset | |

Kanha: fill missing weekdays · optional employee + date range.

## Employee Loan Entry
| Field | Control |
|-------|---------|
| Employee | `ddlemployee` |
| Loan Date | `dtploandate_*` |
| Loan Amount | `txtloanamount` |
| EMI Amount | `txtemiamount` |
| EMI Start Date | `dtpemistartdate_*` |
| Remarks | `txtremarks` |
| Save → Loan Approval | |

## Salary Confirmation (`BalajiSalaryConfirmation.aspx`)
| Field | Notes |
|-------|--------|
| Grade · Dept · Employee | filters |
| Qualification · Pay scale · Basic · Grade pay | |
| Salary mode Bank/Cash · Month · A/c No · Status | Confirmed/Pending |
| DA · HRA · Incentive · Allowance · OT · Gross | |
| Loan · Advance · ESI · PF · Tax · Leave DD · Deduct · Net | |
| Paid leave · Save | |

Kanha flow: Run Payroll (`draft`) → Confirm → Approve → Disburse (+ payslip / NEFT demo). Active loan EMI on run.

## Flow
```
Employee Master
  → Attendance mark / Process month + Leave apply → approve
  → Employee Loan → approve (EMI on payroll)
  → Run Payroll → Confirm → Approve → Disburse + Payslip
```

## Kanha APIs
- `POST/PUT /api/hrms/employees` · `POST …/exit`
- `POST /api/hrms/attendance` · `POST …/attendance/process-month` (from/to/employee)
- `POST /api/hrms/leaves` · `POST …/leaves/{id}/decide`
- `GET/POST /api/hrms/loans` · `POST …/loans/{id}/decide` (loan_date · EMI start)
- `POST /api/hrms/payroll/run` · confirm · approve · payslips · disbursements

## Next
Field track complete.
