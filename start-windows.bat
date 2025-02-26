@echo off
echo Checking requirements...

REM Check if Docker is running
docker info > nul 2>&1
if errorlevel 1 (
    echo [31m❌ Docker is not running. Please start Docker Desktop first.[0m
    pause
    exit /b 1
)

echo [32m🚀 Starting Senior Design Project...[0m
docker-compose up --build
pause