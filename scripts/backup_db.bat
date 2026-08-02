@echo off
cd /d "%~dp0.."
set ROOT=%CD%
set PYTHONPATH=%ROOT%\backend
set PY=%ROOT%\backend\.venv\Scripts\python.exe
if not exist "%PY%" set PY=%ROOT%\.venv\Scripts\python.exe
if not exist "%PY%" set PY=python
"%PY%" -c "from app.services.backup import backup_sqlite; import json; print(json.dumps(backup_sqlite(), indent=2))"
pause
