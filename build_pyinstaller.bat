@echo off
echo Construindo executavel em segundo plano...
echo Isso pode levar 3-5 minutos. Aguarde!
echo.

REM Executar PyInstaller em modo silencioso (preferir .venv para não depender de Python global)
set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
if exist "%PYTHON_EXE%" (
    start /B /WAIT "%PYTHON_EXE%" -m PyInstaller --onefile --windowed --name=UltraDanfeXML --add-data="static;static" --add-data="config;config" --add-data="models;models" --add-data="services;services" --add-data="utils;utils" --add-data=".env;." --add-data="output;output" --hidden-import=flask --hidden-import=flask_cors --hidden-import=openpyxl --hidden-import=lxml --hidden-import=pypdf --hidden-import=requests --hidden-import=brazilfiscalreport --hidden-import=tkinter --hidden-import=PIL main_standalone.py > build_log.txt 2>&1
) else (
    start /B /WAIT py -3 -m PyInstaller --onefile --windowed --name=UltraDanfeXML --add-data="static;static" --add-data="config;config" --add-data="models;models" --add-data="services;services" --add-data="utils;utils" --add-data=".env;." --add-data="output;output" --hidden-import=flask --hidden-import=flask_cors --hidden-import=openpyxl --hidden-import=lxml --hidden-import=pypdf --hidden-import=requests --hidden-import=brazilfiscalreport --hidden-import=tkinter --hidden-import=PIL main_standalone.py > build_log.txt 2>&1
)

echo.
if exist dist\UltraDanfeXML.exe (
    echo [OK] Executavel gerado com sucesso!
    echo.
    
    REM Copiar para pasta portable
    if not exist UltraDanfeXML_Portable mkdir UltraDanfeXML_Portable
    copy /Y dist\UltraDanfeXML.exe UltraDanfeXML_Portable\ > nul
    
    REM Mostrar informacoes
    echo Executavel: UltraDanfeXML_Portable\UltraDanfeXML.exe
    for %%F in (UltraDanfeXML_Portable\UltraDanfeXML.exe) do echo Tamanho: %%~zF bytes
    echo.
    echo [OK] Pronto para distribuir!
) else (
    echo [ERRO] Falha ao gerar executavel
    echo Veja build_log.txt para detalhes
)

pause
