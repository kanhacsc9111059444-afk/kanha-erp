from __future__ import annotations

import os
import secrets
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]
# Prefer pen-drive / portable path so C: Desktop & system disk stay light.
# Set KANHA_DATA_ROOT=E:\KanhaERP-Portable\data in START_KANHA.bat
_data_env = (os.environ.get("KANHA_DATA_ROOT") or "").strip()
DATA = Path(_data_env).expanduser().resolve() if _data_env else (ROOT / "data")
DATA.mkdir(parents=True, exist_ok=True)
BACKUP = DATA / "backups"
BACKUP.mkdir(parents=True, exist_ok=True)

_DEFAULT_SECRET = "kanha-erp-dev-secret-change-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Product / white-label
    app_name: str = "KanhaERP"
    app_version: str = "1.0.0"
    brand_tagline: str = "Enterprise OS"
    brand_logo_url: str = "/assets/favicon.svg"
    brand_support_email: str = "support@kanhaerp.com"
    brand_primary: str = "#1d4ed8"
    brand_accent: str = "#0f766e"

    # Security
    secret_key: str = _DEFAULT_SECRET
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12
    cors_origins: str = "*"
    demo_mode: bool = True
    enforce_secure_secret: bool = True
    min_password_length: int = 8
    login_rate_limit: int = 20  # attempts per window
    login_rate_window_seconds: int = 300
    require_https_hint: bool = True

    # Bootstrap admin (used when seeding empty DB)
    admin_email: str = "admin@kanhaerp.com"
    admin_password: str = "admin123"
    core_owner_email: str = ""  # optional extra owner email for Core Control (defaults to admin_email)
    # Owner Ultra Support unlock (login page). Env: CORE_CONTROL_PASS.
    # Demo fallback if empty: KanhaCoreUltra1. Production: set a strong secret in .env.
    core_control_pass: str = ""

    # Public share gate (HTTP Basic) — env SHARE_GATE_PASSWORD. Empty = off.
    share_gate_user: str = "viewer"
    share_gate_password: str = ""

    company_name: str = "Kanha Industries"
    company_code: str = "KANHA"
    company_gstin: str = "08AABCK1234D1Z5"

    # Database / Redis
    database_url: str = f"sqlite:///{(DATA / 'kanha_erp.db').as_posix()}"
    redis_url: str = "redis://localhost:6379/0"

    # Scheduler (agents auto-run)
    scheduler_enabled: bool = True
    scheduler_interval_minutes: int = 60
    scheduler_run_cash: bool = False  # keep False until WhatsApp keys reviewed
    scheduler_run_stock: bool = True
    scheduler_run_compliance: bool = True
    scheduler_run_whatsapp: bool = True  # templates + chase flows via Automation
    scheduler_run_bridge_learn: bool = True  # Bridge Intelligence curriculum tick

    # WhatsApp Business Cloud API (Meta)
    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_api_version: str = "v19.0"
    whatsapp_verify_token: str = "kanha_meta_verify"  # Meta webhook hub.verify_token

    # Razorpay
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""

    # GSP / e-Invoice / e-Way (ClearTax-style placeholder)
    gsp_base_url: str = ""
    gsp_api_key: str = ""
    gsp_api_secret: str = ""

    # Maps
    maps_provider: str = "none"  # none|google|mapbox
    maps_api_key: str = ""

    # LLM
    llm_provider: str = "none"  # none|openai|azure
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = ""

    # SMTP (optional email)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    # Storage
    upload_max_mb: int = 15

    # ── HA / multi-site resilience (primary + hot replicas + 5 mirrors) ──
    # Better than 5-way multi-writer (conflicts): 1 writer primary, N hot replicas,
    # continuous snapshot sync, auto-failover, 5 identical portable ERP mirrors.
    cluster_enabled: bool = True
    cluster_node_id: str = "node-1"
    cluster_role: str = "primary"  # primary | replica
    cluster_token: str = "kanha-cluster-change-me"
    cluster_public_url: str = "http://127.0.0.1:8080"
    cluster_primary_url: str = "http://127.0.0.1:8080"
    cluster_peers: str = ""  # comma URLs of sibling nodes
    cluster_sync_seconds: int = 30
    cluster_heartbeat_seconds: int = 10
    cluster_failover_after_seconds: int = 45
    cluster_priority: int = 100  # higher wins election on failover
    cluster_min_failover_probes: int = 2  # failed HTTP probes before auto-promote
    cluster_require_probe: bool = True
    # 5 mirror destinations (folders). Empty slots auto-create under data/mirrors/
    backup_mirror_1: str = ""
    backup_mirror_2: str = ""
    backup_mirror_3: str = ""
    backup_mirror_4: str = ""
    backup_mirror_5: str = ""
    # Optional user portable pack (USB / NAS path)
    backup_user_pack: str = ""

    @property
    def is_production(self) -> bool:
        return not self.demo_mode

    @property
    def secret_is_default(self) -> bool:
        return self.secret_key in (_DEFAULT_SECRET, "change-me-to-a-long-random-string", "change-me-in-production")

    @property
    def whatsapp_live(self) -> bool:
        return bool(self.whatsapp_token and self.whatsapp_phone_number_id)

    @property
    def razorpay_live(self) -> bool:
        return bool(self.razorpay_key_id and self.razorpay_key_secret)

    @property
    def gsp_live(self) -> bool:
        return bool(self.gsp_base_url and self.gsp_api_key)

    @property
    def llm_live(self) -> bool:
        return bool(self.llm_api_key and self.llm_provider not in ("", "none"))

    @property
    def maps_live(self) -> bool:
        return bool(self.maps_api_key and self.maps_provider not in ("", "none"))

    @property
    def smtp_live(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)

    def golive_checklist(self) -> list[dict]:
        db_ok = "postgresql" in (self.database_url or "").lower() or self.demo_mode
        return [
            {"id": "secret", "label": "SECRET_KEY set (not default)", "ok": not self.secret_is_default, "need": "connectivity"},
            {"id": "cors", "label": "CORS locked (not *)", "ok": self.cors_origins.strip() != "*", "need": "connectivity"},
            {"id": "database", "label": "Postgres URL (recommended live)", "ok": "postgresql" in (self.database_url or "").lower(), "need": "connectivity"},
            {"id": "demo_off", "label": "DEMO_MODE=false for production", "ok": not self.demo_mode, "need": "config"},
            {"id": "admin_pw", "label": "Admin password not demo default", "ok": self.admin_password != "admin123" or self.demo_mode, "need": "config"},
            {"id": "whatsapp", "label": "WhatsApp Meta token", "ok": self.whatsapp_live, "need": "connectivity"},
            {"id": "razorpay", "label": "Razorpay keys", "ok": self.razorpay_live, "need": "connectivity"},
            {"id": "gsp", "label": "GSP e-Invoice/e-Way keys", "ok": self.gsp_live, "need": "connectivity"},
            {"id": "maps", "label": "Maps API key", "ok": self.maps_live, "need": "connectivity"},
            {"id": "llm", "label": "LLM API key (optional)", "ok": self.llm_live, "need": "connectivity"},
            {"id": "smtp", "label": "SMTP email (optional)", "ok": self.smtp_live, "need": "connectivity"},
            {"id": "scheduler", "label": "Agent scheduler enabled", "ok": self.scheduler_enabled, "need": "config"},
            {"id": "db_path", "label": "Database configured", "ok": bool(self.database_url), "need": "config"},
            {"id": "https", "label": "Serve behind HTTPS in production", "ok": True, "need": "connectivity", "note": "Terminate TLS at nginx/Caddy"},
            {"id": "cluster", "label": "HA cluster enabled", "ok": self.cluster_enabled, "need": "config"},
            {"id": "cluster_token", "label": "CLUSTER_TOKEN not default", "ok": self.cluster_token != "kanha-cluster-change-me" or self.demo_mode, "need": "config"},
            {"id": "ha_peers", "label": "At least one CLUSTER_PEER (hot replica)", "ok": bool(self.peer_urls()) or self.demo_mode, "need": "config"},
            {"id": "ha_mirrors", "label": "Mirrors on separate disks (not only data/mirrors)", "ok": any(bool(x.strip()) for x in [self.backup_mirror_1, self.backup_mirror_2, self.backup_mirror_3, self.backup_mirror_4, self.backup_mirror_5, self.backup_user_pack]) or self.demo_mode, "need": "config"},
        ]

    def mirror_paths(self) -> list[Path]:
        """Resolve up to 5 mirror folders for identical portable ERP packs."""
        raw = [
            self.backup_mirror_1,
            self.backup_mirror_2,
            self.backup_mirror_3,
            self.backup_mirror_4,
            self.backup_mirror_5,
        ]
        out: list[Path] = []
        for i, p in enumerate(raw, start=1):
            path = Path(p) if p.strip() else (DATA / "mirrors" / f"site-{i}")
            path.mkdir(parents=True, exist_ok=True)
            out.append(path)
        if self.backup_user_pack.strip():
            up = Path(self.backup_user_pack.strip())
            up.mkdir(parents=True, exist_ok=True)
            out.append(up)
        return out

    def peer_urls(self) -> list[str]:
        peers = [u.strip().rstrip("/") for u in (self.cluster_peers or "").split(",") if u.strip()]
        primary = (self.cluster_primary_url or "").strip().rstrip("/")
        if primary and primary not in peers:
            peers.insert(0, primary)
        self_url = (self.cluster_public_url or "").strip().rstrip("/")
        return [p for p in peers if p and p != self_url]


settings = Settings()

SECRET_AUTO_GENERATED = False
if settings.is_production and settings.enforce_secure_secret and settings.secret_is_default:
    # Process can start, but operator must set SECRET_KEY in .env for multi-instance / restart safety
    object.__setattr__(settings, "secret_key", secrets.token_urlsafe(48))
    SECRET_AUTO_GENERATED = True
