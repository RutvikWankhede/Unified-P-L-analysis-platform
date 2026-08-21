@echo off
title Stopping Unified P^&L Platform

echo.
echo  [*] Stopping all servers...
echo.

REM Kill processes on ports 8000 and 3000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
    echo  [x] Stopped backend ^(PID: %%a^)
)

for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000 " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
    echo  [x] Stopped frontend ^(PID: %%a^)
)

REM Also kill any orphaned python servers
taskkill /F /IM python.exe >nul 2>&1

echo.
echo  [✓] All servers stopped.
echo.
pause
