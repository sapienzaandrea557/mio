@echo off
setlocal
title SUPER AGENTE - WEB EXPLORER
cd /d "%~dp0"

:: Controlla se node_modules esiste in _WEB_INTERFACE_
if not exist "_WEB_INTERFACE_\node_modules" (
    echo ???? Installazione dipendenze in corso...
    cd /d "_WEB_INTERFACE_"
    npm install
    cd /d ".."
)

echo 🚀 Avvio Rapido Super Agente...
cd /d "_WEB_INTERFACE_"
call npx tsx ..\_INTERNAL_SYSTEM_\CORE_SUPER_AGENTE\web_explorer.ts
cd /d ".."
pause
endlocal
