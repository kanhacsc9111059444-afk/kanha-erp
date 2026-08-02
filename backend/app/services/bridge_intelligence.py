"""
Bridge Intelligence — FULL internal learning curriculum.

Phases (none skipped):
  1 INGEST     — hook inbox, bridge outbox, tally buffer, self snapshot
  2 NORMALIZE  — parties / vouchers / lines / vendors
  3 COMPARE    — external vs Kanha cross-check
  4 SCORE      — accuracy + trust
  5 TAXONOMY   — gap kinds ranked
  6 SAFE_FIX   — fill empty GSTIN/barcode/party only (never money overwrite)
  7 RULES      — recurring patterns → internal playbook
  8 ADVANCE    — readiness for less bridge dependency
  9 RETAIN     — curriculum progress + history persisted

Goal: learn from bridges/hooks → harden native Kanha → grow trust → standalone production.
"""
from __future__ import annotations

import secrets
from collections import Counter
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import Company, Customer, Invoice, Product, PurchaseInvoice, Vendor

LEARNING_PHASES: list[dict[str, str]] = [
    {"id": "ingest", "name": "1 · Ingest", "desc": "Hook inbox + outbox + Tally buffer + self snapshot"},
    {"id": "normalize", "name": "2 · Normalize", "desc": "Party / voucher / line / vendor shapes"},
    {"id": "compare", "name": "3 · Compare", "desc": "External vs Kanha cross-check"},
    {"id": "score", "name": "4 · Score", "desc": "Accuracy + trust score"},
    {"id": "taxonomy", "name": "5 · Taxonomy", "desc": "Gap kinds ranked for focus"},
    {"id": "safe_fix", "name": "6 · Safe fix", "desc": "Fill empty fields only — no money overwrite"},
    {"id": "rules", "name": "7 · Rules", "desc": "Recurring patterns → internal playbook"},
    {"id": "advance", "name": "8 · Advance", "desc": "Native readiness / reduce bridge dependency"},
    {"id": "retain", "name": "9 · Retain", "desc": "Persist curriculum + history"},
]


def _sj(db: Session, company_id: int) -> tuple[Company, dict]:
    co = db.get(Company, company_id)
    if not co:
        raise ValueError("Company not found")
    return co, dict(co.settings_json or {})


def _save(db: Session, co: Company, sj: dict) -> None:
    co.settings_json = sj
    db.add(co)
    db.commit()
    db.refresh(co)


def _norm_gstin(g: str | None) -> str:
    return "".join(ch for ch in (g or "").upper() if ch.isalnum())


def _norm_name(n: str | None) -> str:
    return " ".join((n or "").lower().split())


