@echo off
title FogAI — Web Dashboard
color 0A
echo.
echo  ============================================================
echo   FogAI: Low-Latency Intelligent IoT Architecture
echo   Web Dashboard
echo  ============================================================
echo.
echo  Installing dependencies...
python -m pip install rich numpy colorama flask -q 2>nul
echo  Starting server...
echo  Browser will open at http://localhost:5000
echo.
python web_app.py
pause
