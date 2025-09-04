@echo off
REM AgriTesk System Startup Script (Windows Batch Version)
REM Automatically starts all components of the agricultural monitoring system

echo === AgriTesk System Launcher ===
echo Starting agricultural monitoring system...

REM Check if we're in the right directory
if not exist "main.py" (
    echo ERROR: Please run this script from the AgriTesk project directory
    echo Make sure main.py and receive.py are in the current directory
    pause
    exit /b 1
)

if not exist "receive.py" (
    echo ERROR: Please run this script from the AgriTesk project directory
    echo Make sure main.py and receive.py are in the current directory
    pause
    exit /b 1
)

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Install dependencies if requirements.txt exists
if exist "requirements.txt" (
    echo Installing/updating Python dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo WARNING: Some dependencies may not have installed properly
    ) else (
        echo Dependencies installed successfully
    )
) else (
    echo WARNING: requirements.txt not found, skipping dependency installation
)

REM Function to cleanup processes on exit
:cleanup
echo Shutting down AgriTesk system...
if defined WEBSOCKET_PID (
    taskkill /PID %WEBSOCKET_PID% /F >nul 2>&1
    echo Stopped WebSocket server
)
if defined RECEIVER_PID (
    taskkill /PID %RECEIVER_PID% /F >nul 2>&1
    echo Stopped data receiver
)
echo AgriTesk system stopped
exit /b 0

REM Start WebSocket server
echo Starting WebSocket server...
start /B python main.py
REM Get the process ID (this is a simplified approach)
timeout /t 3 /nobreak >nul

REM Check if server is running
curl -s http://127.0.0.1:8000/ >nul 2>&1
if errorlevel 1 (
    echo WARNING: WebSocket server may not have started properly
) else (
    echo WebSocket server started successfully
)

REM Start data receiver
echo Starting data receiver...
start /B python receive.py
timeout /t 2 /nobreak >nul
echo Data receiver started

REM Open web browser
echo Opening web application...
start http://127.0.0.1:8000/

echo === AgriTesk System Started Successfully ===
echo Web application: http://127.0.0.1:8000/
echo Press any key to stop the system

pause >nul
goto cleanup
