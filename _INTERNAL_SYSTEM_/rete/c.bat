@echo off
setlocal enabledelayedexpansion

:: 1. Chiude i programmi noti (Apache, Node, Nginx)
echo [1] Chiusura software web...
taskkill /F /IM httpd.exe /T >nul 2>&1
taskkill /F /IM node.exe /T >nul 2>&1
taskkill /F /IM nginx.exe /T >nul 2>&1

:: 2. Chiude qualsiasi processo utente su porta 80 e 8080
echo [2] Analisi porte 80 e 8080...
for %%P in (80 8080) do (
    for /f "tokens=5" %%A in ('netstat -ano ^| findstr :%%P ^| findstr LISTENING') do (
        set PID=%%A
        :: Sicurezza: chiude solo se NON è un processo di sistema (PID > 100)
        if !PID! GTR 100 (
            echo [+] Terminazione processo utente PID !PID! su porta %%P
            taskkill /F /PID !PID! /T >nul 2>&1
        )
    )
)

:: 3. Sblocca driver HTTP di sistema (senza danni all'OS)
echo [3] Reset driver HTTP...
net stop http /y >nul 2>&1
net start w3svc >nul 2>&1

echo.
echo [FINE] Porte pronte per l'uso.
pause
