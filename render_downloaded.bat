@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Double-click setup.bat first.
  pause
  exit /b 1
)
echo Creating videos from downloaded audio. No Drive access is needed.
".venv\Scripts\python.exe" dasakam.py %*
set "result=%errorlevel%"
echo Finished with exit code %result%. See videos and logs\run.log.
pause
exit /b %result%
