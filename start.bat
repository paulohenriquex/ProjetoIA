@echo off
echo Iniciando Backend (porta 8080)...
start "Backend" cmd /k "cd /d %~dp0backend && pip install -r requirements.txt && python run.py"
timeout /t 3 /nobreak > nul
echo Buildando Frontend...
cd /d %~dp0frontend
call npm run build
if errorlevel 1 exit /b 1
echo Iniciando Frontend (porta 6500)...
start "Frontend" cmd /k "cd /d %~dp0frontend && python serve.py"
echo.
echo Backend: http://localhost:8080
echo Frontend: http://localhost:6500
echo.
echo Configure GEMINI_API_KEY no arquivo .env antes de usar.
