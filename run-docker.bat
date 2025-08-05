
@echo off
echo ========================================
echo    StringZ - Docker Version
echo ========================================
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not installed or not in PATH
    echo Please install Docker Desktop from https://docker.com
    pause
    exit /b 1
)

echo Building StringZ Docker image...
docker build -t stringz .

if %errorlevel% neq 0 (
    echo ERROR: Failed to build Docker image
    pause
    exit /b 1
)

echo.
echo Starting StringZ container...
echo Opening browser at http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo ========================================

REM Create uploads directory if it doesn't exist
if not exist "uploads" mkdir uploads

REM Start container and open browser
timeout /t 2 /nobreak >nul
start http://localhost:5000
docker run --rm -p 5000:5000 -v "%cd%\uploads:/app/uploads" stringz

pause
