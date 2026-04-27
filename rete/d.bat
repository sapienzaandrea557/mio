@echo off
:: Richiede privilegi di amministratore
NET SESSION >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERRORE] Esegui questo script come AMMINISTRATORE.
    pause
    exit /B
)

echo [1/4] Arresto servizi http.sys (Porta 80/PID 4)...
:: Ferma il servizio principale che tiene impegnato il driver HTTP
net stop http /y

echo [2/4] Chiusura forzata Apache e Node.js...
:: Chiude i processi per nome, indipendentemente dalla porta
taskkill /F /IM httpd.exe /T >nul 2>&1
taskkill /F /IM node.exe /T >nul 2>&1

echo [3/4] Pulizia residui sulle porte 80 e 8080...
for %%P in (80 8080) do (
    for /f "tokens=5" %%A in ('netstat -ano ^| findstr :%%P ^| findstr LISTENING') do (
        taskkill /F /PID %%A /T >nul 2>&1
    )
)

echo [4/4] Riavvio servizi...
:: Riavvia http.sys (e i servizi dipendenti come W3SVC se necessario)
net start w3svc >nul 2>&1

:: RIAVVIO APACHE (Esempio per XAMPP - Modifica il percorso se diverso)
if exist "C:\xampp\apache\bin\httpd.exe" (
    start "" "C:\xampp\apache\bin\httpd.exe"
    echo [OK] Apache avviato.
)

:: RIAVVIO NODE.JS (Esempio - Specifica il tuo file principale)
:: cd /d "C:\tuo\progetto"
:: start "" node app.js

echo.
echo [FINE] Porte liberate e servizi riavviati.
pause
