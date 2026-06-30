@echo off
title FogAI — Low-Latency Intelligent IoT Architecture
color 0A
echo.
echo  ============================================================
echo   FogAI: Low-Latency Intelligent IoT Architecture
echo   Final Year Project Demo
echo  ============================================================
echo.
echo  Installing dependencies...
python -m pip install rich numpy colorama -q 2>nul
echo  Dependencies ready.
echo.
echo  Starting simulation...
echo.
python main.py --cycles 60
echo.
echo  Simulation complete. Check the 'reports\' and 'logs\' folders.
pause
