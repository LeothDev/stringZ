@echo off
echo ========================================
echo    StringZ - Translation QA Tool
echo ========================================
echo.
echo Checking Python installation...

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo Installing required packages...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo Starting StringZ...
echo Browser will open automatically at http://127.0.0.1:5000
echo.
echo Press Ctrl+C to stop the server
echo ========================================
python app.py
pause

