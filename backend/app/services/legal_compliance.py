"""
KanhaERP Legal & Compliance registry.

Nothing is deleted. Risky capabilities stay in code but are:
- SAFE — ok for normal use with disclaimer
- NEEDS_APPROVAL — blocked until admin grants company-level approval
- HIGHLIGHT_ILLEGAL_RISK — never treat as live; watermarked; needs conscious decision

Not formal legal advice — operational guardrails for Indian SME ERP.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import SyncState

LEGAL_KEY = "legal.feature_approvals"
SALARY_POLICY_KEY = "hrms.salary_policy"

# Default salary policy — labour-law aware, sales can be target-first
DEFAULT_SALARY_POLICY: dict[str, Any] = {
    "mode": "labour_safe",  # labour_safe | target_first | hybrid
    "attendance_cut_enabled": False,  # option: allow LOP / absence cut when needed
    "attendance_cut_requires_reason": True,
    "max_attendance_cut_pct": 0,  # 0 = no cut; when enabled, cap e.g. 50
    "sales_pay_basis": "target",  # target | attendance | hybrid
    "office_pay_basis": "attendance_soft",  # attendance_soft logs only unless cut enabled
    "target_full_pay_threshold_pct": 100,  # hit target → full basic (sales)
    "incentive_on_overachieve": True,
    "labour_note": (
        "Code on Wages / Payment of Wages: arbitrary deductions restricted. "
        "Use documented policy + employee notice before attendance cuts. "
        "PF/ESIC figures are illustrative — not EPFO filing."
    ),
}


REGISTRY: list[dict[str, Any]] = [
    {
        "id": "aadhaar_face_auth",
        "title": "Aadhaar Face RD / UIDAI attendance",
        "area": "HRMS / Identity",
        "level": "NEEDS_APPROVAL",
        "status_in_product": "not_wired",
        "why": (
            "UIDAI Face Auth needs AUA/Sub-AUA + ASA, MeitY portal approval, "
            "Aadhaar Data Vault / HSM. Private use without approval is not allowed."
        ),
        "recommendation": "Keep planned — enable only after MeitY/UIDAI approval. Do not store face photos.",
        "law_refs": ["Aadhaar Act", "UIDAI Auth regulations", "Good Governance Rules 2025"],
        "gate": True,
        "delete": False,
    },
    {
        "id": "device_face_attendance",
        "title": "Phone Face ID / fingerprint → Present (no photo store)",
        "area": "HRMS",
        "level": "SAFE",
        "status_in_product": "planned_safe",
        "why": "On-device biometric unlock is not Aadhaar CIDR auth; no biometric template in ERP.",
        "recommendation": "Preferred attendance primary + 1-tap fallback.",
        "law_refs": ["DPDP Act (minimal data)"],
        "gate": False,
        "delete": False,
    },
    {
        "id": "demo_einvoice_irn",
        "title": "Local DEMO IRN / e-Invoice generate",
        "area": "GST / Logistics",
        "level": "HIGHLIGHT_ILLEGAL_RISK",
        "status_in_product": "active_demo",
        "why": (
            "Printing/sharing DEMO IRN as if filed on GSTN/NIC is misrepresentation. "
            "Local generate is OK only with clear DEMO watermark."
        ),
        "recommendation": "Keep DEMO- prefix forever until live GSP. Never claim filed.",
        "law_refs": ["CGST Rules e-invoice", "Misrepresentation / IT Act"],
        "gate": False,
        "delete": False,
        "watermark": "DEMO — NOT FILED WITH GSTN",
    },
    {
        "id": "live_gsp_push",
        "title": "Live GSP / NIC e-Invoice & e-Way push",
        "area": "GST",
        "level": "NEEDS_APPROVAL",
        "status_in_product": "gated",
        "why": "Real filing needs registered GSP + GSTIN credentials + company consent.",
        "recommendation": "Approve only when GSP keys + CA/process ready.",
        "law_refs": ["CGST e-invoice / e-Way"],
        "gate": True,
        "delete": False,
    },
    {
        "id": "demo_eway_lookalike",
        "title": "E-Way bill numbers that look portal-like",
        "area": "GST / Logistics",
        "level": "HIGHLIGHT_ILLEGAL_RISK",
        "status_in_product": "mitigated",
        "why": "Numeric NIC-style EWB can be mistaken for real portal bill.",
        "recommendation": "Force DEMO-EWB- prefix on all local generates.",
        "law_refs": ["CGST e-Way rules"],
        "gate": False,
        "delete": False,
        "watermark": "DEMO — NOT GENERATED ON NIC",
    },
    {
        "id": "whatsapp_live_bulk",
        "title": "WhatsApp live / bulk chase autos",
        "area": "Comms",
        "level": "NEEDS_APPROVAL",
        "status_in_product": "gated",
        "why": "Commercial messaging needs Meta template approval + customer opt-in (TRAI/IT Act).",
        "recommendation": "Demo adapter OK; live send only after approval + opt-in policy.",
        "law_refs": ["IT Act", "TRAI commercial SMS/WA norms", "Meta Business"],
        "gate": True,
        "delete": False,
    },
    {
        "id": "demo_neft_paid",
        "title": "Demo NEFT marked paid + UTR",
        "area": "Payroll / Bank",
        "level": "HIGHLIGHT_ILLEGAL_RISK",
        "status_in_product": "mitigated",
        "why": "Showing paid+UTR without bank transfer can be used to claim salary paid falsely.",
        "recommendation": "Status demo_paid + DEMO-NEFT- UTR only until live bank API.",
        "law_refs": ["Payment of Wages / Code on Wages", "Trust / audit fraud risk"],
        "gate": False,
        "delete": False,
        "watermark": "DEMO — NO BANK TRANSFER",
    },
    {
        "id": "live_bank_neft",
        "title": "Live bank / RazorpayX salary push",
        "area": "Payroll",
        "level": "NEEDS_APPROVAL",
        "status_in_product": "gated",
        "why": "Real money movement needs corporate banking + dual control.",
        "recommendation": "Approve with finance dual-approval SOP.",
        "law_refs": ["Banking regulations", "Internal controls"],
        "gate": True,
        "delete": False,
    },
    {
        "id": "gps_always_on",
        "title": "Field GPS tracking (phone GPS, no Maps key)",
        "area": "HRMS / Privacy",
        "level": "NEEDS_APPROVAL",
        "status_in_product": "consent_model_offer_letter",
        "why": (
            "Location is personal data (DPDP). Kanha model: written consent in offer letter + "
            "explicit OK when employee installs the app. Company keeps that approval on record."
        ),
        "recommendation": (
            "1) Offer letter clause for field/sales roles. "
            "2) App install — employee taps Accept. "
            "3) ERP stores consent (who, when, version). "
            "4) Live ping only for consented employees. Work-hours / field roles only."
        ),
        "law_refs": ["DPDP Act 2023", "Workplace privacy", "Offer letter / employment contract"],
        "gate": True,
        "delete": False,
        "consent_model": "offer_letter_plus_app_install",
    },
    {
        "id": "payroll_statutory_filing",
        "title": "PF / ESIC / PT as statutory filing software",
        "area": "Payroll",
        "level": "NEEDS_APPROVAL",
        "status_in_product": "illustrative_only",
        "why": "Current PF/ESIC math is illustrative — not EPFO/ESIC portal filing.",
        "recommendation": "Disclaimer always on. Live filing via licensed payroll/CA only after approval.",
        "law_refs": ["EPF Act", "ESIC Act"],
        "gate": True,
        "delete": False,
    },
    {
        "id": "salary_attendance_cut",
        "title": "Salary cut linked to attendance (LOP)",
        "area": "Payroll / Labour",
        "level": "NEEDS_APPROVAL",
        "status_in_product": "optional_policy",
        "why": (
            "Code on Wages restricts arbitrary deductions. Cuts need written policy, "
            "employee notice, and lawful heads (absence/LOP as per standing orders)."
        ),
        "recommendation": (
            "Default OFF. Enable only with labour_safe mode + reason on each cut. "
            "Sales roles can use target_first (full pay on target) without attendance cut."
        ),
        "law_refs": ["Code on Wages 2019", "Payment of Wages Act", "Standing orders"],
        "gate": True,
        "delete": False,
    },
    {
        "id": "personal_data_store",
        "title": "Employee/customer phone, bank, GSTIN storage",
        "area": "Privacy",
        "level": "SAFE",
        "status_in_product": "active",
        "why": "Necessary for ERP operations; still DPDP purpose limitation + security.",
        "recommendation": "Keep with access control; no Aadhaar photos; purge demo when needed.",
        "law_refs": ["DPDP Act 2023"],
        "gate": False,
        "delete": False,
    },
    {
        "id": "blackout_freeze",
        "title": "Emergency blackout (write freeze)",
        "area": "Resilience",
        "level": "SAFE",
        "status_in_product": "active",
        "why": "Does not wipe statutory records; operational freeze only.",
        "recommendation": "Unlock before GST/payroll due dates. Keep period lock for books hygiene.",
        "law_refs": ["Record retention (CGST / IT)"],
        "gate": False,
        "delete": False,
    },
    {
        "id": "govt_approved_claim",
        "title": "Claiming government / NIC / UIDAI approved",
        "area": "Marketing",
        "level": "HIGHLIGHT_ILLEGAL_RISK",
        "status_in_product": "forbidden_copy",
        "why": "False govt-approved claims = misleading advertising.",
        "recommendation": "Never claim. Product already avoids this — keep it that way.",
        "law_refs": ["Consumer Protection / unfair trade"],
        "gate": False,
        "delete": False,
    },
]


def _sync_row(db: Session, key: str, company_id: int) -> SyncState:
    full = f"{key}.{company_id}"
    row = db.query(SyncState).filter(SyncState.key == full).first()
    if not row:
        row = SyncState(key=full, value={})
        db.add(row)
        db.flush()
    return row


def get_approvals(db: Session, company_id: int) -> dict[str, Any]:
    row = _sync_row(db, LEGAL_KEY, company_id)
    return dict(row.value or {})


def is_feature_approved(db: Session, company_id: int, feature_id: str) -> bool:
    item = next((x for x in REGISTRY if x["id"] == feature_id), None)
    if not item or not item.get("gate"):
        return True
    approvals = get_approvals(db, company_id)
    entry = approvals.get(feature_id) or {}
    return bool(entry.get("approved"))


def assert_feature_approved(db: Session, company_id: int, feature_id: str) -> None:
    if is_feature_approved(db, company_id, feature_id):
        return
    item = next((x for x in REGISTRY if x["id"] == feature_id), {"title": feature_id})
    raise HTTPException(
        403,
        f"Legal gate: '{item.get('title')}' needs company approval. "
        f"Open Compliance → Legal & Risk board → Approve (conscious decision). Feature not deleted.",
    )


def set_feature_approval(
    db: Session,
    company_id: int,
    *,
    feature_id: str,
    approved: bool,
    note: str = "",
    updated_by: str = "",
) -> dict[str, Any]:
    item = next((x for x in REGISTRY if x["id"] == feature_id), None)
    if not item:
        raise HTTPException(404, f"Unknown feature {feature_id}")
    if item.get("level") == "HIGHLIGHT_ILLEGAL_RISK" and approved and item.get("gate"):
        # Highlight items that are gated still need conscious approve; allow with strong note
        pass
    if item["id"] == "govt_approved_claim" and approved:
        raise HTTPException(400, "Cannot approve false government-approved marketing claims.")
    row = _sync_row(db, LEGAL_KEY, company_id)
    val = dict(row.value or {})
    val[feature_id] = {
        "approved": approved,
        "note": (note or "")[:500],
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "updated_by": updated_by or "",
    }
    row.value = val
    db.flush()
    return val[feature_id]


def legal_board(db: Session, company_id: int) -> dict[str, Any]:
    approvals = get_approvals(db, company_id)
    items = []
    counts = {"SAFE": 0, "NEEDS_APPROVAL": 0, "HIGHLIGHT_ILLEGAL_RISK": 0, "approved_gates": 0, "blocked_gates": 0}
    for item in REGISTRY:
        ap = approvals.get(item["id"]) or {}
        approved = bool(ap.get("approved"))
        gated = bool(item.get("gate"))
        effective = "open" if (not gated or approved) else "blocked_until_approval"
        if item["level"] in counts:
            counts[item["level"]] += 1
        if gated:
            if approved:
                counts["approved_gates"] += 1
            else:
                counts["blocked_gates"] += 1
        items.append(
            {
                **item,
                "approved": approved if gated else None,
                "approval_meta": ap or None,
                "effective": effective,
                "deleted": False,
            }
        )
    return {
        "items": items,
        "counts": counts,
        "policy": (
            "Nothing deleted. HIGHLIGHT = treat as demo/risk, never as live proof. "
            "NEEDS_APPROVAL = blocked until conscious admin approve. "
            "Not formal legal advice — consult CA/advocate for go-live."
        ),
        "salary_policy": get_salary_policy(db, company_id),
    }


def get_salary_policy(db: Session, company_id: int) -> dict[str, Any]:
    row = _sync_row(db, SALARY_POLICY_KEY, company_id)
    merged = {**DEFAULT_SALARY_POLICY, **(row.value or {})}
    return merged


def set_salary_policy(db: Session, company_id: int, body: dict[str, Any], updated_by: str = "") -> dict[str, Any]:
    row = _sync_row(db, SALARY_POLICY_KEY, company_id)
    cur = {**DEFAULT_SALARY_POLICY, **(row.value or {})}
    mode = body.get("mode", cur["mode"])
    if mode not in ("labour_safe", "target_first", "hybrid"):
        raise HTTPException(400, "mode must be labour_safe | target_first | hybrid")
    cut_on = bool(body.get("attendance_cut_enabled", cur["attendance_cut_enabled"]))
    if cut_on and not is_feature_approved(db, company_id, "salary_attendance_cut"):
        raise HTTPException(
            403,
            "Enable attendance salary cut only after approving 'salary_attendance_cut' on Legal board "
            "(labour-law conscious decision).",
        )
    max_pct = float(body.get("max_attendance_cut_pct", cur["max_attendance_cut_pct"]) or 0)
    if max_pct < 0 or max_pct > 50:
        raise HTTPException(400, "max_attendance_cut_pct must be 0–50 (labour-safe cap)")
    cur.update(
        {
            "mode": mode,
            "attendance_cut_enabled": cut_on,
            "attendance_cut_requires_reason": bool(
                body.get("attendance_cut_requires_reason", cur["attendance_cut_requires_reason"])
            ),
            "max_attendance_cut_pct": max_pct if cut_on else 0,
            "sales_pay_basis": body.get("sales_pay_basis", cur["sales_pay_basis"]),
            "office_pay_basis": body.get("office_pay_basis", cur["office_pay_basis"]),
            "target_full_pay_threshold_pct": float(
                body.get("target_full_pay_threshold_pct", cur["target_full_pay_threshold_pct"]) or 100
            ),
            "incentive_on_overachieve": bool(body.get("incentive_on_overachieve", cur["incentive_on_overachieve"])),
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "updated_by": updated_by or "",
        }
    )
    if cur["sales_pay_basis"] not in ("target", "attendance", "hybrid"):
        raise HTTPException(400, "sales_pay_basis invalid")
    row.value = cur
    db.flush()
    return cur


def get_performance_map(db: Session, company_id: int) -> dict[str, Any]:
    row = _sync_row(db, "hrms.performance", company_id)
    return dict(row.value or {})


def set_employee_performance(
    db: Session,
    company_id: int,
    *,
    employee_id: int,
    monthly_target: float,
    achieved: float,
    note: str = "",
) -> dict[str, Any]:
    row = _sync_row(db, "hrms.performance", company_id)
    val = dict(row.value or {})
    pct = round((achieved / monthly_target) * 100, 1) if monthly_target > 0 else 0.0
    entry = {
        "employee_id": employee_id,
        "monthly_target": monthly_target,
        "achieved": achieved,
        "target_achieved_pct": pct,
        "note": (note or "")[:300],
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }
    val[str(employee_id)] = entry
    row.value = val
    db.flush()
    return entry


def get_employee_target_pct(db: Session, company_id: int, employee_id: int) -> float | None:
    m = get_performance_map(db, company_id)
    entry = m.get(str(employee_id))
    if not entry:
        return None
    return float(entry.get("target_achieved_pct") or 0)


CONSENT_VERSION = "v1-offer-letter-app-install"
OFFER_LETTER_GPS_CLAUSE = (
    "Field / sales / marketing roles: during working hours, the Company may collect device GPS "
    "location via the official KanhaERP mobile/PWA app for field visit, attendance support, and "
    "safety — not for off-duty surveillance. Location is used only for employment purposes. "
    "By signing this offer letter and accepting on app install, the employee consents to this. "
    "Consent can be reviewed with HR. Photos of face are not stored for this purpose."
)


def get_consent_map(db: Session, company_id: int) -> dict[str, Any]:
    row = _sync_row(db, "hrms.employee_consent", company_id)
    return dict(row.value or {})


def get_employee_consent(db: Session, company_id: int, employee_id: int) -> dict[str, Any]:
    return dict(get_consent_map(db, company_id).get(str(employee_id)) or {})


def record_employee_consent(
    db: Session,
    company_id: int,
    *,
    employee_id: int,
    offer_letter_ack: bool = True,
    app_install_ack: bool = True,
    gps_consent: bool = True,
    source: str = "offer_letter_app_install",
    note: str = "",
    recorded_by: str = "",
) -> dict[str, Any]:
    if not (offer_letter_ack and app_install_ack and gps_consent):
        raise HTTPException(400, "GPS tracking needs offer letter + app install + GPS consent all accepted")
    row = _sync_row(db, "hrms.employee_consent", company_id)
    val = dict(row.value or {})
    entry = {
        "employee_id": employee_id,
        "gps_consent": True,
        "offer_letter_ack": True,
        "app_install_ack": True,
        "consent_version": CONSENT_VERSION,
        "clause": OFFER_LETTER_GPS_CLAUSE,
        "source": source,
        "note": (note or "")[:400],
        "consented_at": datetime.utcnow().isoformat() + "Z",
        "recorded_by": recorded_by or "",
    }
    val[str(employee_id)] = entry
    row.value = val
    db.flush()
    return entry


def revoke_employee_consent(
    db: Session,
    company_id: int,
    *,
    employee_id: int,
    note: str = "",
    recorded_by: str = "",
) -> dict[str, Any]:
    row = _sync_row(db, "hrms.employee_consent", company_id)
    val = dict(row.value or {})
    entry = {
        "employee_id": employee_id,
        "gps_consent": False,
        "offer_letter_ack": False,
        "app_install_ack": False,
        "consent_version": CONSENT_VERSION,
        "revoked_at": datetime.utcnow().isoformat() + "Z",
        "note": (note or "Revoked")[:400],
        "recorded_by": recorded_by or "",
    }
    val[str(employee_id)] = entry
    row.value = val
    db.flush()
    return entry


def assert_employee_gps_allowed(db: Session, company_id: int, employee_id: int) -> dict[str, Any]:
    """Company enables feature once; each employee needs offer-letter + app-install consent on record."""
    assert_feature_approved(db, company_id, "gps_always_on")
    c = get_employee_consent(db, company_id, employee_id)
    if not c.get("gps_consent"):
        raise HTTPException(
            403,
            "Employee GPS consent missing. Record offer-letter + app-install approval "
            "(HRMS → Consent / on hire). Consent stays on file — no tracking without it.",
        )
    return c


def compute_payslip_line(
    *,
    emp: Any,
    policy: dict[str, Any],
    attendance_days: int,
    working_days: int,
    target_achieved_pct: float | None,
    cut_reason: str = "",
) -> dict[str, Any]:
    """Labour-aware payslip line. Illustrative PF/ESIC only."""
    basic = float(getattr(emp, "basic_salary", 0) or 0)
    dept = (getattr(emp, "department", "") or "").lower()
    desig = (getattr(emp, "designation", "") or "").lower()
    is_sales = any(k in dept or k in desig for k in ("sales", "marketing", "field", "bd"))
    basis = policy["sales_pay_basis"] if is_sales else policy["office_pay_basis"]
    mode = policy.get("mode") or "labour_safe"

    attendance_cut = 0.0
    incentive = 0.0
    notes: list[str] = []
    pay_basic = basic

    # Target-first for sales: full pay if target hit
    if is_sales and basis in ("target", "hybrid") and target_achieved_pct is not None:
        thr = float(policy.get("target_full_pay_threshold_pct") or 100)
        if target_achieved_pct >= thr:
            pay_basic = basic
            notes.append(f"Sales target {target_achieved_pct:.0f}% ≥ {thr:.0f}% → full basic (family/growth model)")
            if policy.get("incentive_on_overachieve") and target_achieved_pct > thr:
                incentive = round(basic * min(0.2, (target_achieved_pct - thr) / 100 * 0.5), 2)
                notes.append(f"Overachieve incentive ₹{incentive}")
        elif basis == "target":
            # Below target: still no silent attendance cut; shortfall note only unless cut enabled
            notes.append(f"Sales target {target_achieved_pct:.0f}% below {thr:.0f}% — review growth plan")
            if mode == "hybrid" and policy.get("attendance_cut_enabled") and working_days > 0:
                absent = max(0, working_days - attendance_days)
                raw = basic * (absent / working_days)
                cap = basic * (float(policy.get("max_attendance_cut_pct") or 0) / 100)
                attendance_cut = round(min(raw, cap), 2) if cap > 0 else 0
        elif basis == "hybrid" and policy.get("attendance_cut_enabled"):
            pass  # handled below

    # Optional attendance cut (gated + reason)
    if policy.get("attendance_cut_enabled") and working_days > 0:
        if is_sales and basis == "target" and target_achieved_pct is not None:
            thr = float(policy.get("target_full_pay_threshold_pct") or 100)
            if target_achieved_pct >= thr:
                attendance_cut = 0.0  # target protects full pay
                notes.append("Attendance cut skipped — target met (policy)")
        else:
            if policy.get("attendance_cut_requires_reason") and not (cut_reason or "").strip():
                notes.append("Attendance cut available but no reason — cut not applied (labour-safe)")
            else:
                absent = max(0, working_days - attendance_days)
                raw = basic * (absent / working_days) if working_days else 0
                cap_pct = float(policy.get("max_attendance_cut_pct") or 0)
                cap = basic * (cap_pct / 100)
                attendance_cut = round(min(raw, cap), 2) if cap_pct > 0 else 0
                if attendance_cut > 0:
                    notes.append(f"LOP/absence cut ₹{attendance_cut} · reason: {cut_reason[:120]}")

    taxable_basic = max(0, pay_basic - attendance_cut)
    pf = round(min(taxable_basic * 0.12, 1800), 2)
    esic = round(taxable_basic * 0.0075, 2)
    net = round(taxable_basic - pf - esic + incentive, 2)
    return {
        "employee_id": emp.id,
        "name": emp.full_name,
        "department": getattr(emp, "department", "") or "",
        "is_sales_role": is_sales,
        "pay_basis": basis,
        "policy_mode": mode,
        "basic": basic,
        "attendance_days": attendance_days,
        "working_days": working_days,
        "target_achieved_pct": target_achieved_pct,
        "attendance_cut": attendance_cut,
        "incentive": incentive,
        "pf": pf,
        "esic": esic,
        "net": net,
        "notes": notes,
        "statutory_disclaimer": "PF/ESIC illustrative — not EPFO/ESIC portal filing",
        "bank_account": getattr(emp, "bank_account", "") or "",
        "ifsc": getattr(emp, "ifsc", "") or "",
        "bank_name": getattr(emp, "bank_name", "") or "",
    }
