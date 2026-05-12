@echo off
REM Script para gerar o executável UltraDanfeXML
echo ============================================================
echo   BUILD ULTRADANFE XML - EXECUTAVEL STANDALONE
echo ============================================================
echo.

REM Ativar ambiente virtual se existir
if exist .venv\Scripts\activate.bat (
    echo Ativando ambiente virtual...
    call .venv\Scripts\activate.bat
) else (
    echo AVISO: Ambiente virtual nao encontrado
    echo Certifique-se de ter todas as dependencias instaladas
    pause
)

REM Executar script de build
echo.
echo Executando script de build...
if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe build_exe.py
) else (
    echo ERRO: Python da .venv nao encontrado.
    echo Rode o inicializar.ps1 para criar o ambiente e instalar dependencias.
    exit /b 1
)

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================================
    echo   BUILD CONCLUIDO COM SUCESSO!
    echo ============================================================
    echo.
    echo O executavel esta em: UltraDanfeXML_Portable\UltraDanfeXML.exe
    echo.
) else (
    echo.
    echo ============================================================
    echo   ERRO NO BUILD!
    echo ============================================================
    echo.
)

pause
