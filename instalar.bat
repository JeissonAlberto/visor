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

:: ── Instalar como comando del sistema ──────────────────────
echo.
echo  Instalando comando "visor"...
pip install -e . -q
if errorlevel 1 (
    echo  [ERROR] Fallo pip install. Intenta: pip install -e .
    pause
    exit /b 1
)
echo  [OK] Instalado.

:: ── Obtener ruta de scripts Python y agregar al PATH ───────
for /f "delims=" %%s in ('python -c "import sysconfig; print(sysconfig.get_path(\"scripts\"))"') do set SCRIPTS=%%s
echo  [OK] Scripts en: %SCRIPTS%

:: Leer PATH actual del usuario
for /f "skip=2 tokens=3*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set UPATH=%%a %%b

:: Agregar si no está ya
echo %UPATH% | find /i "%SCRIPTS%" >nul 2>&1
if errorlevel 1 (
    setx PATH "%UPATH%;%SCRIPTS%" >nul
    echo  [OK] Ruta agregada al PATH del usuario.
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
