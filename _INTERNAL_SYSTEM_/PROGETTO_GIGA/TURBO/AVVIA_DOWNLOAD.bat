@echo off
setlocal
cd /d "%~dp0"
title ARIA2C - DOWNLOAD

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

aria2c.exe -i targets.txt -j 1 -x 4 -s 4 --file-allocation=none --summary-interval=1
pause
