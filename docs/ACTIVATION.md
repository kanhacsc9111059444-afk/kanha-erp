# KanhaERP — Activation & Connection Guide

Common user / IT / owner ke liye. Simple language.

## Goal

KanhaERP ko PC ya pen-drive se chalana, login karna, aur baad me WhatsApp / bank / GST se connect karna.

---

## A. Fastest path (demo / pen-drive)

1. Open portable folder.
2. Read `START_HERE.txt`.
3. Run **`SETUP_PORTABLE.bat`** once (needs Python + internet).
4. Run **`START_KANHA.bat`**.
5. Browser: **http://127.0.0.1:8080**
6. Login with one of the three demo accounts (below).

No cloud account needed for local demo.

---

## B. Demo logins (three)

| Role | Email | Password |
|------|--------|----------|
| **Admin** | `admin@kanhaerp.com` | `admin123` |
| **Sales** | `sales@kanhaerp.com` | `sales123` |
| **Accounts** | `accounts@kanhaerp.com` | `accounts123` |

### Forgot all passwords?

Login page bottom-right **◉ Ultra Support**

- Demo master pass: `KanhaCoreUltra1`
- Or Admin account password
- Then use **Reset PW** to set a new password for any user

Production: set `CORE_CONTROL_PASS` in `.env` (never leave demo default).

---

## C. Activation checklist (company PC)

| Step | What to do | Done? |
|------|------------|-------|
| 1 | Copy folder to `C:\KanhaERP` (or D:) | ☐ |
| 2 | Install Python 3.11+ with PATH | ☐ |
| 3 | Run `SETUP_PORTABLE.bat` | ☐ |
| 4 | Copy `.env.example` → `.env` | ☐ |
| 5 | Change `SECRET_KEY` (long random) | ☐ |
| 6 | Change admin password / `ADMIN_*` | ☐ |
| 7 | Set `CORE_CONTROL_PASS` (owner only) | ☐ |
| 8 | Set `DEMO_MODE=false` when going live | ☐ |
| 9 | Run `START_KANHA.bat` and open browser | ☐ |
| 10 | Settings → Go-live checklist green | ☐ |

---

## D. Connection establish (integrations)

Edit `.env`, then restart KanhaERP.

### 1) WhatsApp Business (Meta Cloud)

```
WHATSAPP_TOKEN=...
WHATSAPP_PHONE_NUMBER_ID=...
WHATSAPP_API_VERSION=v19.0
```

Then open **WhatsApp** module — templates / chase flows.

### 2) Razorpay payments

```
RAZORPAY_KEY_ID=...
RAZORPAY_KEY_SECRET=...
```

### 3) GST e-Invoice / e-Way (GSP)

```
GSP_BASE_URL=...
GSP_API_KEY=...
GSP_API_SECRET=...
```

Demo mode shows `DEMO-EWB-*` / demo paid — live filing needs real GSP.

### 4) Database (bigger companies)

Default = SQLite file in `data/kanha_erp.db` (fine for demo / small office).

Postgres example:

```
DATABASE_URL=postgresql+psycopg2://kanha:STRONG_PASS@127.0.0.1:5432/kanha_erp
```

### 5) LAN access (other PCs on same office network)

1. In `START_KANHA.bat` change `--host 127.0.0.1` to `--host 0.0.0.0`
2. Firewall allow port **8080**
3. Other PC browser: `http://YOUR-PC-IP:8080`
4. Set `CORS_ORIGINS` in `.env` to include that URL

---

## E. First-day user flow

1. Login as **Admin**
2. Click **Start Live Flow** (Lead → Quote → SO → Delivery → Invoice)
3. Check **Approvals** inbox
4. Check **Agents** / Compliance
5. Sales user: CRM + field flow
6. Accounts user: books / GST register / purchase

---

## F. Safety / Ultra Support rules

- Core Control **never deletes** invoices, stock, or users
- Default = **Safe fix** only
- Risky unlocks need **Confirm** + show drawbacks
- Always keep `data/backups` if you run risky confirms

---

## G. Trouble

| Problem | Fix |
|---------|-----|
| Python not found | Reinstall Python, tick Add to PATH |
| Port 8080 busy | Close other KanhaERP / change port in START_KANHA.bat |
| Blank page | Hard refresh Ctrl+F5 |
| Login fail | Use demo passwords or ◉ Ultra Support → Reset PW |
| pip install fail | Check internet / proxy / antivirus |

More: `GO_LIVE.md`, `USER_GUIDE.md`, main `README.md`.
