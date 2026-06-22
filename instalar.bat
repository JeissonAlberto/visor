@echo off
:: ============================================================
::  VISOR — Instalador automático para Windows
::  by Jasol Group · Saravena, Arauca, Colombia
::
::  Doble clic en este archivo para instalar.
::  Después abre una nueva terminal y escribe: visor
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
    echo  IMPORTANTE: marca "Add Python to PATH" al instalar.
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo  [OK] Python %PYVER%

:: ── Verificar version 3.10+ ────────────────────────────────
python -c "import sys; exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Necesitas Python 3.10 o superior.
    pause
    exit /b 1
)
echo  [OK] Version compatible.

:: ── Actualizar pip y setuptools ────────────────────────────
echo.
echo  Actualizando pip y setuptools...
python -m pip install --upgrade pip setuptools wheel -q
echo  [OK] pip y setuptools actualizados.

:: ── Instalar como comando del sistema ──────────────────────
echo.
echo  Instalando comando "visor"...
pip install . -q
if errorlevel 1 (
    echo.
    echo  [ERROR] Fallo la instalacion.
    echo  Intenta manualmente: pip install .
    pause
    exit /b 1
)
echo  [OK] Visor instalado.

:: ── Agregar scripts de Python al PATH ──────────────────────
for /f "delims=" %%s in ('python -c "import sysconfig; print(sysconfig.get_path(\"scripts\"))"') do set SCRIPTS=%%s
echo  [OK] Scripts en: %SCRIPTS%

for /f "skip=2 tokens=3*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set UPATH=%%a %%b

echo %UPATH% | find /i "%SCRIPTS%" >nul 2>&1
if errorlevel 1 (
    setx PATH "%UPATH%;%SCRIPTS%" >nul
    echo  [OK] Ruta agregada al PATH.
) else (
    echo  [OK] Ruta ya estaba en PATH.
)

echo.
echo  ============================================================
echo   LISTO. Cierra esta ventana y abre una nueva terminal.
echo.
echo   Luego escribe:
echo.
echo     visor               - Menu principal
echo     visor --scan        - Escaneo rapido
echo     visor --web         - Servicios web
echo     visor --internet    - Test de internet
echo     visor --setup       - Configuracion
echo     visor --report      - Ultimo reporte
echo.
echo  ============================================================
echo.
pause
