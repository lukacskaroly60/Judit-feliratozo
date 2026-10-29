@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Elso inditas: a program telepitese, ez par percig tart...
  py -3 -m venv .venv 2>nul || python -m venv .venv
  if not exist .venv\Scripts\python.exe (
    echo Nincs telepitve a Python. Telepitsd innen: https://www.python.org/downloads/
    pause
    exit /b 1
  )
  .venv\Scripts\python -m pip install --upgrade pip
  .venv\Scripts\python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Hiba a telepites soran.
    pause
    exit /b 1
  )
)
.venv\Scripts\python -m app
pause
