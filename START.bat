@echo off
chcp 65001 >nul
title ShadowRotate

cd /d "%~dp0"

echo ============================================================
echo   ShadowRotate - Starting
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found
    echo Install from python.org
    pause
    exit /b 1
)

echo [OK] Python found
echo.
echo [*] Starting server...
start "ShadowRotate Server" cmd /k python server.py

timeout /t 5 >nul

echo [*] Starting bot...
start "ShadowRotate Bot" cmd /k python bot.py

echo.
echo Both are running in separate windows.
echo Close this window anytime.
timeout /t 3 >nul