@echo off
setlocal enabledelayedexpansion

title ViralClipper AI Studio - 1-Click Launcher

echo ========================================================
echo         ViralClipper AI Studio - Automated Launcher
echo ========================================================
echo.

:: 1. Check Python installation
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not found in your system PATH!
    echo.
    echo Please install Python (version 3.10, 3.11, 3.12, or 3.13):
    echo https://www.python.org/downloads/
    echo IMPORTANT: Remember to check "Add python.exe to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo [OK] Python detected:
python --version
echo.

:: 2. Check or Create Virtual Environment
if not exist ".venv" (
    echo [*] Creating virtual environment (.venv)...
    python -m venv .venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
) else (
    echo [OK] Virtual environment found (.venv).
)

:: 3. Activate Virtual Environment
call .venv\Scripts\activate.bat

:: 4. Install / Update Dependencies
echo [*] Checking and installing required packages...
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Some dependencies had installation issues, retrying...
    pip install -r requirements.txt
)
echo [OK] All Python dependencies verified.
echo.

:: 5. Check FFmpeg
where ffmpeg >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [NOTICE] FFmpeg was not detected in your system PATH.
    echo Video rendering requires FFmpeg.
    echo.
    echo To install FFmpeg easily on Windows, run this command in PowerShell or Terminal:
    echo     winget install Gyan.FFmpeg
    echo.
    echo Or download and extract it manually from:
    echo     https://www.gyan.dev/ffmpeg/builds/
    echo and add the bin folder to your System PATH.
    echo.
    echo If you already installed it, restart your terminal or PC.
    echo.
) else (
    echo [OK] FFmpeg detected.
)
echo.

:: 6. Ensure required workspace directories exist
if not exist "outputs" mkdir outputs
if not exist "temp" mkdir temp
if not exist "credentials" mkdir credentials

:: 7. Launch Streamlit Web Studio
echo ========================================================
echo  Launching ViralClipper AI Studio on http://localhost:8501
echo ========================================================
echo.
streamlit run app.py

pause
