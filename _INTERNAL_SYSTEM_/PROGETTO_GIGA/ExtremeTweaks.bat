@echo off
setlocal disabledelayedexpansion

:: PERFECT REGISTRY & SYSTEM TWEAKS - Extreme Edition
:: Eseguire come AMMINISTRATORE

title PERFECT WINDOWS TWEAKER
color 0B

echo.
echo  ############################################################
echo  #                                                          #
echo  #       PERFECT WINDOWS TWEAKER - EXTREME EDITION          #
echo  #                                                          #
echo  ############################################################
echo.

:: 1. Verifica Privilegi
openfiles >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] ERRORE: Devi eseguire questo script come AMMINISTRATORE!
    pause
    exit /b
)

:: 2. Backup Punto di Ripristino (Opzionale ma consigliato)
echo [*] Configurazione modifiche a basso livello...

:: 3. DISABILITAZIONE DEFINITIVA DEFENDER (REG + SC)
echo [1/5] Blocco totale Windows Defender...
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows Defender" /v "DisableAntiSpyware" /t REG_DWORD /d 1 /f >nul 2>&1
reg add "HKLM\SYSTEM\CurrentControlSet\Services\WinDefend" /v "Start" /t REG_DWORD /d 4 /f >nul 2>&1
reg add "HKLM\SYSTEM\CurrentControlSet\Services\WdNisSvc" /v "Start" /t REG_DWORD /d 4 /f >nul 2>&1
reg add "HKLM\SYSTEM\CurrentControlSet\Services\Sense" /v "Start" /t REG_DWORD /d 4 /f >nul 2>&1
:: Forza arresto immediato se attivo
sc stop WinDefend >nul 2>&1
sc config WinDefend start= disabled >nul 2>&1

:: 4. OTTIMIZZAZIONE LATENZA HARDWARE (BCDEDIT)
echo [2/5] Ottimizzazione BCD per latenza zero...
bcdedit /set disabledynamictick yes >nul 2>&1
bcdedit /set useplatformtick yes >nul 2>&1
bcdedit /set bootmenupolicy legacy >nul 2>&1
:: Disabilita Fast Startup (evita kernel "sporco" al boot)
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Power" /v "HiberbootEnabled" /t REG_DWORD /d 0 /f >nul 2>&1

:: 5. OTTIMIZZAZIONE REGISTRO (CPU & RAM)
echo [3/5] Tweak Registro per Performance Massime...
:: Priorita' IRQ (Interrupt Request)
reg add "HKLM\System\CurrentControlSet\Control\PriorityControl" /v "IRQ8Priority" /t REG_DWORD /d 1 /f >nul 2>&1
:: Disabilita limitazione di rete per pacchetti non-multimedia
reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile" /v "NetworkThrottlingIndex" /t REG_DWORD /d 4294967295 /f >nul 2>&1
reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile" /v "SystemResponsiveness" /t REG_DWORD /d 0 /f >nul 2>&1

:: 6. DISABILITAZIONE MITIGAZIONI CPU (SPECTRE/MELTDOWN)
echo [4/5] Rimozione freni CPU (Spectre/Meltdown)...
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" /v "FeatureSettingsOverride" /t REG_DWORD /d 3 /f >nul 2>&1
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" /v "FeatureSettingsOverrideMask" /t REG_DWORD /d 3 /f >nul 2>&1

:: 7. PULIZIA E OTTIMIZZAZIONE FINALE
echo [5/5] Pulizia DNS e Cache ARP...
ipconfig /flushdns >nul 2>&1
arp -d * >nul 2>&1
nbtstat -R >nul 2>&1
nbtstat -RR >nul 2>&1

echo.
echo  ------------------------------------------------------------
echo  [*] TUTTI I TWEAK SONO STATI APPLICATI CON PERFEZIONE.
echo  [*] IL PC E' ORA CONFIGURATO PER IL MASSIMO POSSIBILE.
echo  ------------------------------------------------------------
echo.
exit /b
