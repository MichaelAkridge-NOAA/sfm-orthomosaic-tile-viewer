@echo off
REM Startup script for SfM Orthomosaic Viewer (Windows)

echo Starting SfM Orthomosaic Tile Viewer...
echo.

REM Check if config.yaml exists
if not exist "config.yaml" (
    echo Warning: config.yaml not found. Using default configuration.
)

REM Check if data directory exists
if not exist "data" (
    echo Creating data directory...
    mkdir data
)

echo Configuration:
echo    Data Directory: %cd%\data
echo.

REM Start server
echo Starting server...
echo    Open browser to: http://localhost:8000
echo.
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
