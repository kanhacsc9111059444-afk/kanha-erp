# White-label — kisi bhi company ka ERP banao

KanhaERP ek product hai. Client ka naam / logo / colors / admin change karke **bina code rewrite** uska ERP ban jata hai.

---

## Step 1 — Copy pack

```
G:\KanhaERP-Final   →   C:\ClientERP   (ya server folder)
```

## Step 2 — `.env`

```bat
copy .env.example .env
notepad .env
```

Minimum change:

```env
APP_NAME=ShreeBalajiERP
BRAND_TAGLINE=Digital ERP
BRAND_SUPPORT_EMAIL=it@client.com
BRAND_PRIMARY=#0b3d91
BRAND_ACCENT=#c45c26
COMPANY_NAME=SHRI BALAJI ALLOYS CORPORATION
COMPANY_CODE=SBAC
COMPANY_GSTIN=22XXXXX....Z5

ADMIN_EMAIL=admin@client.com
ADMIN_PASSWORD=ReplaceWithStrong1
SECRET_KEY=<python -c "import secrets; print(secrets.token_urlsafe(48))">
DEMO_MODE=false
CORS_ORIGINS=https://erp.client.com,http://127.0.0.1:8080
```

## Step 3 — Fresh database (naya client)

```
data\kanha_erp.db   delete (agar purana demo DB hai)
SETUP_PORTABLE.bat  (pehli baar)
START_KANHA.bat
```

Login → naya `ADMIN_EMAIL` / `ADMIN_PASSWORD`.

## Step 4 — Brand / logo

- Logo file: `frontend/assets/` me rakho → `BRAND_LOGO_URL=/assets/your-logo.svg`
- Ya Admin UI brand save (`PUT /api/brand`)

## Step 5 — Live integrations (optional)

| Need | Set in `.env` |
|------|----------------|
| WhatsApp Meta | `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN` |
| Payments | `RAZORPAY_*` |
| e-Invoice | `GSP_*` |
| AI | `LLM_*` |
| Email | `SMTP_*` |

Webhook URL Meta console me:  
`https://YOUR-DOMAIN/api/meta/whatsapp/webhook`

## Step 6 — Production domain (kanhaone.com later)

1. Postgres `DATABASE_URL=...`
2. `DEMO_MODE=false`
3. nginx/Caddy → port 8080 + HTTPS
4. `CORS_ORIGINS=https://kanhaone.com`
5. See `GO_LIVE.md`

---

## Do / Don't

| Do | Don't |
|----|--------|
| Har client ka alag folder + alag `.env` + alag DB | Ek hi live DB pe do companies mix |
| Strong `SECRET_KEY` + admin password | Default `admin123` production me |
| Backup `data/` regularly | `.venv` ko zip me force mat karo (SETUP dubara bana leta hai) |

---

## Checklist before handoff

- [ ] APP_NAME / COMPANY_NAME correct
- [ ] Admin login works
- [ ] DEMO_MODE=false (live)
- [ ] SECRET_KEY not `change-me…`
- [ ] CORS = real domain
- [ ] Backup script / `#/ha` mirrors known
- [ ] Staff trained on `docs/USER_GUIDE.md`
