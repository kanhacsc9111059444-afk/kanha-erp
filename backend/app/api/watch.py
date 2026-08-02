"""Live Monitor API — watch streams + chat. Video stays on NVR/DVR (not stored here)."""
from __future__ import annotations

from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException

from app.core.deps import CurrentUser, DbDep, assert_perm, audit
from app.models import MonitorCamera, MonitorChat, MonitorSite, User
from app.services.industry_profiles import apply_profile, list_profiles

router = APIRouter(prefix="/api", tags=["watch-industry"])


# ── Industry profile ─────────────────────────────────────────────────────────


@router.get("/company/profiles")
def company_profiles(user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*")
    from app.models import Company

    co = db.get(Company, user.company_id)
    settings = (co.settings_json or {}) if co else {}
    return {
        "ok": True,
        "current": settings.get("industry_profile") or "hybrid",
        "profiles": list_profiles(),
        "note": "Same ERP kernel — profile only scopes which modules show/run.",
    }


class ProfileIn(BaseModel):
    profile: str
    apply_modules: bool = True


@router.put("/company/profile")
def company_set_profile(body: ProfileIn, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*")
    from app.models import Company

    co = db.get(Company, user.company_id)
    if not co:
        raise HTTPException(404, "Company not found")
    pid = (body.profile or "").strip().lower()
    try:
        mods = apply_profile(pid)
    except Exception as e:
        raise HTTPException(400, str(e)) from e
    sj = dict(co.settings_json or {})
    sj["industry_profile"] = pid
    co.settings_json = sj
    if body.apply_modules:
        co.modules_enabled = {**(co.modules_enabled or {}), **mods}
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="industry_profile",
        entity="company",
        detail={"profile": pid, "apply_modules": body.apply_modules},
    )
    db.commit()
    return {
        "ok": True,
        "profile": pid,
        "modules_enabled": co.modules_enabled,
        "message": f"Company profile → {pid}. Modules scoped for that business type.",
    }


# ── Live Monitor (no video storage) ──────────────────────────────────────────


@router.get("/watch/policy")
def watch_policy(user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "watch.*", "settings.*", "hrms.*")
    return {
        "ok": True,
        "stores_video": False,
        "policy": (
            "KanhaERP only opens LIVE streams from your NVR/DVR/camera cloud. "
            "Recording, retention, and heavy video files stay on your DVR/vendor — "
            "ERP does not download or archive footage."
        ),
        "allowed_url_kinds": ["https HLS", "MJPEG", "vendor embed/iframe", "WebRTC gateway URL"],
        "forbidden": ["Uploading MP4/AVI into ERP", "Using ERP as DVR replacement"],
    }


@router.get("/watch/sites")
def watch_sites(user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "watch.*", "settings.*", "hrms.*")
    sites = (
        db.query(MonitorSite)
        .filter(MonitorSite.company_id == user.company_id, MonitorSite.active.is_(True))
        .order_by(MonitorSite.name)
        .all()
    )
    cams = (
        db.query(MonitorCamera)
        .filter(MonitorCamera.company_id == user.company_id, MonitorCamera.active.is_(True))
        .all()
    )
    by_site: dict[int, list] = {}
    for c in cams:
        by_site.setdefault(c.site_id, []).append(
            {
                "id": c.id,
                "name": c.name,
                "location_label": c.location_label,
                "stream_url": c.stream_url,
                "embed_url": c.embed_url or c.stream_url,
                "vendor": c.vendor,
                "kind": c.kind,
            }
        )
    return {
        "ok": True,
        "stores_video": False,
        "sites": [
            {
                "id": s.id,
                "code": s.code,
                "name": s.name,
                "city": s.city,
                "address": s.address,
                "cameras": by_site.get(s.id, []),
            }
            for s in sites
        ],
    }


class SiteIn(BaseModel):
    code: str = ""
    name: str
    city: str = ""
    address: str = ""
    notes: str = ""


@router.post("/watch/sites")
def watch_site_create(body: SiteIn, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "watch.*", "settings.*")
    row = MonitorSite(
        company_id=user.company_id,
        code=body.code or body.name[:8].upper(),
        name=body.name,
        city=body.city,
        address=body.address,
        notes=body.notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"ok": True, "id": row.id, "name": row.name}


class CameraIn(BaseModel):
    site_id: int
    name: str
    location_label: str = ""
    stream_url: str = ""
    embed_url: str = ""
    vendor: str = "generic"
    kind: str = "office"


@router.post("/watch/cameras")
def watch_camera_create(body: CameraIn, user: CurrentUser, db: DbDep) -> dict:
    """Register a live stream URL only — do not upload video files."""
    assert_perm(user, db, "watch.*", "settings.*")
    site = db.get(MonitorSite, body.site_id)
    if not site or site.company_id != user.company_id:
        raise HTTPException(404, "Site not found")
    url = (body.stream_url or body.embed_url or "").strip()
    if not url:
        raise HTTPException(400, "stream_url or embed_url required (external NVR/camera link)")
    if url.lower().startswith("file:") or url.endswith((".mp4", ".avi", ".mkv")):
        raise HTTPException(
            400,
            "Do not point ERP at local video files. Use live HTTPS/HLS/embed from your DVR/cloud.",
        )
    row = MonitorCamera(
        company_id=user.company_id,
        site_id=body.site_id,
        name=body.name,
        location_label=body.location_label,
        stream_url=body.stream_url or url,
        embed_url=body.embed_url or url,
        vendor=body.vendor,
        kind=body.kind,
        meta={"stores_video_in_erp": False},
    )
    db.add(row)
    audit(db, company_id=user.company_id, user_id=user.id, action="camera_add", entity="monitor_camera")
    db.commit()
    db.refresh(row)
    return {"ok": True, "id": row.id, "message": "Camera linked for LIVE view only — footage stays on DVR"}


class ChatIn(BaseModel):
    site_id: int | None = None
    body: str = Field(min_length=1, max_length=2000)
    to_user_id: int | None = None


@router.get("/watch/chat")
def watch_chat_list(user: CurrentUser, db: DbDep, site_id: int | None = None, limit: int = 50) -> dict:
    assert_perm(user, db, "watch.*", "settings.*", "hrms.*")
    q = db.query(MonitorChat).filter(MonitorChat.company_id == user.company_id)
    if site_id:
        q = q.filter(MonitorChat.site_id == site_id)
    rows = q.order_by(MonitorChat.id.desc()).limit(min(limit, 100)).all()
    users = {u.id: u.full_name for u in db.query(User).filter(User.company_id == user.company_id).all()}
    return {
        "ok": True,
        "messages": [
            {
                "id": m.id,
                "site_id": m.site_id,
                "user_id": m.user_id,
                "user_name": users.get(m.user_id, "?"),
                "to_user_id": m.to_user_id,
                "body": m.body,
                "created_at": m.created_at.isoformat() + "Z" if m.created_at else None,
            }
            for m in reversed(rows)
        ],
    }


@router.post("/watch/chat")
def watch_chat_post(body: ChatIn, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "watch.*", "settings.*", "hrms.*")
    row = MonitorChat(
        company_id=user.company_id,
        site_id=body.site_id,
        user_id=user.id,
        body=body.body.strip(),
        to_user_id=body.to_user_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"ok": True, "id": row.id}


@router.post("/watch/seed-demo")
def watch_seed_demo(user: CurrentUser, db: DbDep) -> dict:
    """Demo sites with placeholder embed (public sample HLS) — still no ERP video store."""
    assert_perm(user, db, "watch.*", "settings.*")
    if db.query(MonitorSite).filter(MonitorSite.company_id == user.company_id).count():
        return {"ok": True, "message": "Sites already exist"}
    # Public demo HLS (Apple sample) — replace with your NVR URLs in production
    demo_hls = "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8"
    s1 = MonitorSite(company_id=user.company_id, code="HQ", name="Head Office", city="Indore", address="Main campus")
    s2 = MonitorSite(company_id=user.company_id, code="PLT", name="Plant / Factory", city="Pithampur", address="Unit-1")
    db.add_all([s1, s2])
    db.flush()
    db.add_all(
        [
            MonitorCamera(
                company_id=user.company_id,
                site_id=s1.id,
                name="Reception",
                location_label="Gate",
                stream_url=demo_hls,
                embed_url=demo_hls,
                kind="office",
                vendor="demo",
                meta={"demo": True, "stores_video_in_erp": False},
            ),
            MonitorCamera(
                company_id=user.company_id,
                site_id=s1.id,
                name="Accounts floor",
                location_label="Floor-2",
                stream_url=demo_hls,
                embed_url=demo_hls,
                kind="office",
                vendor="demo",
            ),
            MonitorCamera(
                company_id=user.company_id,
                site_id=s2.id,
                name="Production line A",
                location_label="Shop floor",
                stream_url=demo_hls,
                embed_url=demo_hls,
                kind="plant",
                vendor="demo",
            ),
        ]
    )
    db.commit()
    return {
        "ok": True,
        "message": "Demo sites + cameras linked (sample HLS). Replace URLs with your DVR live links.",
    }
