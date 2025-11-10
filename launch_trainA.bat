@echo off
REM Launch Train A on port 8050
echo ========================================
echo LAUNCHING TRAIN A
echo ========================================
echo Dashboard: http://127.0.0.1:8050
echo Press Ctrl+C to stop
echo ========================================
echo.

python launch_train.py trainA 8050
pause
