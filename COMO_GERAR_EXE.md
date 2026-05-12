# Como Gerar o Executável (.exe)

## Pré-requisitos

1. **Python 3.13+** instalado e no PATH
2. **Node.js** instalado (para build do frontend)
3. **Dependências Python** instaladas: `pip install -r requirements.txt`
4. **PyInstaller** será instalado automaticamente se não estiver presente

## Processo de Build

### Método 1: Script Automatizado (Recomendado)

Execute o script batch:

```bash
build_exe.bat
```

Ou execute diretamente o Python:

```bash
python build_exe.py
```

### Método 2: Manual

Se preferir executar passo a passo:

```bash
# 1. Buildar frontend
cd frontend
npm install
npm run build
cd ..

# 2. Copiar build para pasta static
xcopy /E /I /Y frontend\dist static\dist

# 3. Instalar PyInstaller
pip install pyinstaller

# 4. Gerar executável
pyinstaller --onefile --windowed --name=UltraDanfeXML ^
    --add-data="static;static" ^
    --add-data="config;config" ^
    --add-data="models;models" ^
    --add-data="services;services" ^
    --add-data="utils;utils" ^
    --hidden-import=flask ^
    --hidden-import=flask_cors ^
    --hidden-import=openpyxl ^
    --hidden-import=lxml ^
    --hidden-import=pypdf ^
    --hidden-import=requests ^
    --hidden-import=brazilfiscalreport ^
    --hidden-import=tkinter ^
    --hidden-import=PIL ^
    main_standalone.py
```

## O que o Build Faz

O script `build_exe.py` executa 4 etapas:

1. **Limpeza**: Remove builds anteriores
2. **Build Frontend**: Compila o React com Vite
3. **PyInstaller**: Cria o executável empacotando:
   - Python runtime
   - Todas as dependências Python
   - Frontend compilado
   - Arquivos de configuração
4. **Pacote**: Cria pasta `UltraDanfeXML_Portable` com:
   - `UltraDanfeXML.exe`
   - `.env.example` (template de configuração)
   - `LEIA-ME.txt` (instruções de uso)

## Resultado

Após o build, você terá:

```
UltraDanfeXML_Portable/
├── UltraDanfeXML.exe    (executável standalone ~100-200MB)
├── .env.example          (template de configuração)
└── LEIA-ME.txt          (instruções)
```

## Como Distribuir

1. Compacte a pasta `UltraDanfeXML_Portable` em .zip
2. Distribua o .zip
3. Usuário final apenas:
   - Extrai o .zip
   - Copia `.env.example` para `.env`
   - Configura `API_KEY` no `.env`
   - Executa `UltraDanfeXML.exe`

## Características do Executável

- ✅ **Standalone**: Não requer Python ou Node.js instalado
- ✅ **Auto-contido**: Todas as dependências incluídas
- ✅ **Auto-inicia**: Abre navegador automaticamente
- ✅ **Interface Gráfica**: Sem janela de console
- ✅ **Portável**: Pode ser executado de qualquer pasta

## Troubleshooting

### Erro: "npm não é reconhecido"
- Instale Node.js: https://nodejs.org/

### Erro: PyInstaller falha
- Tente: `pip install --upgrade pyinstaller`
- Verifique antivírus (pode bloquear o build)

### Executável muito grande
- Normal: ~100-200MB (inclui Python runtime completo)
- Para reduzir: considere usar `--onedir` ao invés de `--onefile`

### Executável não inicia
- Verifique se `.env` está configurado
- Execute via terminal para ver mensagens de erro:
  ```bash
  .\UltraDanfeXML.exe
  ```

## Notas Técnicas

- **Entry Point**: `main_standalone.py` (não usar `main.py`)
- **Detecção**: Código detecta automaticamente se está rodando como .exe via `sys.frozen`
- **Recursos**: Arquivos estáticos são acessados via `sys._MEIPASS` quando empacotado
- **Servidor**: Flask roda em modo produção (debug=False, use_reloader=False)
- **Browser**: Abre automaticamente após 1.5s do início do servidor

## Melhorias Futuras

- [ ] Auto-update system
- [ ] Instalador (NSIS ou InnoSetup)
- [ ] Assinatura digital do executável
- [ ] Compressão UPX para reduzir tamanho
