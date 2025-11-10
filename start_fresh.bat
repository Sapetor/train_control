@echo off
echo ========================================
echo STARTING TRAIN CONTROL DASHBOARD
echo ========================================

REM Kill any existing dashboard
echo Stopping any running Python processes...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM python3.exe 2>nul

REM Delete ALL Python cache recursively
echo Clearing ALL Python cache...
for /d /r . %%d in (__pycache__) do @if exist "%%d" (echo Deleting %%d && rd /s /q "%%d")
del /s /q *.pyc 2>nul

REM Force refresh by touching the file
echo Updating file timestamp...
copy /b train_control_platform.py +,, >nul

REM Wait
timeout /t 2 /nobreak >nul

REM Start fresh
echo.
echo Starting dashboard...
echo ========================================
python train_control_platform.py
