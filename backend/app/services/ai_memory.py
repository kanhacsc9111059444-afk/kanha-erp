"""
Company AI memory — teach from text / files / folders; persist forever (company-scoped).

Privacy: do not store passwords or secrets intentionally; skip binary / oversized files.
Used by Demo AI + live LLM context so learned facts survive across sessions.
"""
from __future__ import annotations

import re
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.models import Company

ALLOWED_EXT = {
    ".txt",
    ".md",
    ".markdown",
    ".csv",
    ".tsv",
    ".json",
    ".log",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".html",
    ".htm",
    ".css",
    ".xml",
    ".yml",
    ".yaml",
    ".ini",
    ".cfg",
    ".conf",
    ".sql",
    ".env.example",
    ".rst",
    ".toml",
}
SKIP_NAMES = {".ds_store", "thumbs.db", "desktop.ini"}
MAX_FILE_BYTES = 120_000
MAX_ITEM_CHARS = 24_000
MAX_ITEMS = 120
MAX_TOTAL_CHARS = 400_000


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


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


def _mem(sj: dict) -> dict:
    m = dict(sj.get("ai_memory") or {})
    m.setdefault("items", [])
    return m


def list_memory(db: Session, company_id: int) -> dict[str, Any]:
    _, sj = _sj(db, company_id)
    m = _mem(sj)
    items = list(m.get("items") or [])
    return {
        "ok": True,
        "count": len(items),
        "total_chars": sum(int(i.get("chars") or 0) for i in items),
        "items": [
            {
                "id": i.get("id"),
                "title": i.get("title"),
                "source": i.get("source"),
                "filename": i.get("filename"),
                "tags": i.get("tags") or [],
                "preview": i.get("preview") or "",
                "chars": i.get("chars") or 0,
                "created_at": i.get("created_at"),
            }
            for i in reversed(items)
        ],
        "pitch": (
            "File/folder ya note se AI ko sikhao — company memory me permanent save. "
            "Baad me poochho to yaad se bataayega."
        ),
    }


def get_item(db: Session, company_id: int, mem_id: str) -> dict[str, Any] | None:
    _, sj = _sj(db, company_id)
    for i in _mem(sj).get("items") or []:
        if i.get("id") == mem_id:
            return i
    return None


def delete_memory(db: Session, company_id: int, mem_id: str) -> dict[str, Any]:
    co, sj = _sj(db, company_id)
    m = _mem(sj)
    before = len(m.get("items") or [])
    m["items"] = [i for i in (m.get("items") or []) if i.get("id") != mem_id]
    sj["ai_memory"] = m
    _save(db, co, sj)
    return {"ok": True, "deleted": before - len(m["items"]), "count": len(m["items"])}


def clear_memory(db: Session, company_id: int) -> dict[str, Any]:
    co, sj = _sj(db, company_id)
    sj["ai_memory"] = {"items": [], "cleared_at": _now()}
    _save(db, co, sj)
    return {"ok": True, "count": 0, "message": "AI memory cleared for this company"}


def _decode_bytes(raw: bytes) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", errors="ignore")


def _ext_ok(name: str) -> bool:
    n = (name or "").lower().strip()
    if not n or n in SKIP_NAMES or n.startswith("~$"):
        return False
    p = Path(n)
    if p.suffix.lower() in ALLOWED_EXT:
        return True
    # .env.example style
    if n.endswith(".env.example") or n.endswith(".md.txt"):
        return True
    return False


def _trim_content(text: str) -> str:
    t = (text or "").replace("\x00", " ").strip()
    if len(t) > MAX_ITEM_CHARS:
        t = t[:MAX_ITEM_CHARS] + "\n…[truncated]"
    return t


def _total_chars(items: list[dict]) -> int:
    return sum(int(i.get("chars") or 0) for i in items)


