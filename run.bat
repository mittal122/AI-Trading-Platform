@echo off
REM ============================================================================
REM  AI Trading Platform - zero-to-running launcher for a fresh Windows PC
REM ----------------------------------------------------------------------------
REM  Just run:  run.bat   (double-click, or from a terminal)
REM
REM  EVERY dependency is checked and auto-installed only if missing:
REM    1. Python 3.12          (winget, else silent installer from python.org)
REM    2. Node.js              (winget, else portable zip - no admin needed)
REM    3. Kronos model repo    (downloaded from GitHub - no git needed)
REM    4. Python packages      (venv + requirements-windows.txt)
REM    5. Frontend packages    (npm install)
REM    6. .env                 (seeded from .env.example; KRONOS_PATH and
REM                             JWT_SECRET filled in automatically)
REM  Then starts backend (:8000) + frontend (:5173), each in its own console
REM  window (close a window to stop that service). Safe to re-run any time -
REM  installed things are detected and skipped.
REM
REM  Kronos AI model weights download from HuggingFace on first backend start,
REM  so the very first launch needs internet and a few minutes.
REM ============================================================================
setlocal
cd /d "%~dp0"

set "PY_VERSION=3.12.10"
set "NODE_VERSION=v22.14.0"
set "NODE_FALLBACK_DIR=%LocalAppData%\nodejs\node-%NODE_VERSION%-win-x64"

REM ============================================================
REM  [1/6] Python 3.12
REM ============================================================
call :find_python
if defined PYTHON goto :python_ok

echo [*] Python 3.12 not found - installing...
where winget >nul 2>&1
if not errorlevel 1 (
    winget install -e --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
) else (
    echo [*] winget unavailable - downloading installer from python.org...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12'; Invoke-WebRequest -UseBasicParsing 'https://www.python.org/ftp/python/%PY_VERSION%/python-%PY_VERSION%-amd64.exe' -OutFile \"$env:TEMP\python-setup.exe\""
    if not exist "%TEMP%\python-setup.exe" (
        echo [x] Python download failed - check your internet connection.
        pause & exit /b 1
    )
    start /wait "" "%TEMP%\python-setup.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1
    del "%TEMP%\python-setup.exe" >nul 2>&1
)
call :find_python
if not defined PYTHON (
    echo [x] Python installed but not found - close this window and run run.bat again
    echo     ^(a fresh window picks up the new PATH^).
    pause & exit /b 1
)
:python_ok
echo [+] Python: %PYTHON%

REM ============================================================
REM  [2/6] Node.js (npm)
REM ============================================================
call :find_npm
if defined NPM goto :node_ok

echo [*] Node.js not found - installing...
where winget >nul 2>&1
if not errorlevel 1 (
    winget install -e --id OpenJS.NodeJS.LTS --silent --accept-package-agreements --accept-source-agreements
) else (
    echo [*] winget unavailable - downloading portable Node.js ^(no admin needed^)...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12'; Invoke-WebRequest -UseBasicParsing 'https://nodejs.org/dist/%NODE_VERSION%/node-%NODE_VERSION%-win-x64.zip' -OutFile \"$env:TEMP\node.zip\"; Expand-Archive -Force \"$env:TEMP\node.zip\" \"$env:LocalAppData\nodejs\""
)
call :find_npm
if not defined NPM (
    echo [x] Node.js installed but not found - close this window and run run.bat again.
    pause & exit /b 1
)
:node_ok
echo [+] Node/npm: %NPM%

REM ============================================================
REM  [3/6] .env
REM ============================================================
if not exist .env (
    if exist .env.example (
        copy /y .env.example .env >nul
        echo [!] .env created from .env.example - add your NVIDIA_API_KEY later to enable AI features.
    ) else (
        echo [x] No .env and no .env.example to copy from.
        pause & exit /b 1
    )
)

REM ============================================================
REM  [4/6] Kronos model repo (needed for the backend to boot)
REM ============================================================
if exist "Kronos\model" goto :kronos_ok
REM Also fine if .env already points at a valid Kronos elsewhere
set "KP="
for /f "usebackq tokens=1,* delims==" %%a in (".env") do if /i "%%a"=="KRONOS_PATH" set "KP=%%~b"
if defined KP set "KP=%KP:"=%"
if defined KP if exist "%KP%\model" goto :kronos_ok

