@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Double-click setup.bat first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" dasakam.py --download shared %*
set "result=%errorlevel%"
echo Finished with exit code %result%. Videos are in the videos folder. See logs\run.log for details.
pause
exit /b %result%
