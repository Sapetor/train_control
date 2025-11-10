@echo off
REM Launch all trains on separate ports
REM Each train gets its own dashboard instance

echo ========================================
echo MULTI-TRAIN LAUNCHER
echo ========================================
echo.
echo Starting trains on separate ports:
echo   Train A: http://127.0.0.1:8050
echo   Train B: http://127.0.0.1:8051
echo   Train C: http://127.0.0.1:8052
echo.
echo Press Ctrl+C to stop all trains
echo ========================================
echo.

REM Launch Train A on port 8050
start "Train A - Port 8050" cmd /k python launch_train.py trainA 8050

REM Wait 2 seconds before launching next
timeout /t 2 /nobreak >nul

REM Launch Train B on port 8051
start "Train B - Port 8051" cmd /k python launch_train.py trainB 8051

REM Wait 2 seconds before launching next
timeout /t 2 /nobreak >nul

REM Launch Train C on port 8052
start "Train C - Port 8052" cmd /k python launch_train.py trainC 8052

echo.
echo All trains launched!
echo.
echo Access dashboards at:
echo   Train A: http://127.0.0.1:8050
echo   Train B: http://127.0.0.1:8051
echo   Train C: http://127.0.0.1:8052
echo.
echo Close the train windows to stop them.
echo.
pause
