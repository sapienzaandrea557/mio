@echo off
setlocal enabledelayedexpansion

:: ULTIMATE OPTIMIZER RUNNER
:: Esegue ExtremeTweaks.bat e OptimizeWindows.ps1 come AMMINISTRATORE
:: Mostra l'output e un report finale di successo/errore.

title ULTIMATE WINDOWS OPTIMIZER - RUNNER
color 0B

:: 1. Verifica Privilegi Amministratore e imposta directory corrente
cd /d "%~dp0"
openfiles >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] ERRORE: Devi eseguire questo script come AMMINISTRATORE!
    echo Facendo clic destro e selezionando "Esegui come amministratore".
    pause
    exit /b
)

echo.
echo  ############################################################
echo  #                                                          #
echo  #       ULTIMATE WINDOWS OPTIMIZER - MASTER RUNNER         #
echo  #                                                          #
echo  ############################################################
echo.

set "STATUS_BATCH=OK"
set "STATUS_PS=OK"

:: 2. Esecuzione ExtremeTweaks.bat
echo [*] AVVIO: ExtremeTweaks.bat (Registro e Basso Livello)...
echo ------------------------------------------------------------
call "ExtremeTweaks.bat"
if %errorlevel% neq 0 (
    set "STATUS_BATCH=ERRORE (Exit Code: %errorlevel%)"
) else (
    set "STATUS_BATCH=COMPLETATO CON SUCCESSO"
)
echo.
echo [*] ATTESA 2 SECONDI PRIMA DI PROCEDERE...
timeout /t 2 >nul
echo ------------------------------------------------------------
echo.

:: 3. Esecuzione OptimizeWindows.ps1
echo [*] AVVIO: OptimizeWindows.ps1 (Servizi, Network e Pulizia)...
echo ------------------------------------------------------------
powershell -ExecutionPolicy Bypass -File "%~dp0OptimizeWindows.ps1"
if %errorlevel% neq 0 (
    set "STATUS_PS=ERRORE (Exit Code: %errorlevel%)"
) else (
    set "STATUS_PS=COMPLETATO CON SUCCESSO"
)
echo ------------------------------------------------------------
echo.

:: 4. Report Finale
echo  ============================================================
echo               REPORT FINALE DI OTTIMIZZAZIONE
echo  ============================================================
echo.
echo  1. ExtremeTweaks.bat:    %STATUS_BATCH%
echo  2. OptimizeWindows.ps1:  %STATUS_PS%
echo.
echo  ------------------------------------------------------------
if "%STATUS_BATCH%"=="COMPLETATO CON SUCCESSO" if "%STATUS_PS%"=="COMPLETATO CON SUCCESSO" (
    echo  [*] STATO GENERALE: PERFETTO - TUTTE LE MODIFICHE APPLICATE.
    echo  [*] IL PC E' ORA OTTIMIZZATO AL MASSIMO.
) else (
    echo  [*] STATO GENERALE: PARZIALE - ALCUNE MODIFICHE HANNO AVUTO ERRORI.
    echo  [i] Controlla i log sopra per i dettagli.
)
echo  ------------------------------------------------------------
echo.
echo  RICORDA: RIAVVIA IL PC PER RENDERE EFFETTIVI TUTTI I TWEAK.
echo.
pause
exit /b