def _money(v: Any) -> float:
    try:
        return round(float(v or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _phase_status(bi: dict) -> list[dict[str, Any]]:
    done = set(bi.get("phases_done") or [])
    last = dict(bi.get("last_phase_report") or {})
    out = []
    for p in LEARNING_PHASES:
        out.append(
            {
                **p,
                "done": p["id"] in done,
                "last": last.get(p["id"]),
            }
        )
    return out


def get_state(db: Session, company_id: int) -> dict[str, Any]:
    _, sj = _sj(db, company_id)
    bi = dict(sj.get("bridge_intelligence") or {})
    trust = float(bi.get("trust_score") or 50)
    return {
        "trust_score": trust,
        "runs": int(bi.get("runs") or 0),
        "last_run_at": bi.get("last_run_at"),
        "last_accuracy": bi.get("last_accuracy"),
        "gap_totals": dict(bi.get("gap_totals") or {}),
        "improvements_applied": int(bi.get("improvements_applied") or 0),
        "history": list(reversed(bi.get("history") or []))[:25],
        "open_gaps": list(bi.get("open_gaps") or [])[:50],
        "learnings": list(bi.get("learnings") or [])[:40],
        "playbook": list(bi.get("playbook") or [])[:30],
        "phases": _phase_status(bi),
        "phases_complete": len(set(bi.get("phases_done") or [])),
        "phases_total": len(LEARNING_PHASES),
        "advance": dict(bi.get("advance") or {}),
        "curriculum_pct": round(100.0 * len(set(bi.get("phases_done") or [])) / max(1, len(LEARNING_PHASES)), 1),
        "pitch": (
            "Internal learning: ingest→compare→score→safe-fix→rules→advance. "
            "Bridge se seekho, native harden karo, trust badhao, phir kam bridge pe bhi production."
        ),
    }


def _add_gap(
    gaps: list,
    *,
    kind: str,
    severity: str,
    title: str,
    detail: dict,
    fixable: bool = False,
    phase: str = "compare",
) -> None:
    gaps.append(
        {
            "id": f"gap_{secrets.token_hex(3)}",
            "kind": kind,
            "severity": severity,
            "title": title,
            "detail": detail,
            "fixable": fixable,
            "status": "open",
            "phase": phase,
        }
    )


# ── Phase 1: INGEST ─────────────────────────────────────────────────────────


def phase_ingest(db: Session, company_id: int, *, limit: int = 40) -> dict[str, Any]:
    _, sj = _sj(db, company_id)
    inbox = list(sj.get("third_party_inbox") or [])[-limit:]
    outbox = list(sj.get("bridge_outbox") or [])[-limit:]
    # payloads from outbox (tally sales etc.)
    out_payloads = []
    for j in outbox:
        pl = j.get("payload")
        if isinstance(pl, dict) and pl:
            out_payloads.append({"source": f"outbox:{j.get('action')}", "payload": pl})

    self_inv = (
        db.query(Invoice)
        .filter(Invoice.company_id == company_id)
        .order_by(Invoice.id.desc())
        .limit(20)
        .all()
    )
    self_snap = [
        {
            "source": "self",
            "payload": {
                "number": i.number,
                "total": i.total,
                "tax": i.tax,
                "lines": i.lines or [],
                "customer_id": i.customer_id,
            },
        }
        for i in self_inv
    ]

    samples = []
    for e in inbox:
        samples.append(
            {
                "source": f"hook:{e.get('preset') or 'ext'}",
                "payload": dict(e.get("payload") or {}),
                "event": e.get("event"),
            }
        )
    samples.extend(out_payloads)
    samples.extend(self_snap)

    return {
        "phase": "ingest",
        "counts": {
            "inbox": len(inbox),
            "outbox_payloads": len(out_payloads),
            "self_invoices": len(self_inv),
            "total_samples": len(samples),
        },
        "samples": samples,
    }


# ── Phase 2: NORMALIZE ──────────────────────────────────────────────────────


def _normalize_one(raw: dict[str, Any], source: str = "") -> dict[str, Any]:
    p = dict(raw or {})
    party = p.get("party") or p.get("customer") or p.get("party_name") or p.get("name") or p.get("vendor") or ""
    gstin = _norm_gstin(p.get("gstin") or p.get("party_gstin") or p.get("vendor_gstin") or "")
    number = str(p.get("number") or p.get("invoice_number") or p.get("voucher") or p.get("bill_no") or "").strip()
    total = _money(p.get("total") or p.get("amount") or p.get("grand_total"))
    lines_in = p.get("lines") or p.get("items") or []
    lines = []
    if isinstance(lines_in, list):
        for ln in lines_in:
            if not isinstance(ln, dict):
                continue
            lines.append(
                {
                    "sku": str(ln.get("sku") or ln.get("item_code") or "").strip(),
                    "name": str(ln.get("name") or ln.get("item") or "").strip(),
                    "qty": _money(ln.get("qty") or ln.get("quantity") or 1),
                    "rate": _money(ln.get("rate") or ln.get("price")),
                    "amount": _money(ln.get("amount") or ln.get("line_total")),
                    "barcode": str(ln.get("barcode") or "").strip(),
                }
            )
    return {
        "source": source,
        "party": str(party)[:120],
        "gstin": gstin,
        "number": number,
        "total": total,
        "tax": _money(p.get("tax") or p.get("gst")),
        "lines": lines,
        "kind": "vendor" if p.get("vendor") or p.get("vendor_gstin") else "customer",
        "phone": str(p.get("phone") or p.get("customer_phone") or "")[:20],
        "email": str(p.get("email") or "")[:80],
        "address": str(p.get("address") or p.get("billing_address") or "")[:200],
    }


def phase_normalize(samples: list[dict[str, Any]]) -> dict[str, Any]:
    normalized = []
    for s in samples:
        payload = dict(s.get("payload") or {})
        if s.get("event") and not payload.get("event"):
            payload["event"] = s["event"]
        # attach customer from self snapshot
        if s.get("source") == "self" and payload.get("customer_id"):
            payload.setdefault("party", f"cust#{payload['customer_id']}")
        normalized.append(_normalize_one(payload, source=str(s.get("source") or "")))
    return {
        "phase": "normalize",
        "count": len(normalized),
        "docs": normalized,
    }


# ── Phase 3: COMPARE ────────────────────────────────────────────────────────


def compare_normalized(db: Session, company_id: int, doc: dict[str, Any]) -> dict[str, Any]:
    gaps: list[dict] = []
    checks = {"matched": 0, "partial": 0, "missing": 0, "conflict": 0}
    source = doc.get("source") or "ext"
    party = doc.get("party") or ""
    gstin = doc.get("gstin") or ""
    number = doc.get("number") or ""
    total = _money(doc.get("total"))
    is_self = str(source).startswith("self")

    # --- Party / vendor ---
    cust = None
    vend = None
    if doc.get("kind") == "vendor" or "vendor" in str(source):
        if gstin:
            for v in db.query(Vendor).filter(Vendor.company_id == company_id).all():
                if _norm_gstin(getattr(v, "gstin", "") or "") == gstin:
                    vend = v
                    break
        if not vend and party and not party.startswith("cust#"):
            pn = _norm_name(party)
            for v in db.query(Vendor).filter(Vendor.company_id == company_id).all():
                if _norm_name(v.name) == pn:
                    vend = v
                    break
        if party or gstin:
            if vend:
                checks["matched"] += 1
                if gstin and not _norm_gstin(getattr(vend, "gstin", "") or ""):
                    checks["partial"] += 1
                    _add_gap(
                        gaps,
                        kind="vendor_gstin_missing",
                        severity="medium",
                        title=f"Vendor '{vend.code}' GSTIN empty — external has value",
                        detail={"vendor_id": vend.id, "gstin": gstin, "source": source},
                        fixable=True,
                    )
            elif not is_self:
                checks["missing"] += 1
                _add_gap(
                    gaps,
                    kind="vendor_missing",
                    severity="medium",
                    title=f"External vendor not in Kanha · {party or gstin}",
                    detail={"party": party, "gstin": gstin, "source": source},
                    fixable=True,
                )
    else:
        if gstin:
            for c in db.query(Customer).filter(Customer.company_id == company_id).all():
                if _norm_gstin(getattr(c, "gstin", "") or "") == gstin:
                    cust = c
                    break
        if not cust and party:
            if str(party).startswith("cust#"):
                try:
                    cust = db.get(Customer, int(str(party).split("#")[1]))
                except Exception:
                    cust = None
            else:
                pn = _norm_name(party)
                for c in db.query(Customer).filter(Customer.company_id == company_id).all():
                    if _norm_name(c.name) == pn:
                        cust = c
                        break
        if party or gstin:
            if cust:
                checks["matched"] += 1
                kanha_g = _norm_gstin(getattr(cust, "gstin", "") or "")
                if gstin and not kanha_g:
                    checks["partial"] += 1
                    _add_gap(
                        gaps,
                        kind="party_gstin_missing",
                        severity="medium",
                        title=f"Kanha party '{cust.code}' me GSTIN khali — external has value",
                        detail={"customer_id": cust.id, "gstin": gstin, "source": source},
                        fixable=True,
                    )
                elif gstin and kanha_g and gstin != kanha_g:
                    checks["conflict"] += 1
                    _add_gap(
                        gaps,
                        kind="party_gstin_conflict",
                        severity="high",
                        title=f"GSTIN mismatch · Kanha {kanha_g} vs external {gstin}",
                        detail={"customer_id": cust.id, "kanha": kanha_g, "external": gstin},
                        fixable=False,
                    )
                if doc.get("phone") and not (getattr(cust, "phone", "") or "").strip():
                    _add_gap(
                        gaps,
                        kind="party_phone_missing",
                        severity="low",
                        title=f"Party '{cust.code}' phone empty — external has phone",
                        detail={"customer_id": cust.id, "phone": doc.get("phone")},
                        fixable=True,
                    )
                if doc.get("email") and not (getattr(cust, "email", "") or "").strip():
                    _add_gap(
                        gaps,
                        kind="party_email_missing",
                        severity="low",
                        title=f"Party '{cust.code}' email empty — external has email",
                        detail={"customer_id": cust.id, "email": doc.get("email")},
                        fixable=True,
                    )
                if doc.get("address") and not (getattr(cust, "billing_address", "") or "").strip():
                    _add_gap(
                        gaps,
                        kind="party_address_missing",
                        severity="low",
                        title=f"Party '{cust.code}' address empty — external has address",
                        detail={"customer_id": cust.id, "address": doc.get("address")},
                        fixable=True,
                    )
            elif not is_self:
                checks["missing"] += 1
                _add_gap(
                    gaps,
                    kind="party_missing",
                    severity="medium",
                    title=f"External party not in Kanha · {party or gstin}",
                    detail={"party": party, "gstin": gstin, "source": source},
                    fixable=True,
                )

    # --- Sales / purchase invoice ---
    inv = None
    pi = None
    if number:
        inv = db.query(Invoice).filter(Invoice.company_id == company_id, Invoice.number == number).first()
        if not inv:
            pi = (
                db.query(PurchaseInvoice)
                .filter(PurchaseInvoice.company_id == company_id, PurchaseInvoice.number == number)
                .first()
            )
    if number or total:
        if inv:
            checks["matched"] += 1
            if total and abs(_money(inv.total) - total) > 1.0 and not is_self:
                checks["conflict"] += 1
                _add_gap(
                    gaps,
                    kind="invoice_amount_conflict",
                    severity="high",
                    title=f"{number} amount mismatch · Kanha {_money(inv.total)} vs ext {total}",
                    detail={"invoice_id": inv.id, "kanha": inv.total, "external": total},
                    fixable=False,
                )
            if not (inv.lines or []) and (total or doc.get("lines")):
                checks["partial"] += 1
                _add_gap(
                    gaps,
                    kind="invoice_lines_empty",
                    severity="medium",
                    title=f"{inv.number} Kanha lines empty",
                    detail={"invoice_id": inv.id, "external_lines": len(doc.get("lines") or [])},
                    fixable=bool(doc.get("lines")),
                )
        elif pi:
            checks["matched"] += 1
            if total and abs(_money(pi.total) - total) > 1.0 and not is_self:
                checks["conflict"] += 1
                _add_gap(
                    gaps,
                    kind="pi_amount_conflict",
                    severity="high",
                    title=f"PI {number} amount mismatch · Kanha {_money(pi.total)} vs ext {total}",
                    detail={"purchase_invoice_id": pi.id, "kanha": pi.total, "external": total},
                    fixable=False,
                )
        elif number and not is_self:
            checks["missing"] += 1
            _add_gap(
                gaps,
                kind="invoice_missing",
                severity="low",
                title=f"External voucher {number} Kanha me nahi",
                detail={"number": number, "total": total, "source": source},
                fixable=False,
            )

    # Self-audit flags
    if is_self and inv:
        cust2 = db.get(Customer, inv.customer_id) if inv.customer_id else None
        if cust2 and not _norm_gstin(getattr(cust2, "gstin", "") or ""):
            _add_gap(
                gaps,
                kind="self_party_gstin_empty",
                severity="medium",
                title=f"Self-audit: {cust2.code} GSTIN empty",
                detail={"customer_id": cust2.id, "invoice": inv.number},
                fixable=False,
                phase="compare",
            )
        if not (inv.lines or []):
            _add_gap(
                gaps,
                kind="self_invoice_lines_empty",
                severity="medium",
                title=f"Self-audit: {inv.number} has no lines",
                detail={"invoice_id": inv.id},
                fixable=False,
            )

    # --- Products ---
    for ln in doc.get("lines") or []:
        sku = ln.get("sku") or ""
        name = ln.get("name") or ""
        if not sku and not name:
            continue
        prod = None
        if sku:
            prod = db.query(Product).filter(Product.company_id == company_id, Product.sku == sku).first()
        if not prod and name:
            nn = _norm_name(name)
            for p in db.query(Product).filter(Product.company_id == company_id).limit(300):
                if _norm_name(p.name) == nn:
                    prod = p
                    break
        if prod:
            checks["matched"] += 1
            if not (prod.barcode or "").strip() and ln.get("barcode"):
                _add_gap(
                    gaps,
                    kind="product_barcode_missing",
                    severity="low",
                    title=f"SKU {prod.sku} barcode empty — external has barcode",
                    detail={"product_id": prod.id, "barcode": str(ln.get("barcode"))[:32]},
                    fixable=True,
                )
            if _money(prod.sale_price) <= 0 and _money(ln.get("rate")) > 0:
                _add_gap(
                    gaps,
                    kind="product_price_empty",
                    severity="low",
                    title=f"SKU {prod.sku} sale_price empty — external rate {_money(ln.get('rate'))}",
                    detail={"product_id": prod.id, "rate": ln.get("rate")},
                    fixable=True,
                )
        elif not is_self:
            checks["missing"] += 1
            _add_gap(
                gaps,
                kind="product_missing",
                severity="low",
                title=f"Product not in Kanha · {sku or name}",
                detail={"sku": sku, "name": name, "rate": ln.get("rate")},
                fixable=True,
            )

    total_checks = max(1, sum(checks.values()))
    score = (
        checks["matched"] * 100 + checks["partial"] * 60 + checks["missing"] * 20 + checks["conflict"] * 0
    ) / total_checks
    if checks["conflict"]:
        score = max(0, score - checks["conflict"] * 15)

    return {
        "source": source,
        "checks": checks,
        "accuracy": round(score, 1),
        "gaps": gaps,
        "payload_summary": {"party": party[:80], "gstin": gstin, "number": number, "total": total},
    }


def compare_payload_to_kanha(db: Session, company_id: int, payload: dict[str, Any], *, source: str = "hook") -> dict[str, Any]:
    """Public helper used by inbound hooks."""
    doc = _normalize_one(payload, source=source)
    return compare_normalized(db, company_id, doc)


# ── Phase 4–9 orchestrator ──────────────────────────────────────────────────


def phase_score(compare_results: list[dict]) -> dict[str, Any]:
    accuracies = [r["accuracy"] for r in compare_results] or [70.0]
    accuracy = round(sum(accuracies) / len(accuracies), 1)
    return {"phase": "score", "accuracy": accuracy, "samples": len(compare_results)}


def phase_taxonomy(all_gaps: list[dict]) -> dict[str, Any]:
    counts = Counter(g.get("kind") for g in all_gaps)
    ranked = [{"kind": k, "count": c} for k, c in counts.most_common(20)]
    return {"phase": "taxonomy", "ranked": ranked, "total_gaps": len(all_gaps)}


def phase_rules(all_gaps: list[dict], bi: dict) -> dict[str, Any]:
    """Recurring gap kinds → internal playbook rules."""
    counts = Counter(g.get("kind") for g in all_gaps)
    playbook = list(bi.get("playbook") or [])
    existing = {r.get("kind") for r in playbook}
    new_rules = []
    advice = {
        "party_gstin_missing": "Always capture GSTIN on customer create / SO.",
        "party_gstin_conflict": "Human verify GSTIN before filing e-Invoice.",
        "invoice_lines_empty": "Block post invoice without lines (print/data quality).",
        "product_missing": "Create SKU before billing or map from external code.",
        "product_barcode_missing": "Barcode mandatory for POS SKUs.",
        "vendor_gstin_missing": "Vendor GSTIN required for ITC / RCM.",
        "self_invoice_lines_empty": "Native data quality: fill demo lines or block empty post.",
        "invoice_amount_conflict": "Do not auto-fix — reconcile with books/Tally.",
    }
    for kind, cnt in counts.items():
        if cnt < 2:
            continue
        if kind in existing:
            # bump evidence
            for r in playbook:
                if r.get("kind") == kind:
                    r["evidence"] = int(r.get("evidence") or 0) + cnt
                    r["updated_at"] = _now()
            continue
        rule = {
            "id": f"rule_{secrets.token_hex(3)}",
            "kind": kind,
            "evidence": cnt,
            "advice": advice.get(kind, "Review recurring gap and harden native form validation."),
            "created_at": _now(),
        }
        playbook.append(rule)
        new_rules.append(rule)
        existing.add(kind)
    return {"phase": "rules", "playbook": playbook[-40:], "new_rules": new_rules}


def phase_advance(trust: float, accuracy: float, high_gaps: int, playbook: list) -> dict[str, Any]:
    ready_native = trust >= 80 and accuracy >= 85 and high_gaps == 0
    ready_hybrid = trust >= 65 and accuracy >= 70
    return {
        "phase": "advance",
        "ready_reduce_bridge": ready_native,
        "ready_hybrid_stable": ready_hybrid,
        "recommendation": (
            "Native-first: accounting channel can move toward native; keep hooks for audit only."
            if ready_native
            else (
                "Stay Hybrid: keep Tally/Marg bridge; run Learn weekly + Safe improve."
                if ready_hybrid
                else "Learning mode: ingest more external samples; fix high gaps before reducing bridge."
            )
        ),
        "next_actions": [
            "Run Learn Full after every Marg/Tally sync",
            "Safe improve empty masters",
            "Human resolve high conflicts",
            f"Playbook rules active: {len(playbook)}",
        ],
        "trust_score": trust,
        "accuracy": accuracy,
        "high_gaps": high_gaps,
    }


def apply_safe_improvements(db: Session, company_id: int, *, limit: int = 30) -> dict[str, Any]:
    """Phase 6 — safe fills only."""
    co, sj = _sj(db, company_id)
    bi = dict(sj.get("bridge_intelligence") or {})
    open_gaps = list(bi.get("open_gaps") or [])
    applied = []
    skipped = []
    phases_done = set(bi.get("phases_done") or [])

    for g in open_gaps:
        if len(applied) >= limit:
            break
        if g.get("status") != "open" or not g.get("fixable"):
            continue
        kind = g.get("kind")
        detail = dict(g.get("detail") or {})

        if kind == "party_gstin_missing":
            cust = db.get(Customer, int(detail.get("customer_id") or 0))
            gstin = _norm_gstin(detail.get("gstin"))
            if cust and cust.company_id == company_id and gstin and not _norm_gstin(cust.gstin or ""):
                cust.gstin = gstin
                db.add(cust)
                g["status"] = "applied"
                applied.append({"gap": g["title"], "action": f"GSTIN → {cust.code}"})
            else:
                skipped.append(g["title"])
        elif kind == "party_phone_missing":
            cust = db.get(Customer, int(detail.get("customer_id") or 0))
            phone = str(detail.get("phone") or "").strip()
            if cust and cust.company_id == company_id and phone and not (cust.phone or "").strip():
                cust.phone = phone[:20]
                db.add(cust)
                g["status"] = "applied"
                applied.append({"gap": g["title"], "action": f"Phone → {cust.code}"})
            else:
                skipped.append(g["title"])
        elif kind == "party_email_missing":
            cust = db.get(Customer, int(detail.get("customer_id") or 0))
            email = str(detail.get("email") or "").strip()
            if cust and cust.company_id == company_id and email and not (cust.email or "").strip():
                cust.email = email[:120]
                db.add(cust)
                g["status"] = "applied"
                applied.append({"gap": g["title"], "action": f"Email → {cust.code}"})
            else:
                skipped.append(g["title"])
        elif kind == "party_address_missing":
            cust = db.get(Customer, int(detail.get("customer_id") or 0))
            addr = str(detail.get("address") or "").strip()
            if cust and cust.company_id == company_id and addr and not (cust.billing_address or "").strip():
                cust.billing_address = addr[:500]
                db.add(cust)
                g["status"] = "applied"
                applied.append({"gap": g["title"], "action": f"Address → {cust.code}"})
            else:
                skipped.append(g["title"])
        elif kind == "party_missing":
            name = (detail.get("party") or "").strip()
            gstin = _norm_gstin(detail.get("gstin"))
            if name and not name.startswith("cust#"):
                code = f"EXT-{(gstin or name)[:6].upper()}".replace(" ", "")[:16]
                exists = db.query(Customer).filter(Customer.company_id == company_id, Customer.code == code).first()
                if not exists:
                    db.add(
                        Customer(
                            company_id=company_id,
                            code=code,
                            name=name[:200],
                            gstin=gstin or None,
                            billing_address="Imported via bridge intelligence",
                        )
                    )
                    g["status"] = "applied"
                    applied.append({"gap": g["title"], "action": f"Customer {code}"})
                else:
                    skipped.append(g["title"])
            else:
                skipped.append(g["title"])
        elif kind == "vendor_gstin_missing":
            vend = db.get(Vendor, int(detail.get("vendor_id") or 0))
            gstin = _norm_gstin(detail.get("gstin"))
            if vend and vend.company_id == company_id and gstin and not _norm_gstin(vend.gstin or ""):
                vend.gstin = gstin
                db.add(vend)
                g["status"] = "applied"
                applied.append({"gap": g["title"], "action": f"Vendor GSTIN → {vend.code}"})
            else:
                skipped.append(g["title"])
        elif kind == "vendor_missing":
            name = (detail.get("party") or "").strip()
            gstin = _norm_gstin(detail.get("gstin"))
            if name:
                code = f"VEX-{(gstin or name)[:6].upper()}".replace(" ", "")[:16]
                exists = db.query(Vendor).filter(Vendor.company_id == company_id, Vendor.code == code).first()
                if not exists:
                    db.add(Vendor(company_id=company_id, code=code, name=name[:200], gstin=gstin or None))
                    g["status"] = "applied"
                    applied.append({"gap": g["title"], "action": f"Vendor {code}"})
                else:
                    skipped.append(g["title"])
            else:
                skipped.append(g["title"])
        elif kind == "product_barcode_missing":
            prod = db.get(Product, int(detail.get("product_id") or 0))
            bc = str(detail.get("barcode") or "").strip()
            if prod and prod.company_id == company_id and bc and not (prod.barcode or "").strip():
                prod.barcode = bc[:64]
                db.add(prod)
                g["status"] = "applied"
                applied.append({"gap": g["title"], "action": f"Barcode → {prod.sku}"})
            else:
                skipped.append(g["title"])
        elif kind == "product_price_empty":
            prod = db.get(Product, int(detail.get("product_id") or 0))
            rate = _money(detail.get("rate"))
            if prod and prod.company_id == company_id and rate > 0 and _money(prod.sale_price) <= 0:
                prod.sale_price = rate
                db.add(prod)
                g["status"] = "applied"
                applied.append({"gap": g["title"], "action": f"Sale price → {prod.sku}"})
            else:
                skipped.append(g["title"])
        elif kind == "product_missing":
            sku = str(detail.get("sku") or "").strip() or f"EXT-{secrets.token_hex(3).upper()}"
            name = str(detail.get("name") or sku).strip()
            rate = _money(detail.get("rate"))
            exists = db.query(Product).filter(Product.company_id == company_id, Product.sku == sku).first()
            if not exists:
                db.add(
                    Product(
                        company_id=company_id,
                        sku=sku[:32],
                        name=name[:200],
                        sale_price=rate or 0,
                        cost_price=round((rate or 0) * 0.7, 2),
                        gst_rate=18,
                        category="Bridge-learned",
                    )
                )
                g["status"] = "applied"
                applied.append({"gap": g["title"], "action": f"Product {sku}"})
            else:
                skipped.append(g["title"])
        elif kind == "invoice_lines_empty" and detail.get("external_lines"):
            # cannot invent lines without payload — skip unless we stored them
            skipped.append(g["title"] + " (need external lines payload)")
        else:
            skipped.append(g["title"])

    bi["open_gaps"] = open_gaps
    bi["improvements_applied"] = int(bi.get("improvements_applied") or 0) + len(applied)
    if applied:
        bi["trust_score"] = min(98.0, float(bi.get("trust_score") or 50) + min(6.0, len(applied) * 0.4))
    phases_done.add("safe_fix")
    bi["phases_done"] = sorted(phases_done)
    last = dict(bi.get("last_phase_report") or {})
    last["safe_fix"] = {"applied": len(applied), "at": _now()}
    bi["last_phase_report"] = last
    sj["bridge_intelligence"] = bi
    _save(db, co, sj)

    return {
        "ok": True,
        "phase": "safe_fix",
        "applied": applied,
        "skipped": skipped[:30],
        "count": len(applied),
        "trust_score": bi.get("trust_score"),
        "message": f"Safe improvements · {len(applied)} applied (money never auto-overwritten)",
        "state": get_state(db, company_id),
    }


def run_learn_cycle(db: Session, company_id: int, *, limit: int = 40, auto_safe_fix: bool = False) -> dict[str, Any]:
    """Run FULL curriculum phases 1–5,7–9 (6 optional via auto_safe_fix or separate API)."""
    co, sj = _sj(db, company_id)
    bi = dict(sj.get("bridge_intelligence") or {})
    phase_report: dict[str, Any] = {}
    phases_done = set(bi.get("phases_done") or [])

    # 1 INGEST
    ing = phase_ingest(db, company_id, limit=limit)
    phase_report["ingest"] = ing["counts"]
    phases_done.add("ingest")

    # 2 NORMALIZE
    norm = phase_normalize(ing["samples"])
    phase_report["normalize"] = {"count": norm["count"]}
    phases_done.add("normalize")

    # 3 COMPARE
    compare_results = []
    all_gaps: list[dict] = []
    for doc in norm["docs"]:
        one = compare_normalized(db, company_id, doc)
        compare_results.append(one)
        all_gaps.extend(one["gaps"])
    phase_report["compare"] = {
        "docs": len(compare_results),
        "gaps": len(all_gaps),
        "high": sum(1 for g in all_gaps if g.get("severity") == "high"),
    }
    phases_done.add("compare")

    # 4 SCORE
    scored = phase_score(compare_results)
    accuracy = scored["accuracy"]
    prev_trust = float(bi.get("trust_score") or 50)
    trust = round(prev_trust * 0.65 + accuracy * 0.35, 1)
    phase_report["score"] = {"accuracy": accuracy, "trust_score": trust}
    phases_done.add("score")

    # 5 TAXONOMY
    tax = phase_taxonomy(all_gaps)
    gap_totals = dict(bi.get("gap_totals") or {})
    for g in all_gaps:
        gap_totals[g["kind"]] = int(gap_totals.get(g["kind"]) or 0) + 1
    phase_report["taxonomy"] = tax
    phases_done.add("taxonomy")

    # 6 SAFE_FIX (optional in full cycle)
    safe_result = None
    if auto_safe_fix:
        # persist gaps first so improve can see them
        open_gaps = list(bi.get("open_gaps") or [])
        seen = {g.get("title") for g in open_gaps}
        for g in all_gaps:
            if g["title"] not in seen:
                open_gaps.append(g)
                seen.add(g["title"])
        bi["open_gaps"] = open_gaps[-50:]
        bi["trust_score"] = trust
        bi["last_accuracy"] = accuracy
        sj["bridge_intelligence"] = bi
        _save(db, co, sj)
        safe_result = apply_safe_improvements(db, company_id)
        co, sj = _sj(db, company_id)
        bi = dict(sj.get("bridge_intelligence") or {})
        trust = float(bi.get("trust_score") or trust)
        phases_done = set(bi.get("phases_done") or []) | phases_done
        phase_report["safe_fix"] = {"applied": safe_result.get("count")}
    else:
        phase_report["safe_fix"] = {"skipped": True, "note": "Call /intelligence/improve or Learn Full with auto_fix"}

    # 7 RULES
    rules = phase_rules(all_gaps, bi)
    bi["playbook"] = rules["playbook"]
    phase_report["rules"] = {"playbook_size": len(rules["playbook"]), "new": len(rules["new_rules"])}
    phases_done.add("rules")

    # 8 ADVANCE
    high_gaps = sum(1 for g in all_gaps if g.get("severity") == "high")
    adv = phase_advance(trust, accuracy, high_gaps, bi.get("playbook") or [])
    bi["advance"] = adv
    phase_report["advance"] = {
        "ready_reduce_bridge": adv["ready_reduce_bridge"],
        "recommendation": adv["recommendation"],
    }
    phases_done.add("advance")

    # merge gaps + learnings + history
    open_gaps = list(bi.get("open_gaps") or [])
    seen = {g.get("title") for g in open_gaps}
    for g in all_gaps:
        if g["title"] not in seen:
            open_gaps.append(g)
            seen.add(g["title"])
    open_gaps = open_gaps[-50:]

    # 9 RETAIN (mark before run snapshot so curriculum never misses a phase)
    phases_done.add("retain")
    phase_report["retain"] = {"persisted": True}

    learnings = list(bi.get("learnings") or [])
    learnings.append(
        {
            "at": _now(),
            "accuracy": accuracy,
            "samples": len(compare_results),
            "gaps": len(all_gaps),
            "phases": sorted(phases_done),
            "note": adv["recommendation"],
        }
    )

    run = {
        "id": f"learn_{secrets.token_hex(4)}",
        "at": _now(),
        "accuracy": accuracy,
        "trust_score": trust,
        "samples": len(compare_results),
        "gaps_found": len(all_gaps),
        "high_gaps": high_gaps,
        "phases_done": sorted(phases_done),
        "curriculum_pct": round(100.0 * len(phases_done) / len(LEARNING_PHASES), 1),
    }
    phase_report["retain"]["run_id"] = run["id"]
    history = list(bi.get("history") or [])
    history.append(run)

    bi.update(
        {
            "trust_score": trust,
            "runs": int(bi.get("runs") or 0) + 1,
            "last_run_at": run["at"],
            "last_accuracy": accuracy,
            "gap_totals": gap_totals,
            "history": history[-50:],
            "open_gaps": open_gaps,
            "learnings": learnings[-50:],
            "phases_done": sorted(phases_done),
            "last_phase_report": phase_report,
            "playbook": bi.get("playbook") or [],
            "advance": adv,
        }
    )
    sj["bridge_intelligence"] = bi
    _save(db, co, sj)

    return {
        "ok": True,
        "run": run,
        "accuracy": accuracy,
        "trust_score": trust,
        "samples": len(compare_results),
        "gaps": all_gaps[:40],
        "phase_report": phase_report,
        "phases": _phase_status(bi),
        "advance": adv,
        "safe_fix": safe_result,
        "message": (
            f"Full learn · accuracy {accuracy}% · trust {trust} · "
            f"phases {len(phases_done)}/{len(LEARNING_PHASES)}. {adv['recommendation']}"
        ),
        "state": get_state(db, company_id),
    }


def run_full_curriculum(db: Session, company_id: int, *, auto_safe_fix: bool = True) -> dict[str, Any]:
    """Explicit full curriculum including safe fix."""
    return run_learn_cycle(db, company_id, limit=50, auto_safe_fix=auto_safe_fix)


def learn_from_inbound(db: Session, company_id: int, payload: dict[str, Any], *, source: str = "hook") -> dict[str, Any] | None:
    try:
        one = compare_payload_to_kanha(db, company_id, payload, source=source)
        co, sj = _sj(db, company_id)
        bi = dict(sj.get("bridge_intelligence") or {})
        open_gaps = list(bi.get("open_gaps") or [])
        seen = {g.get("title") for g in open_gaps}
        for g in one.get("gaps") or []:
            if g["title"] not in seen:
                open_gaps.append(g)
                seen.add(g["title"])
        prev = float(bi.get("trust_score") or 50)
        acc = float(one.get("accuracy") or prev)
        bi["trust_score"] = round(prev * 0.9 + acc * 0.1, 1)
        bi["last_accuracy"] = acc
        bi["open_gaps"] = open_gaps[-50:]
        bi["runs"] = int(bi.get("runs") or 0) + 1
        bi["last_run_at"] = _now()
        # mark micro-phases touched
        done = set(bi.get("phases_done") or [])
        done.update(["ingest", "normalize", "compare", "score"])
        bi["phases_done"] = sorted(done)
        sj["bridge_intelligence"] = bi
        _save(db, co, sj)
        return {"accuracy": acc, "gaps": len(one.get("gaps") or []), "trust_score": bi["trust_score"]}
    except Exception:
        return None


def ai_brief(db: Session, company_id: int) -> str:
    st = get_state(db, company_id)
    tops = sorted((st.get("gap_totals") or {}).items(), key=lambda x: -x[1])[:5]
    tops_s = ", ".join(f"{k}×{v}" for k, v in tops) or "none yet"
    adv = st.get("advance") or {}
    return (
        f"Bridge Intelligence (internal learning) · trust {st.get('trust_score')} · "
        f"accuracy {st.get('last_accuracy')} · curriculum {st.get('curriculum_pct')}% "
        f"({st.get('phases_complete')}/{st.get('phases_total')} phases) · "
        f"top gaps: {tops_s}. "
        f"Advance: {adv.get('recommendation') or 'Run Learn Full on Connected Apps'}. "
        f"Safe improve = empty masters only; money conflicts need human."
    )