def _append_item(
    db: Session,
    company_id: int,
    *,
    title: str,
    content: str,
    source: str,
    filename: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    body = _trim_content(content)
    if len(body) < 8:
        raise ValueError("Content too short to learn")
    co, sj = _sj(db, company_id)
    m = _mem(sj)
    items = list(m.get("items") or [])
    # Drop oldest if over caps
    while items and (len(items) >= MAX_ITEMS or _total_chars(items) + len(body) > MAX_TOTAL_CHARS):
        items.pop(0)
    item = {
        "id": f"mem_{secrets.token_hex(4)}",
        "title": (title or filename or "Untitled")[:160],
        "source": source,
        "filename": (filename or "")[:160] or None,
        "tags": [t[:32] for t in (tags or [])[:8]],
        "preview": body[:220].replace("\n", " "),
        "content": body,
        "chars": len(body),
        "created_at": _now(),
    }
    items.append(item)
    m["items"] = items
    m["last_learn_at"] = _now()
    sj["ai_memory"] = m
    _save(db, co, sj)
    return item


def learn_text(
    db: Session,
    company_id: int,
    text: str,
    *,
    title: str = "",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    item = _append_item(
        db,
        company_id,
        title=title or "Taught note",
        content=text,
        source="teach",
        tags=tags,
    )
    return {
        "ok": True,
        "learned": True,
        "item": {k: item[k] for k in ("id", "title", "source", "chars", "preview", "created_at")},
        "message": f"Yaad rakh liya · {item['title']} ({item['chars']} chars). Ab poochho — bataunga.",
    }


def learn_file_bytes(
    db: Session,
    company_id: int,
    *,
    filename: str,
    raw: bytes,
    source: str = "upload",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    name = (filename or "file.txt").strip()
    if not _ext_ok(name):
        raise ValueError(f"File type not supported for learning: {name}")
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError(f"File too large (max {MAX_FILE_BYTES // 1000}KB text): {name}")
    text = _decode_bytes(raw)
    item = _append_item(
        db,
        company_id,
        title=Path(name).stem or name,
        content=text,
        source=source,
        filename=name,
        tags=tags,
    )
    return {
        "ok": True,
        "learned": True,
        "item": {k: item[k] for k in ("id", "title", "source", "filename", "chars", "preview", "created_at")},
        "message": f"File seekh li · {name} ({item['chars']} chars)",
    }


def learn_many_files(
    db: Session,
    company_id: int,
    files: Iterable[tuple[str, bytes]],
    *,
    source: str = "folder",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    learned = []
    skipped = []
    for name, raw in files:
        try:
            r = learn_file_bytes(db, company_id, filename=name, raw=raw, source=source, tags=tags)
            learned.append(r["item"])
        except Exception as e:  # noqa: BLE001
            skipped.append({"file": name, "reason": str(e)[:120]})
    return {
        "ok": True,
        "learned_count": len(learned),
        "skipped_count": len(skipped),
        "learned": learned[:40],
        "skipped": skipped[:40],
        "message": f"Folder/files · {len(learned)} seekhe, {len(skipped)} skip",
        "state": list_memory(db, company_id),
    }


def search_memory(db: Session, company_id: int, query: str, *, limit: int = 5) -> list[dict[str, Any]]:
    _, sj = _sj(db, company_id)
    items = list(_mem(sj).get("items") or [])
    if not items:
        return []
    q = (query or "").strip().lower()
    if not q:
        return list(reversed(items))[:limit]
    tokens = [t for t in re.split(r"[^a-z0-9_\u0900-\u097f]+", q) if len(t) > 2]
    if not tokens:
        tokens = [q]
    scored = []
    for i in items:
        blob = f"{i.get('title','')} {i.get('filename','')} {i.get('preview','')} {i.get('content','')}".lower()
        score = sum(3 if t in blob else 0 for t in tokens)
        score += sum(1 for t in tokens if t in (i.get("title") or "").lower())
        if score > 0:
            scored.append((score, i))
    scored.sort(key=lambda x: (-x[0], x[1].get("created_at") or ""))
    return [i for _, i in scored[:limit]]


def memory_context_block(db: Session, company_id: int, query: str = "", *, limit: int = 4) -> str:
    """Compact block for LLM / demo AI injection."""
    hits = search_memory(db, company_id, query, limit=limit)
    if not hits and not query:
        _, sj = _sj(db, company_id)
        hits = list(reversed(_mem(sj).get("items") or []))[:2]
    if not hits:
        return ""
    parts = ["COMPANY AI MEMORY (taught by user — prefer these facts when relevant):"]
    for i, it in enumerate(hits, 1):
        body = (it.get("content") or "")[:1800]
        parts.append(f"{i}. [{it.get('title')}] ({it.get('source')}/{it.get('filename') or 'note'})\n{body}")
    return "\n\n".join(parts)[:7000]


def answer_from_memory(db: Session, company_id: int, message: str) -> dict[str, Any] | None:
    """If question clearly about learned content, answer from memory."""
    msg = (message or "").strip()
    low = msg.lower()
    hits = search_memory(db, company_id, msg, limit=4)
    force = any(
        k in low
        for k in (
            "yaad",
            "memory",
            "seekha",
            "seekh",
            "learned",
            "what did you learn",
            "kya seekha",
            "kya yaad",
            "tumhe kya",
            "jo maine",
            "file se",
            "folder se",
            "document se",
            "policy",
            "sop",
            "hamari",
            "company rule",
        )
    )
    if not hits and not force:
        return None
    if not hits:
        st = list_memory(db, company_id)
        if not st["count"]:
            return {
                "reply": (
                    "Abhi koi taught memory nahi. AI page pe note likho ya file/folder upload karke "
                    "**Teach AI** dabao — phir main hamesha yaad rakhunga."
                ),
                "from_memory": True,
                "hits": 0,
            }
        # “Kya seekha?” → show actual remembered content, not only titles
        _, sj = _sj(db, company_id)
        recent = list(reversed(_mem(sj).get("items") or []))[:5]
        chunks = []
        for it in recent:
            chunks.append(
                f"**{it.get('title')}** ({it.get('filename') or it.get('source')}):\n"
                f"{(it.get('content') or '')[:1800]}"
            )
        return {
            "reply": f"Company AI memory · {st['count']} entries:\n\n" + "\n\n---\n\n".join(chunks),
            "from_memory": True,
            "hits": st["count"],
        }
    # Build answer
    chunks = []
    for it in hits:
        chunks.append(f"**{it.get('title')}** ({it.get('filename') or it.get('source')}):\n{(it.get('content') or '')[:2200]}")
    return {
        "reply": "Tumhari taught memory se:\n\n" + "\n\n---\n\n".join(chunks),
        "from_memory": True,
        "hits": len(hits),
        "memory_ids": [h.get("id") for h in hits],
    }


def try_parse_teach_command(message: str) -> tuple[str, str] | None:
    """Detect 'yaad rakh: ...' / 'learn: ...' / 'remember: ...' teach commands."""
    raw = (message or "").strip()
    low = raw.lower()
    prefixes = (
        "yaad rakh:",
        "yaad rakho:",
        "yaad rakh ",
        "seekh:",
        "seekho:",
        "learn:",
        "remember:",
        "teach:",
        "sikhao:",
        "sikha:",
    )
    for p in prefixes:
        if low.startswith(p):
            body = raw[len(p) :].strip()
            if len(body) >= 8:
                title = body.split("\n", 1)[0][:80]
                return title, body
    # "yaad rakh that X"
    m = re.match(r"^(yaad\s+rakh[o]?\s+ki|remember\s+that)\s+(.+)$", raw, re.I | re.S)
    if m and len(m.group(2).strip()) >= 8:
        body = m.group(2).strip()
        return body.split("\n", 1)[0][:80], body
    return None
