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
python setup.py --skip-env-check
if errorlevel 1 (
    echo.
    echo Trying python3...
    python3 setup.py --skip-env-check
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
echo ============================================================
echo REQUIRED: DBeaver Database Connection
echo ============================================================
echo.
echo IMPORTANT: You MUST connect to the database using DBeaver
echo    for the program to work properly!
echo.
echo Database location:
echo    data\app.db
echo.
echo DBeaver Connection Steps:
echo    1. Open DBeaver
echo    2. Click Database -^> New Database Connection
echo    3. Choose SQLite
echo    4. Click Next
echo    5. For Database file, click Browse
echo    6. Navigate to the 'data' folder in your project directory
echo    7. Select 'app.db'
echo    8. Click Finish
echo.
echo ============================================================
echo.
echo Next steps:
echo    1. Connect to database using DBeaver (REQUIRED - see above)
echo    2. Create a .env file with your API key:
echo       TOGETHER_AI_API_KEY=your_api_key_here
echo    3. Start the server with:
echo       python run_server.py
echo.
pause
