@echo off
title Mission Control - Swarm Robotics
cd /d "%~dp0"

echo ============================================================
echo   MISSION CONTROL - Swarm Robotics (dashboard NiceGUI)
echo ============================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERRO] Ambiente virtual nao encontrado em .venv\
    echo        Cria-o com:  python -m venv .venv
    echo        E instala:   .venv\Scripts\python.exe -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8080" ^| findstr LISTENING') do (
echo [INFO] A fechar instancia anterior na porta 8080 ^(PID %%a^)...
    taskkill /F /PID %%a >nul 2>&1
)

echo [INFO] A iniciar o servidor em http://localhost:8080
echo [INFO] O browser abre automaticamente. Fecha esta janela para parar o servidor.bre
echo.

".venv\Scripts\python.exe" -m dashboard.app

echo.
echo [INFO] O servidor terminou.
pause