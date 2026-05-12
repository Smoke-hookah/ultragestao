@echo off
REM Verificacao rapida do executavel

echo ============================================================
echo   VERIFICACAO DO EXECUTAVEL ULTRADANFE XML
echo ============================================================
echo.

REM Verificar se .env existe
if exist .env (
    echo [OK] .env encontrado no projeto
    echo.
    echo Primeiras linhas do .env:
    powershell -Command "Get-Content .env -First 3"
    echo.
) else (
    echo [ERRO] .env NAO encontrado!
    echo        Crie um arquivo .env com API_KEY antes de buildar
    pause
    exit /b 1
)

REM Verificar se executavel foi gerado
if exist UltraDanfeXML_Portable\UltraDanfeXML.exe (
    echo [OK] Executavel encontrado!
    echo.
    powershell -Command "$exe = Get-Item 'UltraDanfeXML_Portable\UltraDanfeXML.exe'; Write-Host 'Tamanho:' ([math]::Round($exe.Length/1MB,2)) 'MB'; Write-Host 'Data:' $exe.LastWriteTime"
    echo.
    echo [OK] Pronto para distribuir!
    echo.
    echo Conteudo do pacote:
    dir /B UltraDanfeXML_Portable
) else (
    echo [AVISO] Executavel ainda nao foi gerado
    echo         Execute: build_exe.bat
    echo         Ou: .venv\Scripts\python.exe build_exe.py
)

echo.
echo ============================================================
pause
