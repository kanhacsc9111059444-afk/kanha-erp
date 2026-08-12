# KanhaERP — Production Deployment Guide

Your ERP is production-ready. This guide covers deployment, security, and go-live checklist.

---

## Prerequisites

1. **Server/Hosting:** Linux server, Docker-capable or traditional hosting
2. **Database:** PostgreSQL 12+ (recommended for production)
3. **HTTPS:** SSL certificate (Let's Encrypt or provider)
4. **Domain:** Your company domain
5. **Backups:** Daily backup strategy in place

---

## Step 1: Environment Setup

### Create `.env` file

```env
# Application
APP_NAME=YourCompanyERP
APP_VERSION=1.0.0
DEMO_MODE=false

# Security (CRITICAL)
SECRET_KEY=<generate-long-random-string-here>
ADMIN_PASSWORD=<change-this-strong-password>
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Company
COMPANY_NAME=Your Company Pvt Ltd
COMPANY_CODE=YOUR
COMPANY_GSTIN=22AAAAA0000A1Z5
ADMIN_EMAIL=admin@yourdomain.com

# Branding
BRAND_TAGLINE=Your Company Tagline
BRAND_PRIMARY=#1d4ed8
BRAND_ACCENT=#0f766e
BRAND_LOGO_URL=/assets/your-logo.svg
BRAND_SUPPORT_EMAIL=support@yourdomain.com

# Database (PostgreSQL)
DATABASE_URL=postgresql+psycopg2://kanha:secure_password@db.yourdomain.com:5432/kanha_erp

# Redis (for caching)
REDIS_URL=redis://redis:6379/0

# Integrations (optional)
WHATSAPP_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_VERIFY_TOKEN=
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
GSP_BASE_URL=
GSP_API_KEY=
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
MAPS_API_KEY=
LLM_API_KEY=
LLM_PROVIDER=openai
```

---

## Step 2: Database Setup

### Option A: Docker Compose (Easiest)

```bash
docker-compose up -d
# This starts: API, PostgreSQL, Redis
```

### Option B: Manual PostgreSQL

```bash
# Create database
psql -U postgres
CREATE DATABASE kanha_erp;
CREATE USER kanha WITH PASSWORD 'secure_password';
ALTER ROLE kanha SET client_encoding TO 'utf8';
ALTER ROLE kanha SET default_transaction_isolation TO 'read committed';
ALTER ROLE kanha SET default_transaction_deferrable TO on;
GRANT ALL PRIVILEGES ON DATABASE kanha_erp TO kanha;
```

---

## Step 3: Application Deployment

### Option A: Docker (Recommended)

```bash
# Build image
docker build -t kanha-erp:latest .

# Run container
docker run -d \
  --name kanha-erp \
  -p 8000:8000 \
  --env-file .env \
  kanha-erp:latest
```

### Option B: Traditional Deployment

```bash
# Setup backend
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# OR: venv\Scripts\activate  (Windows)

pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Option C: Systemd Service (Linux)

Create `/etc/systemd/system/kanha-erp.service`:

```ini
[Unit]
Description=KanhaERP Service
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/opt/kanha-erp
Environment="PATH=/opt/kanha-erp/venv/bin"
EnvironmentFile=/opt/kanha-erp/.env
ExecStart=/opt/kanha-erp/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl start kanha-erp
sudo systemctl enable kanha-erp
```

---

## Step 4: HTTPS & Reverse Proxy

### Nginx Configuration

Create `/etc/nginx/sites-available/kanha-erp`:

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }
}
```

Enable:

```bash
sudo ln -s /etc/nginx/sites-available/kanha-erp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## Step 5: SSL Certificate (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot certonly --nginx -d yourdomain.com -d www.yourdomain.com
```

---

## Step 6: Security Checklist

- [ ] Change `SECRET_KEY` to strong random string
- [ ] Set `DEMO_MODE=false`
- [ ] Change admin password (not `admin123`)
- [ ] Set `CORS_ORIGINS` to your domain only (never `*`)
- [ ] Enable HTTPS (SSL certificate installed)
- [ ] Configure firewall (only ports 80, 443 open)
- [ ] Set up daily database backups
- [ ] Enable audit logging
- [ ] Configure rate limiting on login API
- [ ] Test email/WhatsApp/payment integrations with real keys
- [ ] Run security scan (OWASP, SQL injection tests)

---

## Step 7: Database Backup

### Daily PostgreSQL Backup Script

```bash
#!/bin/bash
# /opt/kanha-erp/scripts/backup.sh

BACKUP_DIR="/opt/kanha-erp/backups"
DB_NAME="kanha_erp"
DB_USER="kanha"
DB_HOST="localhost"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILENAME="$BACKUP_DIR/kanha_erp_$TIMESTAMP.sql.gz"

mkdir -p $BACKUP_DIR

pg_dump -h $DB_HOST -U $DB_USER $DB_NAME | gzip > $FILENAME

# Keep only last 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Backup created: $FILENAME"
```

Add to crontab:

```bash
crontab -e
# Add: 0 2 * * * /opt/kanha-erp/scripts/backup.sh
```

---

## Step 8: Monitoring & Logs

### Health Check Endpoint

```bash
curl https://yourdomain.com/api/health
```

Expected response:

```json
{
  "ok": true,
  "app": "YourCompanyERP",
  "version": "1.0.0",
  "demo_mode": false,
  "production": true
}
```

### View Logs

```bash
# If using Docker
docker logs -f kanha-erp

# If using systemd
sudo journalctl -u kanha-erp -f
```

---

## Step 9: Initial Setup

1. **Login:** https://yourdomain.com → Admin credentials
2. **Company Setup:** Settings → Company configuration
3. **Users:** Add your team members (Admin → Users)
4. **Roles:** Configure RBAC (Admin → Roles)
5. **Chart of Accounts:** Accounting → Masters
6. **Masters:** Add customers, vendors, products

---

## Common Issues

### Issue: "Connection refused" on database

**Solution:**
```bash
# Check PostgreSQL running
sudo systemctl status postgresql

# Restart if needed
sudo systemctl restart postgresql
```

### Issue: CORS error in browser

**Solution:**
Update `.env` with correct `CORS_ORIGINS`:
```env
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### Issue: 500 error on API calls

**Solution:**
Check application logs:
```bash
docker logs kanha-erp
# Or: journalctl -u kanha-erp
```

---

## Scaling

For high traffic:

1. Use multiple Uvicorn workers
2. Add load balancer (nginx, HAProxy)
3. Use Redis for sessions
4. Enable database connection pooling
5. CDN for static assets

---

## Support

- **Documentation:** See `/docs` folder
- **Health Check:** `GET /api/health`
- **API Docs:** `GET /docs`

---

**Last Updated:** August 2, 2026
