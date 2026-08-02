@echo off
cd /d "%~dp0"
set ROOT=%CD%
set PYTHONPATH=%ROOT%\backend

if not exist "%ROOT%\.env" (
  echo [WARN] .env missing — copy .env.example to .env before production go-live.
  if exist "%ROOT%\.env.example" echo        copy "%ROOT%\.env.example" "%ROOT%\.env"
)

REM Prefer local project venv, then backend venv, then trading-engine venv, then system python
set PY=%ROOT%\.venv\Scripts\python.exe
if not exist "%PY%" set PY=%ROOT%\backend\.venv\Scripts\python.exe
if not exist "%PY%" set PY=c:\Users\HP\Projects\kanha-ai-trading-engine\.venv\Scripts\python.exe
if not exist "%PY%" set PY=python

echo Starting KanhaERP on http://127.0.0.1:8080
echo Tip: production use run.prod.bat + .env ^(DEMO_MODE=false^). See GO_LIVE.md
"%PY%" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8080 --app-dir "%ROOT%\backend"
