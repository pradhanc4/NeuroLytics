@echo off
setlocal
echo Stopping NeuroLytics...
taskkill /FI "WINDOWTITLE eq NeuroLytics*" /T /F >nul 2>&1
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":5000" ^| findstr "LISTENING"') do (
    taskkill /PID %%P /F >nul 2>&1
)
echo NeuroLytics stop command completed.
endlocal
