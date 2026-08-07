@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "VENV=%ROOT%\.venv"
set "PYTHON="

echo.
echo   VISOR - Instalador automatico para Windows
echo   --------------------------------------------
echo.

where py >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON=py -3"
) else (
    where python >nul 2>&1
    if %errorlevel% equ 0 set "PYTHON=python"
)

if not defined PYTHON (
    echo   [ERROR] Python 3.10+ no esta instalado o no esta en el PATH.
    echo   Descargalo desde https://www.python.org/downloads/windows/
    if not defined VISOR_NO_PAUSE pause
    exit /b 1
)

%PYTHON% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)"
if %errorlevel% neq 0 (
    echo   [ERROR] Visor necesita Python 3.10 o superior.
    if not defined VISOR_NO_PAUSE pause
    exit /b 1
)

echo   [1/4] Creando entorno aislado...
if not exist "%VENV%\Scripts\python.exe" (
    %PYTHON% -m venv "%VENV%"
    if %errorlevel% neq 0 (
        echo   [ERROR] No se pudo crear el entorno virtual.
        if not defined VISOR_NO_PAUSE pause
        exit /b 1
    )
) else (
    echo         Entorno existente reutilizado.
)

echo   [2/4] Instalando Visor...
set "PIP_USER=0"
"%VENV%\Scripts\python.exe" -m pip install --no-user --editable "%ROOT%" --no-deps --quiet
if %errorlevel% neq 0 (
    echo   [ERROR] No se pudo instalar Visor.
    if not defined VISOR_NO_PAUSE pause
    exit /b 1
)

echo   [3/4] Agregando Visor al PATH del usuario...
set "VISOR_ROOT=%ROOT%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$root=$env:VISOR_ROOT; $p=[Environment]::GetEnvironmentVariable('Path','User'); $parts=@($p -split ';' | Where-Object { $_ -and $_ -ne $root }); [Environment]::SetEnvironmentVariable('Path', (($parts + $root) -join ';'), 'User')"
if %errorlevel% neq 0 (
    echo   [AVISO] No se pudo modificar el PATH automaticamente.
    echo          Puedes usar "%ROOT%\visor.bat" directamente.
)

set "PATH=%ROOT%;%PATH%"

echo   [4/4] Verificando comando visor...
call "%ROOT%\visor.bat" --version
if %errorlevel% neq 0 (
    echo   [ERROR] La comprobacion de Visor fallo.
    if not defined VISOR_NO_PAUSE pause
    exit /b 1
)

echo.
echo   INSTALACION TERMINADA.
echo   Abre una terminal nueva y escribe: visor
 echo.
if not defined VISOR_NO_PAUSE pause
endlocal
