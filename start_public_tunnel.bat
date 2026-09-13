@echo off
title ViralClipper AI Studio - Live Public Tunnel
echo ==========================================================
echo       ViralClipper AI Studio - Cloudflare Live Tunnel
echo ==========================================================
echo.
echo [1/2] Starting Streamlit Studio on localhost:8501...
start /b python -m streamlit run app.py --server.port 8501 --server.headless true

timeout /t 3 /nobreak >nul

echo [2/2] Starting secure Cloudflare public tunnel...
echo.
echo Share the https://*.trycloudflare.com link with anyone in the world!
echo Login ID:  7372817332
echo Password:  8210501077amit
echo.
echo ==========================================================
.\cloudflared.exe tunnel --url http://localhost:8501
pause
