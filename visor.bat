@echo off
setlocal
set "VISOR_PATH=%~dp0"
python "%VISOR_PATH%main.py" %*
endlocal
