@echo off
:: ============================================================
::  VISOR — Instalador automático para Windows
::  by Jasol Group · Saravena, Arauca, Colombia
::
::  Ejecutar como: instalar.bat
::  (doble clic o desde PowerShell)
:: ============================================================

title Visor - Instalador automatico
color 0A

echo.
echo  ============================================================
echo   VISOR - Monitor de Red v2.0 - by Jasol Group
echo   Instalador automatico para Windows
echo  ============================================================
echo.

:: ── 1. Verificar Python ────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python no esta instalado o no esta en el PATH.
    echo.
    echo  Descargalo desde: https://www.python.org/downloads/
    echo  IMPORTANTE: Al instalar, marca la opcion "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo  [OK] Python encontrado: %PYVER%

:: ── 2. Verificar version minima 3.10 ───────────────────────
python -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Necesitas Python 3.10 o superior.
    echo  Version actual: %PYVER%
    echo  Descarga la ultima version en: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo  [OK] Version de Python compatible.

:: ── 3. Verificar pip ───────────────────────────────────────
pip --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] pip no encontrado. Reinstala Python con pip incluido.
    pause
    exit /b 1
)
echo  [OK] pip disponible.
echo.

:: ── 4. Instalar Visor como comando del sistema ─────────────
echo  Instalando Visor...
pip install -e . --quiet
if errorlevel 1 (
    echo.
    echo  [ERROR] Fallo la instalacion con pip install.
    echo  Intenta manualmente: pip install -e .
    pause
    exit /b 1
)

echo  [OK] Visor instalado correctamente.
echo.

:: ── 5. Verificar que el comando visor funciona ─────────────
visor --version >nul 2>&1
if errorlevel 1 (
    echo  [AVISO] El comando "visor" no se reconoce todavia en esta sesion.
    echo  Esto es normal en Windows - cierra y vuelve a abrir PowerShell.
    echo.
    echo  Mientras tanto, puedes usar:
    echo    python main.py
    echo.
) else (
    echo  [OK] Comando "visor" disponible globalmente.
    echo.
)

:: ── 6. Agregar scripts de Python al PATH automaticamente ───
echo  Agregando scripts de Python al PATH del sistema...
for /f "delims=" %%p in ('python -c "import sysconfig; print(sysconfig.get_path(\"scripts\"))"') do set SCRIPTS_DIR=%%p

if defined SCRIPTS_DIR (
    :: Agregar al PATH del usuario actual (no requiere admin)
    for /f "skip=2 tokens=3*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set CURRENT_PATH=%%a %%b
    
    echo %CURRENT_PATH% | find /i "%SCRIPTS_DIR%" >nul 2>&1
    if errorlevel 1 (
        setx PATH "%CURRENT_PATH%;%SCRIPTS_DIR%" >nul 2>&1
        echo  [OK] Directorio de scripts agregado al PATH: %SCRIPTS_DIR%
        echo  [!] Cierra y vuelve a abrir PowerShell para aplicar los cambios.
    ) else (
        echo  [OK] El directorio de scripts ya esta en el PATH.
    )
) else (
    echo  [AVISO] No se pudo detectar el directorio de scripts de Python.
)

echo.
echo  ============================================================
echo   INSTALACION COMPLETADA
echo  ============================================================
echo.
echo   Comandos disponibles (abre una nueva terminal):
echo.
echo     visor               -^> Menu interactivo principal
echo     visor --scan        -^> Escaneo rapido de dispositivos
echo     visor --web         -^> Verificar servicios web
echo     visor --internet    -^> Test de calidad de internet
echo     visor --setup       -^> Asistente de configuracion
echo     visor --report      -^> Ver ultimo reporte
echo.
echo   Si "visor" no funciona en esta sesion, usa:
echo     python main.py
echo.
echo  ============================================================
echo.
pause
