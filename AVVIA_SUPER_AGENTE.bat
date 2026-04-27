@echo off
setlocal
title SUPER AGENTE - WEB EXPLORER
cd /d "%~dp0"

:: Controlla se node_modules esiste, altrimenti installa (opzionale, ma utile)
if not exist node_modules (
    echo ???? Installazione dipendenze in corso...
    npm install
)

echo 🚀 Avvio Rapido Super Agente...
call npx tsx CORE_SUPER_AGENTE\web_explorer.ts
pause
endlocal
