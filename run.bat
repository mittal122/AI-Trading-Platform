@echo off
REM ============================================================================
REM  AI Trading Platform - one-click launcher (Windows)
REM ----------------------------------------------------------------------------
REM  Just run:  run.bat   (double-click, or from a terminal)
REM
REM  On first run it bootstraps everything automatically:
REM    - creates the Python venv (.venv) and installs backend requirements
REM    - seeds .env from .env.example if you don't have one yet
REM    - installs frontend dependencies (npm install)
REM  On every run it starts backend (:8000) + frontend (:5173), each in its
REM  own console window (close a window to stop that service).
REM
REM  NOTE: the backend needs KRONOS_PATH in .env pointing at a local clone of
REM  the Kronos model repo (with model.py) - the app will not boot without it.
REM ============================================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM ---- pick a python ---------------------------------------------------------
set "PYTHON="
where py >nul 2>&1 && (py -3.12 -c "pass" >nul 2>&1 && set "PYTHON=py -3.12")
if not defined PYTHON (
    where python >nul 2>&1 && set "PYTHON=python"
)
if not defined PYTHON (
    echo [x] Python not found. Install Python 3.12 from python.org, then re-run run.bat
    pause & exit /b 1
)

REM ---- 1. .env ---------------------------------------------------------------
if not exist .env (
    if exist .env.example (
        copy /y .env.example .env >nul
        echo [!] .env created from .env.example - add your API keys ^(NVIDIA/Binance^) and set KRONOS_PATH.
    ) else (
        echo [x] No .env and no .env.example to copy from.
        pause & exit /b 1
    )
)

REM ---- 2. python venv + backend deps -----------------------------------------
if not exist .venv\Scripts\uvicorn.exe (
    echo [*] Setting up Python venv - first run, one time...
    if not exist .venv %PYTHON% -m venv .venv
    .venv\Scripts\python.exe -m pip install --quiet --upgrade pip
    .venv\Scripts\python.exe -m pip install --quiet -r requirements.txt
    if errorlevel 1 (
        echo [x] Backend dependency install failed - see output above.
        pause & exit /b 1
    )
    echo [+] Backend dependencies installed.
)

REM ---- 3. frontend deps ------------------------------------------------------
if not exist frontend\node_modules (
    where npm >nul 2>&1
    if errorlevel 1 (
        echo [x] npm not found. Install Node.js from nodejs.org, then re-run run.bat
        pause & exit /b 1
    )
    echo [*] Installing frontend dependencies - first run, one time...
    pushd frontend
    call npm install --silent
    popd
    echo [+] Frontend dependencies installed.
)

if not exist logs mkdir logs

REM ---- 4. stop any previous instance (whatever holds ports 8000 / 5173) ------
echo [*] Stopping any previous instance...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 " ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173 " ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1

REM ---- 5. start backend + frontend, each in its own window --------------------
echo [*] Starting backend on :8000 ...
start "AI Trading - Backend (close to stop)" /d "%~dp0" cmd /k "set PYTHONPATH=. && .venv\Scripts\uvicorn.exe backend.app.main:app --port 8000"

echo [*] Starting frontend on :5173 ...
start "AI Trading - Frontend (close to stop)" /d "%~dp0frontend" cmd /k "npm run dev"

REM ---- 6. wait for backend health (Kronos model load can take a while) --------
echo|set /p="Waiting for backend"
set "UP="
for /l %%i in (1,1,60) do (
    if not defined UP (
        curl -s -m 1 http://localhost:8000/ >nul 2>&1 && set UP=1
        if not defined UP (
            echo|set /p="."
            timeout /t 1 /nobreak >nul
        )
    )
)
echo.
if defined UP (
    echo [+] Backend:  http://localhost:8000
) else (
    echo [!] Backend not responding yet - check the Backend window for errors
    echo     ^(missing KRONOS_PATH in .env is the usual cause^).
)
echo [+] Frontend: http://localhost:5173
echo.
echo   Both run in their own windows - close a window to stop that service.
echo.
pause
