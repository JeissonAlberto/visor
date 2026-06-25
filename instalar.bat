@echo off
echo.
echo   [ Jasol Group - Instalador de Visor v2.8 ]
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
pip install -e .

echo   3. Configurando acceso rapido...
echo   Listo. Ahora puedes usar el comando 'visor' desde cualquier terminal.
echo.
echo   Presiona una tecla para abrir Visor por primera vez...
pause
visor
