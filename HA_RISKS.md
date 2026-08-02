# KanhaERP — Realtime risks & protections

Pehle se protect — baad me firefight nahi.

| # | Real problem | Kya tootega | Protection (ab code me) | Aapka config action |
|---|--------------|-------------|-------------------------|---------------------|
| 1 | **Split-brain** | 2 primaries → double invoice/stock | Fence epoch + heartbeat auto-demote + priority/node_id tie-break | Peers same `CLUSTER_TOKEN` |
| 2 | **False failover** | Network blip pe galat promote | HTTP probe gate (`CLUSTER_MIN_FAILOVER_PROBES=2`) | Keep probes ≥2 |
| 3 | **Old primary returns** | Purana server phir writes | Higher fence dekhe → auto demote to replica | Restart old node as replica after repair |
| 4 | **Same-disk “5 mirrors”** | Disk crash = sab gaye | Risk board flags same-disk | `BACKUP_MIRROR_1..5` alag drives/NAS + USB pack |
| 5 | **No hot replica** | Primary down → sirf zip, live ERP nahi | Go-live + risks checklist | Kam se kam 1 peer in `CLUSTER_PEERS` |
| 6 | **Client hits dead URL** | Browser purane server pe | 409 `redirect_writes` + UI confirm open primary | Prefer floating DNS/VIP later |
| 7 | **Duplicate Re-enter** | Crash ke baad double doc | `X-Idempotency-Key` middleware | UI already sends keys |
| 8 | **Entry mid-crash** | Half row | DB rollback + Failed entries queue | Use Resilience → Re-enter |
| 9 | **Pack apply overlap** | Corrupt DB | Apply lock + `.incoming` + `.prev` + checksum | — |
| 10 | **Default cluster token** | Fake node join | Checklist + risks red | Strong `CLUSTER_TOKEN` |
| 11 | **SQLite sync lag** | Seconds-level lag under load | Checksum sync; Postgres recommended | Prod: Postgres URL |
| 12 | **Replica write by mistake** | Split data | Middleware blocks writes on replica | Banner shows PRIMARY URL |

## UI

**Resilience / HA** → “Realtime risks (protected now)” panel  
Also: top banner PRIMARY / HOT REPLICA

## API

- `GET /api/ha/risks` — full board  
- `GET /api/ha/status` — includes `fence_epoch`, `risks_open`

## Env knobs

```env
CLUSTER_REQUIRE_PROBE=true
CLUSTER_MIN_FAILOVER_PROBES=2
CLUSTER_FAILOVER_AFTER_SECONDS=45
CLUSTER_TOKEN=long-random-shared
CLUSTER_PEERS=http://192.168.1.11:8080
BACKUP_MIRROR_1=D:\kanha\m1
BACKUP_MIRROR_2=E:\kanha\m2
BACKUP_USER_PACK=F:\USB\kanha
```

## Honest limit

Zero physical downtime **across the whole internet** needs floating IP / DNS / load balancer in front. App layer already: auto-promote, demote, heal, idempotency, multi-mirror. Infra VIP = next upgrade when you go multi-site live.
