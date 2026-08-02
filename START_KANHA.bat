@echo off
chcp 65001 >nul
cd /d "%~dp0"
set ROOT=%CD%
set PYTHONPATH=%ROOT%\backend
rem Keep DB / backups / mirrors on THIS drive (pen drive) — not Desktop / C: clutter
set KANHA_DATA_ROOT=%ROOT%\data
title KanhaERP

if not exist "%ROOT%\.venv\Scripts\python.exe" (
  echo [WARN] Portable venv missing.
  echo Pehle SETUP_PORTABLE.bat chalao ^(ek baar^).
  pause
  exit /b 1
)

if not exist "%ROOT%\.env" (
  if exist "%ROOT%\.env.example" copy /Y "%ROOT%\.env.example" "%ROOT%\.env" >nul
)

if not exist "%ROOT%\data" mkdir "%ROOT%\data"
if not exist "%ROOT%\data\backups" mkdir "%ROOT%\data\backups"

echo.
echo  KanhaERP starting from: %ROOT%
echo  Data on pen drive: %KANHA_DATA_ROOT%
echo  Open browser: http://127.0.0.1:8080
echo  Stop: Ctrl+C in this window
echo.
echo  Demo logins:
echo    Admin     admin@kanhaerp.com     / admin123
echo    Sales     sales@kanhaerp.com     / sales123
echo    Accounts  accounts@kanhaerp.com  / accounts123
echo  Ultra Support (login page): KanhaCoreUltra1
echo  New: Kanha Books module = #/books
echo.

"%ROOT%\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8080 --app-dir "%ROOT%\backend"
pause
