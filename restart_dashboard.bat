@echo off
echo ========================================
echo RESTARTING TRAIN CONTROL DASHBOARD
echo ========================================

REM Kill any existing dashboard processes
echo.
echo 1. Stopping any running dashboard processes...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq train_control_platform*" >nul 2>&1
if errorlevel 1 (
    echo    No running processes found
) else (
    echo    Stopped running processes
)

REM Clear Python cache
echo.
echo 2. Clearing Python cache...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" >nul 2>&1
del /s /q *.pyc >nul 2>&1
echo    Python cache cleared

REM Wait a moment
timeout /t 1 /nobreak >nul

REM Start the dashboard
echo.
echo 3. Starting dashboard...
echo ========================================
python train_control_platform.py
