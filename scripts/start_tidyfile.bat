@echo off
chcp 65001 >nul
title TidyFile File Organizer
echo ================================================
echo     TidyFile File Organizer Starting...
echo ================================================

cd /d "%~dp0"

REM Check Python environment
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python environment not found, please ensure Python is installed and added to PATH
    pause
    exit /b 1
)

REM Check main program file
if not exist "main.py" (
    echo [ERROR] Main program file main.py not found
    pause
    exit /b 1
)

REM Start program
echo [INFO] Starting TidyFile File Organizer...
python main.py

if errorlevel 1 (
    echo [ERROR] Program exited abnormally
    pause
    exit /b 1
)

echo [INFO] Program exited normally
pause 