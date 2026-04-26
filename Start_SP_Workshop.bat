@echo off
setlocal
set "PROJECT_DIR=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Unblock-File -LiteralPath '%PROJECT_DIR%scripts\run_sp_workshop.ps1' -ErrorAction SilentlyContinue" >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -File "%PROJECT_DIR%scripts\run_sp_workshop.ps1"
if errorlevel 1 (
  echo.
  echo SP Workshop failed to start.
  pause
  exit /b 1
)
