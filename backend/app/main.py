from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import advanced, books, bridges, core, extended, ha, ops, parity, rules, trading, watch
from app.core.blackout_middleware import BlackoutLockdownMiddleware
from app.core.config import DATA, SECRET_AUTO_GENERATED, settings
from app.core.database import Base, SessionLocal, engine
from app.core.heal_middleware import FailedEntryMiddleware
from app.core.idempotency import IdempotencyMiddleware
from app.core.rbac_guard import RbacWriteMiddleware
from app.core.share_gate import ShareGateMiddleware
from app.services.scheduler import start_scheduler
from app.services.seed import ensure_shell_extras, seed_if_empty

# Import models so metadata is registered
import app.models  # noqa: F401

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version=settings.app_version)

    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    # Production: never leave CORS wide open
    if settings.is_production and origins == ["*"]:
        origins = ["http://127.0.0.1:8080", "http://localhost:8080"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins if origins != ["*"] else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Order: last added = outermost. Blackout should catch writes early.
    app.add_middleware(RbacWriteMiddleware)
    app.add_middleware(BlackoutLockdownMiddleware)
    app.add_middleware(IdempotencyMiddleware)
    app.add_middleware(FailedEntryMiddleware)
    # Outermost when share password set: browser asks password before ERP
    app.add_middleware(ShareGateMiddleware)

    app.include_router(core.router)
    app.include_router(trading.router)
    app.include_router(extended.router)
    app.include_router(ops.router)
    app.include_router(parity.router)
    app.include_router(books.router)
    app.include_router(bridges.router)
    app.include_router(advanced.router)
    app.include_router(advanced.extras_router)
    app.include_router(advanced.meta_router)
    app.include_router(ha.router)
    app.include_router(rules.router)
    app.include_router(watch.router)

    @app.on_event("startup")
    def _startup() -> None:
        Base.metadata.create_all(bind=engine)
        try:
            from sqlalchemy import text

            with engine.begin() as conn:
                cols = {r[1] for r in conn.execute(text("PRAGMA table_info(journal_entries)")).fetchall()}
                if cols and "voucher_type" not in cols:
                    conn.execute(text("ALTER TABLE journal_entries ADD COLUMN voucher_type VARCHAR(32) DEFAULT 'journal'"))
                if cols and "party_name" not in cols:
                    conn.execute(text("ALTER TABLE journal_entries ADD COLUMN party_name VARCHAR(200) DEFAULT ''"))
                pc = {r[1] for r in conn.execute(text("PRAGMA table_info(production_challans)")).fetchall()}
                if pc and "product_id" not in pc:
                    conn.execute(text("ALTER TABLE production_challans ADD COLUMN product_id INTEGER"))
                if pc and "warehouse_id" not in pc:
                    conn.execute(text("ALTER TABLE production_challans ADD COLUMN warehouse_id INTEGER"))
                sm = {r[1] for r in conn.execute(text("PRAGMA table_info(stock_moves)")).fetchall()}
                if sm and "batch_id" not in sm:
                    conn.execute(text("ALTER TABLE stock_moves ADD COLUMN batch_id INTEGER"))
                wo = {r[1] for r in conn.execute(text("PRAGMA table_info(work_orders)")).fetchall()}
                if wo and "wip_value" not in wo:
                    conn.execute(text("ALTER TABLE work_orders ADD COLUMN wip_value FLOAT DEFAULT 0"))
                pay = {r[1] for r in conn.execute(text("PRAGMA table_info(payments)")).fetchall()}
                if pay and "allocations" not in pay:
                    conn.execute(text("ALTER TABLE payments ADD COLUMN allocations JSON DEFAULT '[]'"))
                pi = {r[1] for r in conn.execute(text("PRAGMA table_info(purchase_invoices)")).fetchall()}
                if pi and "rcm" not in pi:
                    conn.execute(text("ALTER TABLE purchase_invoices ADD COLUMN rcm BOOLEAN DEFAULT 0"))
                so = {r[1] for r in conn.execute(text("PRAGMA table_info(sales_orders)")).fetchall()}
                if so and "custom" not in so:
                    conn.execute(text("ALTER TABLE sales_orders ADD COLUMN custom JSON DEFAULT '{}'"))
                dn = {r[1] for r in conn.execute(text("PRAGMA table_info(deliveries)")).fetchall()}
                if dn and "custom" not in dn:
                    conn.execute(text("ALTER TABLE deliveries ADD COLUMN custom JSON DEFAULT '{}'"))
                if dn and "invoice_id" not in dn:
                    conn.execute(text("ALTER TABLE deliveries ADD COLUMN invoice_id INTEGER"))
                invc = {r[1] for r in conn.execute(text("PRAGMA table_info(invoices)")).fetchall()}
                if invc and "custom" not in invc:
                    conn.execute(text("ALTER TABLE invoices ADD COLUMN custom JSON DEFAULT '{}'"))
                vend = {r[1] for r in conn.execute(text("PRAGMA table_info(vendors)")).fetchall()}
                if vend and "custom" not in vend:
                    conn.execute(text("ALTER TABLE vendors ADD COLUMN custom JSON DEFAULT '{}'"))
                po = {r[1] for r in conn.execute(text("PRAGMA table_info(purchase_orders)")).fetchall()}
                if po and "custom" not in po:
                    conn.execute(text("ALTER TABLE purchase_orders ADD COLUMN custom JSON DEFAULT '{}'"))
                grn = {r[1] for r in conn.execute(text("PRAGMA table_info(goods_receipts)")).fetchall()}
                if grn and "custom" not in grn:
                    conn.execute(text("ALTER TABLE goods_receipts ADD COLUMN custom JSON DEFAULT '{}'"))
                if grn and "purchase_invoice_id" not in grn:
                    conn.execute(text("ALTER TABLE goods_receipts ADD COLUMN purchase_invoice_id INTEGER"))
                pi_cols = {r[1] for r in conn.execute(text("PRAGMA table_info(purchase_invoices)")).fetchall()}
                if pi_cols and "custom" not in pi_cols:
                    conn.execute(text("ALTER TABLE purchase_invoices ADD COLUMN custom JSON DEFAULT '{}'"))
                emp = {r[1] for r in conn.execute(text("PRAGMA table_info(employees)")).fetchall()}
                if emp and "custom" not in emp:
                    conn.execute(text("ALTER TABLE employees ADD COLUMN custom JSON DEFAULT '{}'"))
                acc = {r[1] for r in conn.execute(text("PRAGMA table_info(accounts)")).fetchall()}
                if acc and "custom" not in acc:
                    conn.execute(text("ALTER TABLE accounts ADD COLUMN custom JSON DEFAULT '{}'"))
                je = {r[1] for r in conn.execute(text("PRAGMA table_info(journal_entries)")).fetchall()}
                if je and "custom" not in je:
                    conn.execute(text("ALTER TABLE journal_entries ADD COLUMN custom JSON DEFAULT '{}'"))
                el = {r[1] for r in conn.execute(text("PRAGMA table_info(employee_loans)")).fetchall()}
                if el and "custom" not in el:
                    conn.execute(text("ALTER TABLE employee_loans ADD COLUMN custom JSON DEFAULT '{}'"))
        except Exception:
            pass
        try:
            from app.services.auto_configure import apply_runtime_on_startup

            apply_runtime_on_startup()
        except Exception:
            pass
        db = SessionLocal()
        try:
            seed_if_empty(db)
            ensure_shell_extras(db)
        finally:
            db.close()
        start_scheduler()

    @app.get("/api/health")
    def health() -> dict:
        checklist = settings.golive_checklist()
        ready_core = all(
            c["ok"]
            for c in checklist
            if c["id"] in ("secret", "demo_off", "admin_pw") or settings.demo_mode
        )
        # In demo_mode, core is always "ready for local"
        if settings.demo_mode:
            ready_core = not settings.secret_is_default or True
        wait_connectivity = [c for c in checklist if not c["ok"] and c.get("need") == "connectivity"]
        blackout = {"active": False}
        try:
            from app.services.blackout import is_blackout, blackout_status
            from app.core.database import SessionLocal as _SL

            if is_blackout():
                _db = _SL()
                try:
                    blackout = blackout_status(_db)
                finally:
                    _db.close()
        except Exception:
            pass
        return {
            "ok": True,
            "app": settings.app_name,
            "version": settings.app_version,
            "demo_mode": settings.demo_mode,
            "production": settings.is_production,
            "shell": "final",
            "white_label": True,
            "secret_auto_generated": SECRET_AUTO_GENERATED,
            "scheduler_enabled": settings.scheduler_enabled,
            "blackout": blackout,
            "cluster": {
                "enabled": settings.cluster_enabled,
                "node_id": settings.cluster_node_id,
                "role": settings.cluster_role,
                "primary_url": settings.cluster_primary_url,
                "mirrors": len(settings.mirror_paths()),
            },
            "integrations": {
                "whatsapp": settings.whatsapp_live,
                "razorpay": settings.razorpay_live,
                "gsp": settings.gsp_live,
                "maps": settings.maps_live,
                "llm": settings.llm_live,
                "smtp": settings.smtp_live,
                "postgres": "postgresql" in (settings.database_url or "").lower(),
            },
            "golive": {
                "checklist": checklist,
                "waiting_on_connectivity": [c["id"] for c in wait_connectivity],
                "ready_for_keys": True,
            },
            "brand": {
                "name": settings.app_name,
                "tagline": settings.brand_tagline,
                "logo_url": settings.brand_logo_url,
                "primary": settings.brand_primary,
                "accent": settings.brand_accent,
            },
        }

    if FRONTEND.exists():
        app.mount("/assets", StaticFiles(directory=FRONTEND), name="assets")
        DATA.mkdir(parents=True, exist_ok=True)
        (DATA / "uploads").mkdir(parents=True, exist_ok=True)
        app.mount("/uploads", StaticFiles(directory=DATA / "uploads"), name="uploads")

        @app.get("/")
        def index() -> FileResponse:
            return FileResponse(FRONTEND / "index.html")

        @app.get("/{full_path:path}")
        def spa_fallback(full_path: str) -> FileResponse:
            candidate = FRONTEND / full_path
            if candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(FRONTEND / "index.html")

    return app


app = create_app()
