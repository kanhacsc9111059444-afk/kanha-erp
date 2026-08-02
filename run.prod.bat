@echo off
cd /d "%~dp0"
set ROOT=%CD%
set PYTHONPATH=%ROOT%\backend

if not exist "%ROOT%\.env" (
  echo [ERROR] .env missing. Copy .env.example to .env and set SECRET_KEY + DEMO_MODE=false
  if exist "%ROOT%\.env.example" copy "%ROOT%\.env.example" "%ROOT%\.env"
  pause
  exit /b 1
)

set PY=%ROOT%\.venv\Scripts\python.exe
if not exist "%PY%" set PY=%ROOT%\backend\.venv\Scripts\python.exe
if not exist "%PY%" set PY=python

echo.
echo KanhaERP PRODUCTION — http://0.0.0.0:8080
echo Put nginx/Caddy TLS in front. Keys in .env = live integrations.
echo.
"%PY%" -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --app-dir "%ROOT%\backend" --workers 1
