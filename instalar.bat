@echo off
:: ============================================================
::  VISOR — Instalador automático para Windows
::  by Jasol Group · Saravena, Arauca, Colombia
:: ============================================================

title Visor - Instalador
color 0A

echo.
echo  ============================================================
echo   VISOR - Monitor de Red v2.0 - by Jasol Group
echo  ============================================================
echo.

:: ── Verificar Python ───────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python no encontrado.
    echo  Descargalo en: https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo  [OK] Python %PYVER%

:: ── Actualizar pip ─────────────────────────────────────────
echo  Actualizando pip...
python -m pip install --upgrade pip setuptools wheel -q 2>nul
echo  [OK] pip listo.

:: ── Instalar Visor ─────────────────────────────────────────
echo.
echo  Instalando Visor...
python -m pip install . -q --no-warn-script-location
if errorlevel 1 (
    echo  [ERROR] Fallo la instalacion.
    pause
    exit /b 1
)
echo  [OK] Visor instalado.

:: ── Detectar donde quedo visor.exe ─────────────────────────
for /f "delims=" %%s in ('python -c "import sysconfig; print(sysconfig.get_path(\"scripts\"))"') do set SCRIPTS=%%s
echo  [OK] visor.exe esta en: %SCRIPTS%

:: ── Agregar esa ruta al PATH del usuario ───────────────────
for /f "skip=2 tokens=3*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set UPATH=%%a %%b
if not defined UPATH set UPATH=

echo %UPATH% | find /i "%SCRIPTS%" >nul 2>&1
if errorlevel 1 (
    setx PATH "%UPATH%;%SCRIPTS%" >nul
    echo  [OK] Ruta agregada al PATH: %SCRIPTS%
) else (
    echo  [OK] Ruta ya estaba en PATH.
)

:: ── Crear visor.bat de respaldo en la misma carpeta ────────
echo @echo off > visor.bat
echo python "%~dp0main.py" %%* >> visor.bat
echo  [OK] visor.bat creado como respaldo en esta carpeta.

:: ── Copiar visor.bat a una ruta que SI este en PATH ─────────
copy /y visor.bat "%USERPROFILE%\AppData\Local\Microsoft\WindowsApps\visor.bat" >nul 2>&1
if not errorlevel 1 (
    echo  [OK] visor.bat copiado a WindowsApps ^(siempre en PATH^).
)

echo.
echo  ============================================================
echo   LISTO.
echo.
echo   Cierra esta ventana, abre una nueva terminal y escribe:
echo.
echo     visor               - Menu principal
echo     visor --scan        - Escaneo rapido
echo     visor --web         - Servicios web
echo     visor --internet    - Test de internet
echo     visor --setup       - Configuracion
echo     visor --report      - Ultimo reporte
echo.
echo   Si "visor" no funciona, usa desde esta carpeta:
echo     .\visor.bat
echo  ============================================================
echo.
pause
