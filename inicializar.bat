@echo off
setlocal
cd /d "%~dp0"

REM Atalho para rodar o inicializar.ps1 com duplo-clique
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0inicializar.ps1" %*

endlocal
