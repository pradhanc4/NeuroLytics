@echo off
setlocal
cd /d "%~dp0"
echo ============================================
echo        NeuroLytics - Starting Project
echo ============================================
echo.
echo Project: %CD%
echo Python : venv\Scripts\python.exe
echo URL    : http://127.0.0.1:5000/
echo.
echo The virtual environment is used automatically.
echo Keep this window open while NeuroLytics is running.
echo.
call venv\Scripts\python.exe scripts\start_neurolytics.py
endlocal
