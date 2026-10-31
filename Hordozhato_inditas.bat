@echo off
rem ============================================================
rem  Judit feliratozo - HORDOZHATO valtozat inditasa
rem  Semmit nem telepit es nem hagy a gepen: minden ebben a mappaban van.
rem ============================================================
cd /d "%~dp0"
"python\python.exe" -c "import uvicorn, faster_whisper" >nul 2>&1
if errorlevel 1 (
  echo A hordozhato valtozat meg nincs teljesen elokeszitve.
  echo Elobb futtasd le a "Hordozhato_elokeszites.bat" fajlt.
  pause
  exit /b 1
)
rem Az AI modell es minden atmeneti fajl ebben a mappaban maradjon
set "HF_HOME=%~dp0data\hf"
set "HF_HUB_DISABLE_TELEMETRY=1"
set "HF_HUB_DISABLE_SYMLINKS_WARNING=1"
"python\python.exe" -m app
pause
