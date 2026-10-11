@echo off
chcp 65001 >nul
title Gemini Control - Windows Bridge
cd /d "%~dp0"
echo ==============================================
echo      Gemini Control - Bridge Setup
echo ==============================================
echo.
echo 1. Open chrome://extensions
echo 2. Enable developer mode
echo 3. Copy the ID below Gemini Control
echo.
set /p EXTENSION_ID=Paste extension ID (32 letters): 
if "%EXTENSION_ID%"=="" (
 echo No extension ID entered.
 goto end
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-Bridge.ps1" -ExtensionId "%EXTENSION_ID%"
if errorlevel 1 (
 echo.
 echo Setup did not complete. Read the error above.
 goto end
)
echo.
echo Setup completed. Reload the Chrome extension.
:end
echo.
pause
