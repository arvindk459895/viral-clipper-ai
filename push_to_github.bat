@echo off
setlocal enabledelayedexpansion

title Push to GitHub - ViralClipper AI Studio

echo ========================================================
echo     Uploading ViralClipper AI Studio to GitHub
echo ========================================================
echo.
echo Target Repository:
echo https://github.com/arvindk459895/viral-clipper-ai-studio.git
echo.
echo [*] Pushing branch main to GitHub...
echo (If a browser window or login prompt appears, please click "Sign in with your browser" to authorize.)
echo.

git push -u origin main

if %ERRORLEVEL% equ 0 (
    echo.
    echo ========================================================
    echo  [SUCCESS] Upload complete!
    echo ========================================================
    echo.
    echo Opening your GitHub repository in your browser...
    start https://github.com/arvindk459895/viral-clipper-ai-studio
) else (
    echo.
    echo ========================================================
    echo  [ERROR] Git push encountered an issue.
    echo ========================================================
    echo Please ensure you are logged into your GitHub account:
    echo arvindk459895@gmail.com
)

echo.
pause
