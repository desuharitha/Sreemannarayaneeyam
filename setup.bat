@echo off
setlocal
cd /d "%~dp0"
echo Setting up free local tools in this folder. No system settings are changed.
python --version >nul 2>&1
if errorlevel 1 (
  echo Install Python 3.11 or newer from https://www.python.org/downloads/windows/
  echo Select Add Python to PATH during installation, then run this file again.
  pause
  exit /b 1
)
python -m venv .venv
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install --index-url https://pypi.org/simple -r requirements.txt
if errorlevel 1 goto failed
echo Setup complete. Double-click test_one.bat to create Dasakam 1 first.
pause
exit /b 0
:failed
echo Setup failed. Check the message above and your internet connection.
pause
exit /b 1
