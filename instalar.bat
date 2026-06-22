@echo off
:: ============================================================
::  VISOR — Instalador definitivo
::  Crea el comando "visor" que funciona desde cualquier lugar
:: ============================================================
title Visor - Instalador
color 0A

echo.
echo  Instalando Visor...
echo.

:: Guardar ruta actual (donde esta el codigo)
set VISOR_DIR=%~dp0
:: Quitar la barra final
if "%VISOR_DIR:~-1%"=="\" set VISOR_DIR=%VISOR_DIR:~0,-1%

:: Detectar python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python no encontrado. Instala Python 3.10+ desde python.org
    pause & exit /b 1
)

:: Crear el archivo visor.bat en System32 (requiere admin) o en AppData
set DESTINO=%USERPROFILE%\AppData\Local\Microsoft\WindowsApps\visor.bat

echo @echo off > "%DESTINO%"
echo python "%VISOR_DIR%\main.py" %%* >> "%DESTINO%"

if exist "%DESTINO%" (
    echo  [OK] Comando "visor" instalado en: %DESTINO%
) else (
    echo  [AVISO] No se pudo instalar en WindowsApps. Intentando metodo alternativo...
    goto metodo2
)
goto fin

:metodo2
:: Crear en carpeta del usuario y agregar al PATH
set DESTINO2=%USERPROFILE%\visor.bat
echo @echo off > "%DESTINO2%"
echo python "%VISOR_DIR%\main.py" %%* >> "%DESTINO2%"

:: Agregar carpeta del usuario al PATH
for /f "skip=2 tokens=3*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set UPATH=%%a %%b
if not defined UPATH set UPATH=%USERPROFILE%
setx PATH "%UPATH%;%USERPROFILE%" >nul
echo  [OK] Comando "visor" instalado en: %DESTINO2%
echo  [!] Cierra y abre una nueva terminal para que el PATH se actualice.
goto fin

:fin
echo.
echo  ============================================================
echo   LISTO. Abre una nueva terminal CMD y escribe: visor
echo  ============================================================
echo.
pause
