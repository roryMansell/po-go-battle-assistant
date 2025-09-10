@echo off
setlocal enabledelayedexpansion

rem --- config ---
set PORT=8000

rem go to this script's folder (your project root)
cd /d "%~dp0"

rem --- find python ---
set PYTHON=
where python >nul 2>nul && set "PYTHON=python"
if not defined PYTHON (
  where py >nul 2>nul && set "PYTHON=py -3"
)
if not defined PYTHON (
  echo [ERROR] Python 3 not found. Install Python or add it to PATH.
  echo         https://www.python.org/downloads/
  pause
  exit /b 1
)

rem --- start server in a new window that stays open ---
start "Pokédex Server" cmd /k "C:\Users\roryc\anaconda3\python.exe" -m http.server %PORT%

rem small delay so the server can bind
ping -n 2 127.0.0.1 >nul

rem open browser (use 127.0.0.1 to avoid some localhost quirks)
start "" "http://127.0.0.1:%PORT%/index.html"
exit /b 0
