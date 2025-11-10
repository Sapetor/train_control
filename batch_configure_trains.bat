@echo off
REM ============================================================================
REM Batch Configuration Script for Multiple ESP32 Trains
REM ============================================================================
REM
REM This script helps configure multiple ESP32s quickly.
REM Edit the train configurations below, then run this script.
REM
REM Usage:
REM   1. Connect first ESP32 to USB (note COM port)
REM   2. Edit TRAIN1_ID, TRAIN1_PORT, TRAIN1_COM below
REM   3. Run this script
REM   4. Follow on-screen prompts
REM   5. Repeat for additional trains
REM
REM ============================================================================

echo.
echo ========================================
echo ESP32 Train Batch Configuration
echo ========================================
echo.

REM ----------------------------------------------------------------------------
REM CONFIGURATION SECTION - Edit these values
REM ----------------------------------------------------------------------------

REM Train 1 Configuration
set TRAIN1_ID=trainA
set TRAIN1_PORT=5555
set TRAIN1_COM=COM3

REM Train 2 Configuration
set TRAIN2_ID=trainB
set TRAIN2_PORT=5556
set TRAIN2_COM=COM4

REM Train 3 Configuration
set TRAIN3_ID=trainC
set TRAIN3_PORT=5557
set TRAIN3_COM=COM5

REM ----------------------------------------------------------------------------
REM Check if Python is installed
REM ----------------------------------------------------------------------------
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.x and try again
    pause
    exit /b 1
)

REM Check if configure_train.py exists
if not exist configure_train.py (
    echo ERROR: configure_train.py not found in current directory
    echo Please run this script from the project root directory
    pause
    exit /b 1
)

REM ----------------------------------------------------------------------------
REM Main Menu
REM ----------------------------------------------------------------------------
:MENU
echo.
echo ========================================
echo Select Configuration Option
echo ========================================
echo.
echo 1. Configure Train 1 (%TRAIN1_ID% on %TRAIN1_COM%)
echo 2. Configure Train 2 (%TRAIN2_ID% on %TRAIN2_COM%)
echo 3. Configure Train 3 (%TRAIN3_ID% on %TRAIN3_COM%)
echo 4. Configure All Trains (Sequential)
echo 5. Check Configuration of Connected Train
echo 6. Reset Train Configuration
echo 7. Exit
echo.

set /p choice="Enter choice (1-7): "

if "%choice%"=="1" goto TRAIN1
if "%choice%"=="2" goto TRAIN2
if "%choice%"=="3" goto TRAIN3
if "%choice%"=="4" goto ALL_TRAINS
if "%choice%"=="5" goto CHECK_CONFIG
if "%choice%"=="6" goto RESET_CONFIG
if "%choice%"=="7" goto END
echo Invalid choice. Please try again.
goto MENU

REM ----------------------------------------------------------------------------
REM Configure Train 1
REM ----------------------------------------------------------------------------
:TRAIN1
echo.
echo ========================================
echo Configuring Train 1
echo ========================================
echo Train ID: %TRAIN1_ID%
echo UDP Port: %TRAIN1_PORT%
echo COM Port: %TRAIN1_COM%
echo ========================================
echo.
echo INSTRUCTIONS:
echo 1. Connect ESP32 #1 to %TRAIN1_COM%
echo 2. Press any key to continue...
pause >nul

echo.
echo Sending configuration...
python configure_train.py --train %TRAIN1_ID% --udp %TRAIN1_PORT% --port %TRAIN1_COM%

if %errorlevel% equ 0 (
    echo.
    echo SUCCESS: Train 1 configured successfully!
    echo Train ID: %TRAIN1_ID%
    echo UDP Port: %TRAIN1_PORT%
    echo.
) else (
    echo.
    echo ERROR: Configuration failed. Check the error messages above.
    echo.
)

echo Press any key to return to menu...
pause >nul
goto MENU

REM ----------------------------------------------------------------------------
REM Configure Train 2
REM ----------------------------------------------------------------------------
:TRAIN2
echo.
echo ========================================
echo Configuring Train 2
echo ========================================
echo Train ID: %TRAIN2_ID%
echo UDP Port: %TRAIN2_PORT%
echo COM Port: %TRAIN2_COM%
echo ========================================
echo.
echo INSTRUCTIONS:
echo 1. Connect ESP32 #2 to %TRAIN2_COM%
echo 2. Press any key to continue...
pause >nul

echo.
echo Sending configuration...
python configure_train.py --train %TRAIN2_ID% --udp %TRAIN2_PORT% --port %TRAIN2_COM%

if %errorlevel% equ 0 (
    echo.
    echo SUCCESS: Train 2 configured successfully!
    echo Train ID: %TRAIN2_ID%
    echo UDP Port: %TRAIN2_PORT%
    echo.
) else (
    echo.
    echo ERROR: Configuration failed. Check the error messages above.
    echo.
)

