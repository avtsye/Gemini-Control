@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0server"
echo Gemini Control - Local Server
where node >nul 2>&1
if errorlevel 1 (
 echo Node.js is not installed. Install Node.js LTS from https://nodejs.org/
 goto done
)
if not exist .env (
 copy .env.example .env >nul
 echo Please open server\.env and replace MY_GEMINI_API_KEY with your own key.
 echo The key stays on your PC. Do not share it.
 notepad .env
)
findstr /C:"MY_GEMINI_API_KEY" .env >nul 2>&1
if not errorlevel 1 (
 echo The Gemini API key is not configured yet in server\.env.
 goto done
)
if not exist node_modules\tsx\dist (
 echo Installing dependencies (internet connection required)...
 call npm install --no-audit --no-fund
 if errorlevel 1 goto done
)
echo Open http://127.0.0.1:3000 in Chrome.
echo Ctrl+C to stop the server.
set APP_URL=http://127.0.0.1:3000
call npm run dev
:done
echo.
pause
