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

:: Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python no encontrado.
    echo  Descargalo en: https://www.python.org/downloads/
    pause & exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo  [OK] Python %PYVER%

:: Ruta del codigo
set VISOR_DIR=%~dp0
if "%VISOR_DIR:~-1%"=="\" set VISOR_DIR=%VISOR_DIR:~0,-1%

:: Crear comando visor en WindowsApps (siempre en PATH, sin admin)
set DESTINO=%USERPROFILE%\AppData\Local\Microsoft\WindowsApps\visor.bat
echo @echo off > "%DESTINO%"
echo python "%VISOR_DIR%\main.py" %* >> "%DESTINO%"

if exist "%DESTINO%" (
    echo  [OK] Comando "visor" instalado.
) else (
    echo  [ERROR] No se pudo crear el comando.
    pause & exit /b 1
)

echo.
echo  ============================================================
echo   LISTO. Abre una nueva terminal y escribe: visor
echo.
echo     visor               - Menu principal
echo     visor --scan        - Escaneo rapido
echo     visor --web         - Servicios web
echo     visor --internet    - Test de internet
echo     visor --setup       - Configuracion
echo     visor --report      - Ultimo reporte
echo  ============================================================
echo.
pause
