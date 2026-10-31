@echo off
rem ============================================================
rem  Judit feliratozo - HORDOZHATO valtozat elokeszitese
rem  Egyszer kell lefuttatni (internet kell hozza). Mindent ebbe a
rem  mappaba tolt le (pl. pendrive-ra), a gepre nem telepit semmit.
rem ============================================================
setlocal
cd /d "%~dp0"
set "PYVER=3.12.10"
set "HF_HOME=%~dp0data\hf"
set "HF_HUB_DISABLE_TELEMETRY=1"
set "HF_HUB_DISABLE_SYMLINKS_WARNING=1"

echo.
echo  Judit feliratozo - hordozhato valtozat elokeszitese
echo  Mappa: %~dp0
echo.

if exist "python\python.exe" goto :pip
echo [1/3] Python letoltese (kb. 10 MB)...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing 'https://www.python.org/ftp/python/%PYVER%/python-%PYVER%-embed-amd64.zip' -OutFile 'python.zip'; Expand-Archive -Force 'python.zip' 'python'; Remove-Item 'python.zip'"
if not exist "python\python.exe" goto :hiba
rem A beagyazott Python alapbol nem lat telepitett csomagokat es a program mappajat sem:
rem bekapcsoljuk a site-packages-t es hozzaadjuk a program mappajat ("..").
powershell -NoProfile -ExecutionPolicy Bypass -Command "$f='python\python312._pth'; $t=(Get-Content $f) -replace '^#\s*import site','import site'; $t += '..'; Set-Content -Encoding ASCII $f $t"
if errorlevel 1 goto :hiba

:pip
"python\python.exe" -c "import uvicorn, fastapi, multipart, faster_whisper, imageio_ffmpeg" >nul 2>&1 && goto :runtime
echo [2/3] Szukseges reszek letoltese (kb. 300 MB)...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing 'https://bootstrap.pypa.io/get-pip.py' -OutFile 'python\get-pip.py'"
if not exist "python\get-pip.py" goto :hiba
"python\python.exe" "python\get-pip.py" --no-cache-dir --no-warn-script-location
if errorlevel 1 goto :hiba
"python\python.exe" -m pip install --no-cache-dir --no-warn-script-location -r requirements.txt
if errorlevel 1 goto :hiba
del "python\get-pip.py"

:runtime
rem Az AI reszei a Microsoft Visual C++ futtatokornyezetet hasznaljak. Ha ezen a gepen
rem megvan, bemasoljuk a Python melle, hogy olyan gepen is fusson, ahol nincs telepitve.
for %%D in (msvcp140.dll msvcp140_1.dll msvcp140_2.dll vcruntime140.dll vcruntime140_1.dll concrt140.dll) do (
  if not exist "python\%%D" if exist "%SystemRoot%\System32\%%D" copy /y "%SystemRoot%\System32\%%D" "python\%%D" >nul
)
"python\python.exe" -c "import faster_whisper, ctranslate2" 2>nul
if errorlevel 1 goto :vcredist

:model
echo.
echo [3/3] AI modell letoltese a mappaba (hogy kesobb internet nelkul is mukodjon)
echo    1 = Legpontosabb (large-v3, kb. 3 GB) - ajanlott
echo    2 = Gyorsabb (large-v3-turbo, kb. 1,6 GB)
echo    3 = Mindketto (kb. 4,6 GB)
echo    4 = Most egyiket sem (az elso hasznalatkor toltodik le)
choice /c 1234 /n /m "Valassz (1/2/3/4): "
set "VALASZ=%errorlevel%"
if "%VALASZ%"=="1" call :letolt large-v3 || goto :hiba
if "%VALASZ%"=="2" call :letolt large-v3-turbo || goto :hiba
if "%VALASZ%"=="3" call :letolt large-v3 || goto :hiba
if "%VALASZ%"=="3" call :letolt large-v3-turbo || goto :hiba

echo.
echo  KESZ! Inditas: dupla kattintas a "Hordozhato_inditas.bat" fajlra.
echo  A teljes mappa (pl. a pendrive) barmelyik 64 bites Windowsos gepen hasznalhato.
echo.
pause
exit /b 0

:letolt
echo  Letoltes: %1 ...
"python\python.exe" -c "from faster_whisper import download_model; download_model('%1')"
exit /b %errorlevel%

:vcredist
echo.
echo  HIBA: hianyzik a Microsoft Visual C++ futtatokornyezet ezen a gepen.
echo  Toltsd le es telepitsd innen, majd futtasd ujra ezt a fajlt:
echo    https://aka.ms/vs/17/release/vc_redist.x64.exe
echo.
pause
exit /b 1

:hiba
echo.
echo  HIBA tortent az elokeszites soran. Ellenorizd az internetkapcsolatot,
echo  majd futtasd ujra ezt a fajlt - onnan folytatja, ahol abbahagyta.
echo  (Ha nem sikerul, a fenti uzeneteket kuldd el a fejlesztonek.)
echo.
pause
exit /b 1
