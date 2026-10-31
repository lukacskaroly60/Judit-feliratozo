@echo off
rem ============================================================
rem  Judit feliratozo - telepitheto valtozat inditasa
rem  Elso inditaskor telepiti a szukseges reszeket a .venv mappaba.
rem ============================================================
chcp 65001 >nul
cd /d "%~dp0"
if exist ".venv\telepites_kesz.txt" goto :start

rem Korabbi, mukodo telepites (ellenorzo jel nelkul): nem kell ujratelepiteni
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -c "import uvicorn, fastapi, multipart, faster_whisper, imageio_ffmpeg" >nul 2>&1 && (
    echo kesz> ".venv\telepites_kesz.txt"
    goto :start
  )
)

rem Megfelelo Python keresese: 64 bites, 3.10 - 3.14 kozotti verzio.
rem (A legujabb Python verziokhoz az AI egyes reszei meg nem jelentek meg.)
set "PY="
for %%V in (3.12 3.13 3.14 3.11 3.10) do if not defined PY (
  py -%%V -c "import struct, sys; sys.exit(struct.calcsize('P') != 8)" >nul 2>&1 && set "PY=py -%%V"
)
if not defined PY (
  python -c "import struct, sys; sys.exit(not ((3, 10) <= sys.version_info[:2] <= (3, 14) and struct.calcsize('P') == 8))" >nul 2>&1 && set "PY=python"
)
if not defined PY goto :nincspython

echo.
echo Elso inditas: a program telepitese, ez par percig tart...
echo (Python: %PY%)
echo.
if exist ".venv" rmdir /s /q ".venv"
%PY% -m venv .venv
if not exist ".venv\Scripts\python.exe" goto :hiba
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :hiba
echo kesz> ".venv\telepites_kesz.txt"

:start
".venv\Scripts\python.exe" -m app
pause
exit /b 0

:nincspython
echo.
echo  Nem talalhato megfelelo Python ezen a gepen.
echo  A programhoz 64 bites Python 3.12 kell (a legujabb, 3.15-os verzio meg NEM jo).
echo.
echo  Megoldas (valassz egyet):
echo   1) Telepitsd a Python 3.12-t (a meglevo Python mellett is lehet):
echo      https://www.python.org/downloads/release/python-31210/
echo      - lent: "Windows installer (64-bit)"
echo      - a telepitoben pipald be: "Add python.exe to PATH"
echo      majd inditsd ujra ezt a fajlt.
echo   2) Vagy hasznald a hordozhato valtozatot, ahhoz nem kell Python:
echo      dupla kattintas a "Hordozhato_elokeszites.bat" fajlra.
echo.
pause
exit /b 1

:hiba
echo.
echo  Hiba tortent a telepites soran. Ellenorizd az internetkapcsolatot,
echo  majd inditsd ujra ezt a fajlt - a telepites elolrol indul.
echo  (Ha ujra hibat kapsz, a fenti uzeneteket kuldd el a fejlesztonek.)
echo.
pause
exit /b 1
