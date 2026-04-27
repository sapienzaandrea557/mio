@echo off
:: Verifica privilegi Admin
net session >nul 2>&1 || (echo [!] Esegui come AMMINISTRATORE & pause & exit)

echo [RESET SICURO PORTE 80 / 8080]

:: 1. Sblocca la porta 80 dai servizi Windows (PID 4) in modo gentile
:: net stop http ferma solo i servizi web di sistema, non danneggia l'OS
net stop http /y >nul 2>&1

:: 2. Chiude i programmi specifici per nome (I più comuni per queste porte)
taskkill /F /IM httpd.exe /T >nul 2>&1
taskkill /F /IM node.exe /T >nul 2>&1
taskkill /F /IM nginx.exe /T >nul 2>&1

:: 3. Chiude tutto il resto sulle porte 80/8080, filtrando i processi di sistema
for %%P in (80 8080) do (
    for /f "tokens=5" %%A in ('netstat -ano ^| findstr :%%P ^| findstr LISTENING') do (
        set PID=%%A
        :: Protezione: chiude solo se il PID è maggiore di 100 (evita kernel e driver critici)
        if !PID! GTR 100 (
            echo [+] Chiusura processo utente PID !PID! sulla porta %%P...
            taskkill /F /PID !PID! /T >nul 2>&1
        ) else (
            echo [-] Ignorato processo di sistema PID !PID! sulla porta %%P.
        )
    )
)

:: 4. Riavvio dei servizi (opzionale)
net start w3svc >nul 2>&1
echo [OPERAZIONE COMPLETATA] Le porte dovrebbero essere libere ora.
pause
