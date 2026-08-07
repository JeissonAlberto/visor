@echo off
setlocal
set "VISOR_ROOT=%~dp0"
if exist "%VISOR_ROOT%.venv\Scripts\python.exe" (
    "%VISOR_ROOT%.venv\Scripts\python.exe" "%VISOR_ROOT%main.py" %*
) else (
    python "%VISOR_ROOT%main.py" %*
)
set "EXIT_CODE=%ERRORLEVEL%"
endlocal & exit /b %EXIT_CODE%
