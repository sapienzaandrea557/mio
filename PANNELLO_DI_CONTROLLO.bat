@echo off
setlocal enabledelayedexpansion
title SUPER AGENTS - CENTRAL CONTROL PANEL
color 0B

:MENU
cls
echo ============================================================
echo           SUPER AGENTS - PANNELLO DI CONTROLLO
echo ============================================================
echo.
echo [1] PROGETTO SCUOLE: Avvia Dashboard Amministrativa (Flask)
echo [2] PROGETTO SCUOLE: Sincronizza Database MIUR (Open Data)
echo [3] PROGETTO SCUOLE: Avvia Monitor di Sistema (Alerts)
echo [4] PROGETTO GIGA: Avvia Bandwidth Eater (God-Mode)
echo [5] PROGETTO GIGA: Monitor Traffico in Tempo Reale
echo [6] PROGETTO MIO: Avvia Super Agente (ADB/Controllo)
echo [7] PROGETTO MIO: Aim Assist Ultra (Rete)
echo [8] APRI DOCUMENTAZIONE: Istruzioni Expert Policy
echo [9] GIT: Sincronizza tutto (Add, Commit, Push)
echo [0] ESCI
echo.
echo ============================================================
set /p choice="Seleziona un'opzione (0-9): "

if "%choice%"=="1" goto SCUOLE_DASH
if "%choice%"=="2" goto SCUOLE_MIUR
if "%choice%"=="3" goto SCUOLE_MONITOR
if "%choice%"=="4" goto GIGA_EATER
if "%choice%"=="5" goto GIGA_MONITOR
if "%choice%"=="6" goto MIO_SUPER
if "%choice%"=="7" goto MIO_ASSIST
if "%choice%"=="8" goto DOCS
if "%choice%"=="9" goto GIT_SYNC
if "%choice%"=="0" exit
goto MENU

:SCUOLE_DASH
echo Avvio Dashboard Scuole...
cd /d "d:\ANDREA\GitHub\Scuole\CORE_SCUOLE"
start python dashboard.py
pause
goto MENU

:SCUOLE_MIUR
echo Sincronizzazione Database MIUR...
cd /d "d:\ANDREA\GitHub\Scuole\CORE_SCUOLE"
python -c "from scuole_sicurezza_stradale import sincronizza_database_miur; sincronizza_database_miur(force=True)"
pause
goto MENU

:SCUOLE_MONITOR
echo Avvio Monitoraggio Sistema...
cd /d "d:\ANDREA\GitHub\Scuole\CORE_SCUOLE"
start python monitor_system.py
pause
goto MENU

:GIGA_EATER
echo Avvio Bandwidth Eater (God-Mode)...
cd /d "d:\ANDREA\GitHub\Giga\CORE_GIGA"
start python bandwidth_eater_ultimate.py
pause
goto MENU

:GIGA_MONITOR
echo Avvio Counter Giga...
cd /d "d:\ANDREA\GitHub\Giga\CORE_GIGA"
start python real_time_giga_counter.py
pause
goto MENU

:MIO_SUPER
echo Avvio Super Agente...
cd /d "d:\ANDREA\GitHub\mio"
start AVVIA_SUPER_AGENTE.bat
pause
goto MENU

:MIO_ASSIST
echo Avvio Aim Assist Ultra...
cd /d "d:\ANDREA\GitHub\mio\_INTERNAL_SYSTEM_\rete"
start python aim_assist_ultra.py
pause
goto MENU

:DOCS
echo Apertura Documentazione...
start notepad "d:\ANDREA\GitHub\mio\INSTRUCTIONS_TRAE.md"
goto MENU

:GIT_SYNC
echo Sincronizzazione Git in corso...
cd /d "d:\ANDREA\GitHub\mio"
git add .
git commit -m "Auto-sync from Central Control Panel"
git push origin main
echo Sync completato per 'mio'.
echo (Nota: Per 'Scuole' e 'Giga', configura il remote URL prima di sincronizzare)
pause
goto MENU