echo [*] Downloading Kronos model repo from GitHub ^(one time^)...
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12'; Invoke-WebRequest -UseBasicParsing 'https://api.github.com/repos/shiyu-coder/Kronos/zipball' -OutFile \"$env:TEMP\kronos.zip\"; if (Test-Path \"$env:TEMP\kronos_x\") { Remove-Item -Recurse -Force \"$env:TEMP\kronos_x\" }; Expand-Archive -Force \"$env:TEMP\kronos.zip\" \"$env:TEMP\kronos_x\"; $inner = Get-ChildItem \"$env:TEMP\kronos_x\" -Directory | Select-Object -First 1; Move-Item $inner.FullName (Join-Path (Get-Location) 'Kronos')"
if not exist "Kronos\model" (
    echo [x] Kronos download failed - check your internet connection and re-run.
    pause & exit /b 1
)
echo [+] Kronos repo downloaded to .\Kronos
:kronos_ok

REM ============================================================
REM  [5/6] Python venv + backend packages
REM ============================================================
if not exist .venv\Scripts\uvicorn.exe (
    echo [*] Creating Python venv and installing backend packages - one time, several minutes...
    if not exist .venv %PYTHON% -m venv .venv
    .venv\Scripts\python.exe -m pip install --upgrade pip
    .venv\Scripts\python.exe -m pip install -r requirements-windows.txt
    if errorlevel 1 (
        echo [x] Backend package install failed - see output above.
        pause & exit /b 1
    )
    echo [+] Backend packages installed.
)

REM Fill in KRONOS_PATH / JWT_SECRET in .env if they're missing (idempotent).
.venv\Scripts\python.exe scripts\bootstrap_env.py

REM ============================================================
REM  [6/6] Frontend packages
REM ============================================================
if not exist frontend\node_modules (
    echo [*] Installing frontend packages - one time...
    pushd frontend
    call %NPM% install --silent
    popd
    echo [+] Frontend packages installed.
)

REM ============================================================
REM  Start: free ports, launch both, health-check backend
REM ============================================================
echo [*] Stopping any previous instance...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 " ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173 " ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1

echo [*] Starting backend on :8000 ...
start "AI Trading - Backend (close to stop)" /d "%~dp0" cmd /k "set PYTHONPATH=. && .venv\Scripts\uvicorn.exe backend.app.main:app --port 8000"

echo [*] Starting frontend on :5173 ...
start "AI Trading - Frontend (close to stop)" /d "%~dp0frontend" cmd /k "npm run dev"

echo|set /p="Waiting for backend (first start downloads AI model weights - can take minutes)"
set "UP="
for /l %%i in (1,1,180) do (
    if not defined UP (
        powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 http://localhost:8000/ | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1 && set UP=1
        if not defined UP (
            echo|set /p="."
            timeout /t 2 /nobreak >nul
        )
    )
)
echo.
if defined UP (
    echo [+] Backend:  http://localhost:8000
) else (
    echo [!] Backend not responding yet - check the Backend window for errors.
)
echo [+] Frontend: http://localhost:5173
echo.
echo   Both run in their own windows - close a window to stop that service.
echo.
pause
exit /b 0

REM ============================================================
REM  Helpers
REM ============================================================
:find_python
set "PYTHON="
py -3.12 -c "pass" >nul 2>&1 && set "PYTHON=py -3.12" && goto :eof
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PYTHON="%LocalAppData%\Programs\Python\Python312\python.exe"" && goto :eof
if exist "%ProgramFiles%\Python312\python.exe" set "PYTHON="%ProgramFiles%\Python312\python.exe"" && goto :eof
python -c "import sys; sys.exit(0 if sys.version_info[:2] >= (3, 10) else 1)" >nul 2>&1 && set "PYTHON=python" && goto :eof
goto :eof

:find_npm
set "NPM="
where npm >nul 2>&1 && set "NPM=npm" && goto :eof
if exist "%ProgramFiles%\nodejs\npm.cmd" (
    set "PATH=%ProgramFiles%\nodejs;%PATH%"
    set "NPM=npm"
    goto :eof
)
if exist "%NODE_FALLBACK_DIR%\npm.cmd" (
    set "PATH=%NODE_FALLBACK_DIR%;%PATH%"
    set "NPM=npm"
    goto :eof
)
goto :eof
