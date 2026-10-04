@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run setup.bat first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" dasakam.py --preview 100
if not errorlevel 1 start "" "videos\preview_100.png"
pause
