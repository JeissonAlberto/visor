@echo off
echo.
echo   [ Jasol Group - Instalador de Visor v5.2.1 ]
echo   ------------------------------------------
echo.
echo   1. Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   [ERROR] Python no esta instalado o no esta en el PATH.
    pause
    exit /b
)

echo   2. Instalando Visor como comando global...
pip install -e . --force-reinstall

echo   3. Configurando acceso rapido...
echo   Listo. Ahora puedes usar el comando 'visor' desde cualquier terminal.
echo.
pause
visor
