@echo off
chcp 65001 >nul
cd /d "%~dp0"
set ROOT=%CD%
title KanhaERP Portable Setup

echo.
echo  ========================================
echo   KanhaERP — Portable Setup (first run)
echo  ========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python not found in PATH.
  echo Install Python 3.11+ from https://www.python.org/downloads/
  echo Tick "Add python.exe to PATH" during install.
  pause
  exit /b 1
)

python --version
echo.

if not exist "%ROOT%\.venv\Scripts\python.exe" (
  echo [1/3] Creating virtual environment...
  python -m venv "%ROOT%\.venv"
  if errorlevel 1 (
    echo [ERROR] venv create failed.
    pause
    exit /b 1
  )
) else (
  echo [1/3] Virtual environment already exists.
)

echo [2/3] Installing packages...
"%ROOT%\.venv\Scripts\python.exe" -m pip install --upgrade pip
"%ROOT%\.venv\Scripts\python.exe" -m pip install -r "%ROOT%\backend\requirements.txt"
if errorlevel 1 (
  echo [ERROR] pip install failed. Check internet / antivirus.
  pause
  exit /b 1
)

if not exist "%ROOT%\.env" (
  if exist "%ROOT%\.env.example" (
    copy /Y "%ROOT%\.env.example" "%ROOT%\.env" >nul
    echo [3/3] Created .env from .env.example ^(demo defaults^).
  ) else (
    echo [3/3] No .env.example — using built-in demo defaults.
  )
) else (
  echo [3/3] .env already present.
)

if not exist "%ROOT%\data" mkdir "%ROOT%\data"

echo.
echo  SETUP DONE.
echo  Ab START_KANHA.bat double-click karo.
echo  Browser: http://127.0.0.1:8080
echo.
pause
