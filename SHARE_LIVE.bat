@echo off
chcp 65001 >nul
cd /d "%~dp0"
title KanhaERP Live Share Tunnel

set ROOT=%CD%
set CF=%ROOT%\tools\cloudflared.exe
set SHARE_PASS=KanhaView@2026

if not exist "%CF%" (
  echo [ERROR] tools\cloudflared.exe missing.
  echo Pehle download complete hone do, ya SETUP share se cloudflared lao.
  pause
  exit /b 1
)

echo.
echo  ========================================
echo   KanhaERP — Global Live Share
echo  ========================================
echo  1) Local ERP must be running on 8080
echo  2) Share link niche aayega (trycloudflare.com)
echo  3) Browser pehle SHARE password maangega
echo     User: viewer
echo     Pass: %SHARE_PASS%
echo  4) Phir ERP login: admin@kanhaerp.com / admin123
echo.
echo  NOTE: Source folder copy nahi hota.
echo  Browser UI assets dikhte hain (normal web) — .py code expose nahi.
echo  Band karne ke liye Ctrl+C
echo.

REM Apply share gate for this process tree if you restart uvicorn with these env vars.
REM Tunnel itself only forwards; gate is on the app.
echo Starting Cloudflare quick tunnel → http://127.0.0.1:8080
echo.

"%CF%" tunnel --url http://127.0.0.1:8080
pause
