@echo off
setlocal
cd /d "%~dp0"
title ARIA2C - AVVIO INTERATTIVO

echo.
echo Questo script avvia un download "normale" con aria2c.
echo Usalo solo per download legittimi e con permesso (rispetta ISP e policy dei server).
echo.

if not exist "aria2c.exe" (
  echo Metti aria2c.exe in questa cartella: "%~dp0"
  pause
  exit /b 1
)

if not exist "targets.txt" (
  echo File targets.txt mancante in: "%~dp0"
  pause
  exit /b 1
)

choice /c SN /m "Vuoi avviare il download adesso?"
if errorlevel 2 (
  echo Annullato.
  exit /b 0
)

aria2c.exe -i targets.txt -j 1 -x 4 -s 4 --file-allocation=none --summary-interval=1
pause
