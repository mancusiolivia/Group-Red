@echo off
REM Windows batch script for easy setup
REM This script installs dependencies and runs the setup

echo ============================================================
echo Essay Testing System - Windows Setup
echo ============================================================
echo.

echo Step 1: Installing Python dependencies...
python -m pip install -r server/requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR: Failed to install dependencies. Trying python3...
    python3 -m pip install -r server/requirements.txt
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to install dependencies. Please install manually.
        pause
        exit /b 1
    )
)

echo.
echo Step 2: Running database setup...
python setup.py
if errorlevel 1 (
    echo.
    echo Trying python3...
    python3 setup.py
    if errorlevel 1 (
        echo.
        echo ERROR: Setup failed. Please check the errors above.
        pause
        exit /b 1
    )
)

echo.
echo ============================================================
echo Setup Complete!
echo ============================================================
echo.
echo Next: Create a .env file with your API key:
echo    TOGETHER_AI_API_KEY=your_api_key_here
echo.
echo Then start the server with:
echo    python run_server.py
echo.
pause
