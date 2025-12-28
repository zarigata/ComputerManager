@echo off
echo Starting Computer Manager from source...
cd /d "%~dp0"

:: Check if venv exists
if not exist "venv" (
    echo Virtual environment not found. Creating...
    python -m venv venv
    call venv\Scripts\activate
    echo Installing dependencies...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate
)

:: Set PYTHONPATH to current directory
set PYTHONPATH=%CD%

:: Run the application
python src\main.py

if %ERRORLEVEL% NEQ 0 (
    echo Application exited with error code %ERRORLEVEL%
    pause
)
