@echo off
echo ========================================
echo STARTING TRAIN CONTROL DASHBOARD
echo NO DEBUG MODE - FINAL VERSION
echo ========================================

REM Stop any running Python processes
echo Stopping any running Python processes...
taskkill /F /IM python.exe 2>nul

REM Clear cache
echo Clearing Python cache...
for /d /r . %%d in (__pycache__) do @if exist "%%d" (rd /s /q "%%d")
del /s /q *.pyc 2>nul

REM Set environment variable to disable debug mode
set FLASK_DEBUG=0

REM Wait a moment
timeout /t 2 /nobreak > nul

REM Start the dashboard
echo Starting dashboard (NO DEBUG MODE)...
python train_control_platform.py

pause
