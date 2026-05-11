@echo off
setlocal enabledelayedexpansion

set "ROOT=%~dp0"
set "DATABASE_URL=postgresql+psycopg://diploma:diploma@localhost:5433/diploma"
set "ML_URL=http://localhost:8000"
set "BACKEND_URL=http://localhost:8001"

cd /d "%ROOT%"

echo [Diploma] Starting project from:
echo %ROOT%
echo.

where docker >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Docker was not found in PATH.
    echo Install Docker Desktop and try again.
    pause
    exit /b 1
)

where uv >nul 2>nul
if errorlevel 1 (
    echo [ERROR] uv was not found in PATH.
    echo Install uv and run dependencies sync first.
    pause
    exit /b 1
)

if not exist "%ROOT%packages\ml\.env" (
    echo [ERROR] packages\ml\.env was not found.
    echo Create it first. Example:
    echo ML_DATASET_ROOT=F:\path\to\dataset
    echo BACKEND_URL=http://localhost:8001
    echo ML_DEVICE=cpu
    pause
    exit /b 1
)

echo [1/5] Starting PostgreSQL...
docker compose up -d postgres
if errorlevel 1 (
    echo [ERROR] Failed to start PostgreSQL.
    pause
    exit /b 1
)

echo [2/5] Waiting for PostgreSQL to become ready...
set "DB_READY="
for /l %%i in (1,1,30) do (
    docker compose exec -T postgres pg_isready -U diploma -d diploma >nul 2>nul
    if not errorlevel 1 (
        set "DB_READY=1"
        goto db_ready
    )
    timeout /t 2 /nobreak >nul
)

:db_ready
if not defined DB_READY (
    echo [ERROR] PostgreSQL did not become ready in time.
    docker compose ps
    pause
    exit /b 1
)

echo [3/5] Applying database migrations...
pushd "%ROOT%packages\backend"
set "DATABASE_URL=%DATABASE_URL%"
uv run alembic upgrade head
if errorlevel 1 (
    popd
    echo [ERROR] Failed to apply database migrations.
    pause
    exit /b 1
)
popd

echo [4/5] Starting ML and backend services in separate windows...
start "Diploma ML service" powershell -NoExit -ExecutionPolicy Bypass -Command "$env:BACKEND_URL='%BACKEND_URL%'; cd '%ROOT%packages\ml'; uv run uvicorn ml.main:app --host 127.0.0.1 --port 8000 --reload"

timeout /t 3 /nobreak >nul

start "Diploma Backend" powershell -NoExit -ExecutionPolicy Bypass -Command "$env:DATABASE_URL='%DATABASE_URL%'; $env:ML_URL='%ML_URL%'; cd '%ROOT%packages\backend'; uv run uvicorn backend.main:app --host 127.0.0.1 --port 8001 --reload"

echo [5/5] Starting frontend...
timeout /t 3 /nobreak >nul
start "Diploma Frontend" powershell -NoExit -ExecutionPolicy Bypass -Command "$env:BACKEND_URL='%BACKEND_URL%'; $env:ML_URL='%ML_URL%'; cd '%ROOT%packages\frontend'; uv run python -m frontend.main"

echo.
echo [OK] Launch commands were sent.
echo PostgreSQL:  localhost:5433
echo ML docs:     http://localhost:8000/docs
echo Backend docs:http://localhost:8001/docs
echo.
echo Close the service windows to stop ML/backend/frontend.
echo To stop PostgreSQL, run: docker compose down
echo.
pause
