from __future__ import annotations

import logging
import threading
import time
from datetime import datetime

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import Company, User

log = logging.getLogger("kanha.scheduler")
_started = False


def _system_user(db):
    user = db.query(User).filter(User.is_superadmin.is_(True), User.is_active.is_(True)).first()
    if user:
        return user
    return db.query(User).filter(User.is_active.is_(True)).first()


def run_agent_tick() -> dict:
    """Run Cash + Stock + Compliance agents for each company (background)."""
    from app.api.extended import agent_cash_run, agent_compliance_run, agent_stock_run

    db = SessionLocal()
    summary = {"ran_at": datetime.utcnow().isoformat() + "Z", "companies": []}
    try:
        user = _system_user(db)
        if not user:
            return {"ok": False, "error": "no user"}
        companies = db.query(Company).filter(Company.active.is_(True)).all()
        for co in companies:
            actor = (
                db.query(User)
                .filter(User.company_id == co.id, User.is_active.is_(True))
                .order_by(User.is_superadmin.desc())
                .first()
            ) or user
            row = {"company_id": co.id, "ok": True}
            try:
                if settings.scheduler_run_cash:
                    row["cash"] = agent_cash_run(actor, db).get("message")
                else:
                    row["cash"] = "skipped (SCHEDULER_RUN_CASH=false)"
            except Exception as e:
                row["cash_error"] = str(e)
            try:
                if settings.scheduler_run_stock:
                    row["stock"] = agent_stock_run(actor, db).get("message")
                else:
                    row["stock"] = "skipped"
            except Exception as e:
                row["stock_error"] = str(e)
            try:
                if settings.scheduler_run_compliance:
                    row["compliance"] = agent_compliance_run(actor, db).get("message")
                else:
                    row["compliance"] = "skipped"
            except Exception as e:
                row["compliance_error"] = str(e)
            try:
                if getattr(settings, "scheduler_run_whatsapp", True):
                    from app.services.whatsapp_automation import run_all_whatsapp_automation

                    wa = run_all_whatsapp_automation(db, co.id, actor.id, settings.app_name)
                    row["whatsapp"] = wa.get("message")
                    db.commit()
                else:
                    row["whatsapp"] = "skipped (SCHEDULER_RUN_WHATSAPP=false)"
            except Exception as e:
                row["whatsapp_error"] = str(e)
            try:
                if getattr(settings, "scheduler_run_bridge_learn", True):
                    from app.services.bridge_intelligence import run_learn_cycle

                    bi = run_learn_cycle(db, co.id, limit=25, auto_safe_fix=False)
                    row["bridge_learn"] = (
                        f"acc {bi.get('accuracy')} trust {bi.get('trust_score')} "
                        f"phases {len((bi.get('run') or {}).get('phases_done') or [])}"
                    )
                else:
                    row["bridge_learn"] = "skipped"
            except Exception as e:
                row["bridge_learn_error"] = str(e)
            summary["companies"].append(row)
        summary["ok"] = True
        return summary
    except Exception as e:
        log.exception("scheduler tick failed")
        return {"ok": False, "error": str(e)}
    finally:
        db.close()


def run_ha_tick() -> dict:
    """Cluster heartbeat + pull/publish + multi-site mirror + auto-failover."""
    if not settings.cluster_enabled:
        return {"ok": True, "skipped": True}
    from app.services.ha_sync import ha_tick

    try:
        return ha_tick()
    except Exception as e:
        log.exception("HA tick failed")
        return {"ok": False, "error": str(e)}


def start_scheduler() -> None:
    global _started
    if _started:
        return
    _started = True

    agent_on = settings.scheduler_enabled
    ha_on = settings.cluster_enabled
    if not agent_on and not ha_on:
        return

    agent_interval = max(5, int(settings.scheduler_interval_minutes)) * 60
    ha_interval = max(15, int(getattr(settings, "cluster_sync_seconds", 30) or 30))

    def agent_loop() -> None:
        time.sleep(15)
        while True:
            try:
                result = run_agent_tick()
                log.info("Kanha agent scheduler tick: %s", result.get("ok"))
            except Exception:
                log.exception("scheduler loop error")
            time.sleep(agent_interval)

    def ha_loop() -> None:
        time.sleep(8)
        while True:
            try:
                result = run_ha_tick()
                log.info("HA tick: ok=%s role=%s", result.get("ok"), settings.cluster_role)
            except Exception:
                log.exception("HA loop error")
            time.sleep(ha_interval)

    if agent_on:
        threading.Thread(target=agent_loop, name="kanha-agent-scheduler", daemon=True).start()
        log.info("Agent scheduler started (every %s min)", settings.scheduler_interval_minutes)
    if ha_on:
        threading.Thread(target=ha_loop, name="kanha-ha-scheduler", daemon=True).start()
        log.info("HA cluster scheduler started (every %ss)", ha_interval)
