@echo off
setlocal
cd /d "%~dp0"
title ViralClipper AI Studio - 1-Click Launcher

echo ========================================================
echo         ViralClipper AI Studio - Automated Launcher
echo ========================================================
echo.

REM 1. Detect Python Executable
set "PYTHON_EXE="
where python >nul 2>&1
if %ERRORLEVEL% equ 0 set "PYTHON_EXE=python"
if "%PYTHON_EXE%"=="" (
    where py >nul 2>&1
    if %ERRORLEVEL% equ 0 set "PYTHON_EXE=py"
)

if "%PYTHON_EXE%"=="" goto :PYTHON_NOT_FOUND

%PYTHON_EXE% --version >nul 2>&1
if %ERRORLEVEL% neq 0 goto :PYTHON_NOT_FOUND

echo [OK] Python detected:
%PYTHON_EXE% --version
echo.

REM 2. Create Virtual Environment if not present
if exist ".venv\Scripts\activate.bat" goto :VENV_EXISTS

echo [*] Creating virtual environment in .venv ...
%PYTHON_EXE% -m venv --system-site-packages .venv
if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Failed to create virtual environment!
    goto :ERROR_EXIT
)
echo [OK] Virtual environment created successfully.
goto :VENV_READY

:VENV_EXISTS
echo [OK] Virtual environment found: .venv

:VENV_READY
echo.

REM 3. Activate Virtual Environment
echo [*] Activating virtual environment...
call ".venv\Scripts\activate.bat"
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Could not activate virtual environment!
    goto :ERROR_EXIT
)
echo [OK] Virtual environment active.
echo.

REM 4. Install / Verify Dependencies
echo [*] Checking and verifying dependencies from requirements.txt ...
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt --quiet
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Retrying package installation with detailed logs...
    python -m pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Package installation failed!
        goto :ERROR_EXIT
    )
)
echo [OK] All dependencies verified.
echo.

REM 5. Check FFmpeg
where ffmpeg >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [NOTICE] FFmpeg was not detected in your system PATH.
    echo Video rendering requires FFmpeg.
    echo.
    echo To install FFmpeg on Windows, run this in PowerShell or Terminal:
    echo     winget install Gyan.FFmpeg
    echo.
    echo Or download and extract from:
    echo     https://www.gyan.dev/ffmpeg/builds/
    echo and add the bin folder to your System PATH.
    echo.
) else (
    echo [OK] FFmpeg detected.
)
echo.

REM 6. Ensure required workspace directories exist
if not exist "outputs" mkdir outputs
if not exist "temp" mkdir temp
if not exist "credentials" mkdir credentials

REM 7. Launch Streamlit Web Studio
echo ========================================================
echo  Launching ViralClipper AI Studio on http://localhost:8501
echo ========================================================
echo.
echo Tips:
echo  - Studio will automatically open in your default browser.
echo  - Press Ctrl+C in this window anytime to stop the studio.
echo.

python -m streamlit run app.py
goto :DONE

:PYTHON_NOT_FOUND
echo [ERROR] Python was not found in your system PATH!
echo.
echo Please install Python 3.10 to 3.13 from:
echo   https://www.python.org/downloads/
echo.
echo IMPORTANT: During installation, be sure to check the box:
echo   "Add python.exe to PATH"
echo.
goto :ERROR_EXIT

:ERROR_EXIT
echo.
echo ========================================================
echo  Launcher stopped due to an error.
echo ========================================================
echo.
pause
exit /b 1

:DONE
echo.
echo ========================================================
echo  ViralClipper AI Studio has been closed.
echo ========================================================
echo.
pause
