@echo off
echo ========================================
echo    StringZ - Translation QA Tool
echo ========================================

cd /d "%~dp0"

REM Set Python paths correctly
set PYTHONPATH=%~dp0Lib\site-packages;%~dp0stringZ-source
set PYTHONHOME=%~dp0python

echo Testing Python and Flask...
%~dp0python\python.exe -c "import sys; sys.path.insert(0, r'%~dp0Lib\site-packages'); import flask; print('Flask version:', flask.__version__)"

if %errorlevel% neq 0 (
    echo ERROR: Flask not accessible!
    echo Installing dependencies...
    
    REM Try different pip installation methods
    if exist "Lib\site-packages\pip" (
        %~dp0python\python.exe -c "import sys; sys.path.insert(0, r'%~dp0Lib\site-packages'); import pip._internal; pip._internal.main(['install', '--target', r'%~dp0Lib\site-packages', '-r', r'%~dp0stringZ-source\requirements.txt'])"
    ) else (
        echo Please install dependencies manually
        pause
        exit /b 1
    )
)

echo Starting StringZ...
cd stringZ-source
%~dp0python\python.exe main.py
pause
