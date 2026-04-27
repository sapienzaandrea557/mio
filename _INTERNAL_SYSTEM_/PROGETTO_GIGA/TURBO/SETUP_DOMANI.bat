@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title DOMANI - SETUP TURBO

set "DST=%USERPROFILE%\Desktop\domani\TURBO"
set "TMP=%TEMP%\domani_aria2"

echo.
echo Creo la cartella: "%DST%"
echo.

if not exist "%DST%" mkdir "%DST%" >nul 2>&1
if errorlevel 1 (
  echo Errore: non riesco a creare "%DST%".
  pause
  exit /b 1
)

echo Copio i file TURBO...
xcopy "%~dp0*" "%DST%\" /E /I /Y >nul
if errorlevel 1 (
  echo Errore: copia file non riuscita.
  pause
  exit /b 1
)

if exist "%DST%\aria2c.exe" goto aria_ok

where aria2c.exe >nul 2>&1
if errorlevel 1 goto aria_download

for /f "delims=" %%F in ('where aria2c.exe 2^>nul') do (
  copy /Y "%%F" "%DST%\aria2c.exe" >nul
  goto aria_ok
)

:aria_download
echo.
echo aria2c.exe non trovato. Provo a scaricare aria2 (portable)...
echo.

if exist "%TMP%" rmdir /S /Q "%TMP%" >nul 2>&1
mkdir "%TMP%" >nul 2>&1

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;" ^
  "$h=@{'User-Agent'='domani-setup'};" ^
  "$rel=Invoke-RestMethod -Headers $h -Uri 'https://api.github.com/repos/aria2/aria2/releases/latest';" ^
  "$asset=$rel.assets | Where-Object { $_.name -match 'win-64bit' -and $_.name -match '\.zip$' } | Select-Object -First 1;" ^
  "if(-not $asset){ $asset=$rel.assets | Where-Object { $_.name -match '\.zip$' } | Select-Object -First 1 }" ^
  "if(-not $asset){ throw 'Nessun asset .zip trovato su GitHub.' }" ^
  "$zip=Join-Path $env:TEMP 'aria2_portable.zip';" ^
  "Invoke-WebRequest -Headers $h -Uri $asset.browser_download_url -OutFile $zip;" ^
  "$out=Join-Path $env:TEMP 'domani_aria2';" ^
  "if(Test-Path $out){ Remove-Item -Recurse -Force $out }" ^
  "New-Item -ItemType Directory -Force -Path $out | Out-Null;" ^
  "Expand-Archive -Force -Path $zip -DestinationPath $out;" ^
  "$exe=Get-ChildItem -Path $out -Recurse -Filter aria2c.exe | Select-Object -First 1;" ^
  "if(-not $exe){ throw 'aria2c.exe non trovato nello zip.' }" ^
  "Copy-Item -Force $exe.FullName '%DST%\aria2c.exe';"

if errorlevel 1 (
  echo.
  echo Non sono riuscito a scaricare aria2 automaticamente.
  echo Puoi installarlo con:
  echo   winget install aria2.aria2
  echo e poi rilanciare questo setup.
  echo.
  pause
  exit /b 1
)

:aria_ok
echo.
echo OK: setup completato in "%USERPROFILE%\Desktop\domani\TURBO"
echo.
echo Vuoi avviare un download di test adesso?
choice /c SN /m "S/N"
if errorlevel 2 goto end

if not exist "%DST%\targets.txt" (
  echo File targets.txt mancante in "%DST%".
  pause
  exit /b 1
)

pushd "%DST%"
aria2c.exe -i targets.txt -j 1 -x 4 -s 4 --file-allocation=none --summary-interval=1
popd
pause

:end
start "" "%USERPROFILE%\Desktop\domani\TURBO"
