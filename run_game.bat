@echo off
title Moba Manager - Verificador e Launcher
color 0F

echo ===================================================
echo      MOBA MANAGER - SISTEMA DE INICIALIZACAO
echo ===================================================
echo.

:: 1. Executando os testes unitários do backend
echo [1/5] Executando testes unitarios do backend...
set PYTHONPATH=.
.\venv\Scripts\python -m pytest
if %errorlevel% neq 0 (
    color 0C
    echo.
    echo ===================================================
    echo   [ERRO] A suite de testes unitarios falhou!
    echo   Por favor, copie o log acima e envie na conversa.
    echo ===================================================
    pause
    exit /b %errorlevel%
)
echo [OK] Todos os testes do backend passaram!
echo.

:: 2. Executando a verificação de build/tipos do Frontend
echo [2/5] Verificando compilação do Frontend (TypeScript)...
cd frontend
call npm run build
if %errorlevel% neq 0 (
    color 0C
    echo.
    echo ===================================================
    echo   [ERRO] O build/compilacao do Frontend falhou!
    echo   Por favor, copie o log acima e envie na conversa.
    echo ===================================================
    cd ..
    pause
    exit /b %errorlevel%
)
cd ..
echo [OK] Compilacao do frontend verificada com sucesso!
echo.

:: 3. Iniciando o Backend FastAPI
echo [3/5] Iniciando o servidor Backend (FastAPI)...
start "Moba Manager Backend" cmd /c "set PYTHONPATH=. && .\venv\Scripts\python -m uvicorn src.main:app --port 8000"

:: Aguarda 5 segundos para o servidor subir completamente
timeout /t 5 /nobreak >nul

:: 4. Executando a Semeadura do Banco (Seed)
echo [4/5] Alimentando o banco de dados (SQLite Seed)...
.\venv\Scripts\python seed_runner.py
if %errorlevel% neq 0 (
    color 0C
    echo.
    echo ===================================================
    echo   [ERRO] Falha ao rodar o Seed do banco de dados!
    echo   Verifique se o backend esta rodando na porta 8000.
    echo   Envie a saida de erro gerada para correção.
    echo ===================================================
    pause
    exit /b %errorlevel%
)
echo [OK] Banco de dados SQLite recriado e semeado com sucesso!
echo.

:: 5. Iniciando o Frontend Vite e Abrindo o Navegador
echo [5/5] Iniciando o servidor Frontend (Vite)...
cd frontend
start "Moba Manager Frontend" cmd /c "npm run dev"

:: Aguarda 2 segundos e abre o navegador no dashboard
timeout /t 2 /nobreak >nul
echo.
echo ===================================================
echo   [SUCESSO] Todo o ecossistema esta rodando!
echo   Abrindo o simulador no seu navegador...
echo ===================================================
start http://localhost:5173
echo.
