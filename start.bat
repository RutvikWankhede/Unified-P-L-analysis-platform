@echo off
title Unified P^&L Intelligence Platform
echo.
echo  =========================================================
echo   Unified P^&L Intelligence - Starting All Services...
echo  =========================================================
echo.

REM Find Python
set PYTHON=python
if exist "unified-pl-system\venv\Scripts\python.exe" (
    set PYTHON=unified-pl-system\venv\Scripts\python.exe
)

echo  [*] Using Python: %PYTHON%
echo  [*] Starting platform...
echo.

%PYTHON% run.py

pause
