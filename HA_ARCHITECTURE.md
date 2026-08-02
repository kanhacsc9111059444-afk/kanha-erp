# KanhaERP — HA / Portable Resilience Architecture

Your idea is right: **backup of only a DB file is not enough**. You need the **whole ERP runnable in multiple places**, with **same latest data**, so if one server dies the business does not stop.

## Why NOT “5 writers at once”

If 5 servers all accept sales/invoices at the same time:

- Same invoice number can be created twice
- Stock goes negative in one place and positive in another
- Merging later is painful and error-prone (**split-brain**)

So the **better** design (still matches your goal) is:

| Layer | What it is | Your goal |
|--------|------------|-----------|
| **1 Primary** | Only node that accepts **writes** | Single source of truth |
| **Hot replicas (2–4)** | Full ERP running, **read + sync**, ready to become primary | Zero downtime if primary crashes |
| **5 identical portable packs** | Full ERP snapshot (DB + uploads + RESTORE.txt) on separate disks/NAS/USB | Data + ERP in 5 places |
| **User pack** | Extra copy on your USB/NAS (`BACKUP_USER_PACK`) | Personal final backup |

All replicas and mirrors stay on the **same checksum / seq** — latest identical data, not divergent copies.

## How it works day-to-day

1. Users work on **primary** URL (or a load balancer that points writes to primary).
2. Every ~`CLUSTER_SYNC_SECONDS`, HA tick:
   - Heartbeat to peers
   - Primary **publishes** portable pack → copies to mirror folders 1–5 (+ user pack)
   - Replicas **pull** `LATEST.zip` and apply → identical DB + uploads
3. If primary heartbeats stop longer than `CLUSTER_FAILOVER_AFTER_SECONDS`:
   - Highest `CLUSTER_PRIORITY` online replica **auto-promotes**
   - Writes continue on the new primary
4. Dead server: repair it, or install portable pack on a **new** machine as replica → it catches up and joins the cluster.

## Portable pack contents

Each mirror folder gets:

- `kanha_erp.db` (full business data)
- `uploads/` (documents / media)
- `manifest.json` (seq + checksum)
- `RESTORE.txt` (how to spin a new node)
- `LATEST.zip` / `LATEST/` pointer (always the newest)

## Configure (`.env`)

```env
CLUSTER_ENABLED=true
CLUSTER_NODE_ID=node-1
CLUSTER_ROLE=primary
CLUSTER_TOKEN=shared-secret-same-on-all-nodes
CLUSTER_PUBLIC_URL=http://192.168.1.10:8080
CLUSTER_PRIMARY_URL=http://192.168.1.10:8080
CLUSTER_PEERS=http://192.168.1.11:8080,http://192.168.1.12:8080
CLUSTER_PRIORITY=100

BACKUP_MIRROR_1=D:\kanha-mirrors\site-1
BACKUP_MIRROR_2=E:\kanha-mirrors\site-2
BACKUP_MIRROR_3=\\NAS\kanha\site-3
BACKUP_MIRROR_4=
BACKUP_MIRROR_5=
BACKUP_USER_PACK=F:\KanhaUSB\portable
```

**Replica node** example:

```env
CLUSTER_NODE_ID=node-2
CLUSTER_ROLE=replica
CLUSTER_PRIORITY=90
CLUSTER_PUBLIC_URL=http://192.168.1.11:8080
CLUSTER_PRIMARY_URL=http://192.168.1.10:8080
CLUSTER_TOKEN=same-as-primary
CLUSTER_PEERS=http://192.168.1.10:8080,http://192.168.1.12:8080
```

## UI

Open **Resilience / HA** (`#/ha`):

- Sync now / Publish snapshot / Mirror all sites
- Run HA tick
- **Promote this node** (manual failover if auto has not fired)

## APIs

| Method | Path | Auth |
|--------|------|------|
| GET | `/api/ha/status` | JWT + `ha.*` / `settings.*` |
| POST | `/api/ha/sync-now` | JWT |
| POST | `/api/ha/publish` | JWT |
| POST | `/api/ha/mirror-all` | JWT |
| POST | `/api/ha/promote` | JWT |
| POST | `/api/ha/tick` | JWT |
| POST | `/api/ha/heartbeat` | `X-Cluster-Token` |
| GET | `/api/ha/snapshot/meta` | token |
| GET | `/api/ha/snapshot/download` | token |

## Operator playbook

1. **Primary down** → wait ~45s for auto-promote, or open surviving node → Promote.
2. Point DNS / users to new primary URL (or keep a floating VIP).
3. Repair old server → set `CLUSTER_ROLE=replica` → start → it pulls latest.
4. **Brand new machine** → extract `LATEST.zip` → copy DB + uploads → set env as replica → `run.prod.bat`.

## Postgres note

Portable file sync is optimized for **SQLite** packs today. For heavy multi-site Postgres production, keep the same **primary + replica** roles and use Postgres streaming replication / managed HA; mirrors still hold the portable SQLite export for disaster USB restore. The cluster control plane (heartbeat / promote / UI) is the same.

## Bottom line

You get what you asked for — **complete ERP in many places, same latest data, auto continue on crash** — without the data corruption of five writers. That is the safer, production-grade version of your concept.

## What “Primary” means (simple)

- **Primary** = abhi jo machine **writes** (invoice, stock, payment) accept karti hai.
- Yeh **hamesha wahi fixed server nahi** — sirf ek *role* hai.
- Primary crash → highest-priority **live** replica **auto primary** ban jati hai.
- Purani machine repair / naya pack → wapas **replica** ban ke latest data catch karti hai.

## Entry crash auto-heal

Separate from server failover:

1. Bad write → DB **rollback** (half entry save nahi hoti)
2. Payload → **Failed entries** queue (`/api/ha/failed-entries`)
3. UI **Re-enter** → same data dubara submit
4. Browser bhi last failed write draft rakhta hai (`kanha_failed_write`)

Open **Resilience / HA** → Failed entries panel.