echo Press any key to return to menu...
pause >nul
goto MENU

REM ----------------------------------------------------------------------------
REM Configure Train 3
REM ----------------------------------------------------------------------------
:TRAIN3
echo.
echo ========================================
echo Configuring Train 3
echo ========================================
echo Train ID: %TRAIN3_ID%
echo UDP Port: %TRAIN3_PORT%
echo COM Port: %TRAIN3_COM%
echo ========================================
echo.
echo INSTRUCTIONS:
echo 1. Connect ESP32 #3 to %TRAIN3_COM%
echo 2. Press any key to continue...
pause >nul

echo.
echo Sending configuration...
python configure_train.py --train %TRAIN3_ID% --udp %TRAIN3_PORT% --port %TRAIN3_COM%

if %errorlevel% equ 0 (
    echo.
    echo SUCCESS: Train 3 configured successfully!
    echo Train ID: %TRAIN3_ID%
    echo UDP Port: %TRAIN3_PORT%
    echo.
) else (
    echo.
    echo ERROR: Configuration failed. Check the error messages above.
    echo.
)

echo Press any key to return to menu...
pause >nul
goto MENU

REM ----------------------------------------------------------------------------
REM Configure All Trains Sequentially
REM ----------------------------------------------------------------------------
:ALL_TRAINS
echo.
echo ========================================
echo Sequential Configuration of All Trains
echo ========================================
echo.
echo This will configure 3 trains one after another.
echo You will need to swap USB connections between trains.
echo.
echo Press any key to start, or Ctrl+C to cancel...
pause >nul

REM Train 1
echo.
echo ========================================
echo [1/3] Configuring Train 1
echo ========================================
echo Connect ESP32 #1 to %TRAIN1_COM%
echo Press any key when ready...
pause >nul
echo Configuring %TRAIN1_ID%...
python configure_train.py --train %TRAIN1_ID% --udp %TRAIN1_PORT% --port %TRAIN1_COM%
echo Waiting 15 seconds for ESP32 to reboot...
timeout /t 15 /nobreak >nul

REM Train 2
echo.
echo ========================================
echo [2/3] Configuring Train 2
echo ========================================
echo Connect ESP32 #2 to %TRAIN2_COM%
echo Press any key when ready...
pause >nul
echo Configuring %TRAIN2_ID%...
python configure_train.py --train %TRAIN2_ID% --udp %TRAIN2_PORT% --port %TRAIN2_COM%
echo Waiting 15 seconds for ESP32 to reboot...
timeout /t 15 /nobreak >nul

REM Train 3
echo.
echo ========================================
echo [3/3] Configuring Train 3
echo ========================================
echo Connect ESP32 #3 to %TRAIN3_COM%
echo Press any key when ready...
pause >nul
echo Configuring %TRAIN3_ID%...
python configure_train.py --train %TRAIN3_ID% --udp %TRAIN3_PORT% --port %TRAIN3_COM%
echo Waiting 15 seconds for ESP32 to reboot...
timeout /t 15 /nobreak >nul

echo.
echo ========================================
echo All Trains Configured!
echo ========================================
echo Train 1: %TRAIN1_ID% on port %TRAIN1_PORT%
echo Train 2: %TRAIN2_ID% on port %TRAIN2_PORT%
echo Train 3: %TRAIN3_ID% on port %TRAIN3_PORT%
echo ========================================
echo.
echo Press any key to return to menu...
pause >nul
goto MENU

REM ----------------------------------------------------------------------------
REM Check Configuration
REM ----------------------------------------------------------------------------
:CHECK_CONFIG
echo.
echo ========================================
echo Check Train Configuration
echo ========================================
echo.
set /p check_com="Enter COM port to check (e.g., COM3): "

echo.
echo Checking configuration on %check_com%...
python configure_train.py --get-config --port %check_com%

echo.
echo Press any key to return to menu...
pause >nul
goto MENU

REM ----------------------------------------------------------------------------
REM Reset Configuration
REM ----------------------------------------------------------------------------
:RESET_CONFIG
echo.
echo ========================================
echo Reset Train Configuration
echo ========================================
echo.
echo WARNING: This will clear the train configuration!
echo The ESP32 will return to configuration mode.
echo.
set /p reset_com="Enter COM port to reset (e.g., COM3): "

echo.
echo Are you sure you want to reset configuration?
set /p confirm="Type YES to confirm: "

if /i "%confirm%"=="YES" (
    echo.
    echo Resetting configuration on %reset_com%...
    python configure_train.py --reset --port %reset_com%
) else (
    echo Reset cancelled.
)

echo.
echo Press any key to return to menu...
pause >nul
goto MENU

REM ----------------------------------------------------------------------------
REM End
REM ----------------------------------------------------------------------------
:END
echo.
echo Exiting...
echo.
exit /b 0
