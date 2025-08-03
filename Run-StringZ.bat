@echo off
echo ========================================
echo    StringZ - Translation QA Tool
echo ========================================
echo Starting portable version...

cd /d "%~dp0"
set PYTHONPATH=%~dp0;%~dp0Lib\site-packages
set PYTHONHOME=%~dp0python

echo Testing Python...
%~dp0python\python.exe --version
if %errorlevel% neq 0 (
    echo ERROR: Python test failed!
    pause
    exit /b 1
)

echo Changing to source directory...
cd stringZ-source
echo Current directory: %CD%

echo Checking for app.py...
if not exist "app.py" (
    echo ERROR: app.py not found!
    dir
    pause
    exit /b 1
)

echo Checking dependencies...
if not exist "%~dp0Lib\site-packages\flask" (
    echo Installing dependencies...
    %~dp0python\python.exe -m ensurepip --default-pip
    %~dp0python\python.exe -m pip install --target %~dp0Lib\site-packages -r requirements.txt
)

echo Starting StringZ...
%~dp0python\python.exe app.py
pause
