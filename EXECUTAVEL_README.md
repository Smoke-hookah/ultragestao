# Executável Standalone - UltraDanfeXML

## ✅ O que foi implementado

### 1. **Configurações Embutidas no Executável**
- O arquivo `.env` agora é **incluído dentro do executável**
- Usuário **não precisa configurar nada**
- Todas as API_KEYs já vêm pré-configuradas

### 2. **Como Funciona**

#### Durante o Desenvolvimento:
```
config.py → carrega .env da pasta do projeto
```

#### No Executável:
```
config.py → carrega .env de dentro do .exe (sys._MEIPASS)
Output/Logs → criados ao lado do .exe
```

### 3. **Estrutura do Executável**

```
UltraDanfeXML_Portable/
├── UltraDanfeXML.exe  (52MB - inclui Python + dependências + frontend + .env)
└── LEIA-ME.txt        (instruções simples)
```

### 4. **Experiência do Usuário**

1. Extrai o .zip
2. Executa `UltraDanfeXML.exe`
3. Navegador abre automaticamente
4. **Já está pronto para usar!**

Não precisa:
- ❌ Configurar API_KEY
- ❌ Criar arquivo .env
- ❌ Instalar Python/Node
- ❌ Fazer nenhuma configuração

### 5. **Código Modificado**

#### `config.py`
```python
# Detecta modo executável
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)  # .env está aqui dentro
    RUNTIME_DIR = Path(sys.executable).parent  # output/logs aqui
else:
    BASE_DIR = Path(__file__).resolve().parent
    RUNTIME_DIR = BASE_DIR
```

#### `build_exe.py`
```python
# Adiciona .env ao executável
if env_file.exists():
    cmd.append("--add-data=.env;.")
```

### 6. **Arquivos Removidos**
- ❌ `frontend/src/pages/Configuracoes.tsx` (página de config)
- ❌ `frontend/src/components/ConfigCheck.tsx` (verificação)
- ❌ Endpoints `/api/configuracoes` (GET/POST)
- ❌ Item "Configurações" do menu

### 7. **Build do Executável**

```bash
python build_exe.py
```

Gera:
- ✅ Frontend compilado (Vite)
- ✅ Python runtime empacotado
- ✅ Todas as dependências
- ✅ Arquivos estáticos
- ✅ **.env com API_KEYs**

### 8. **Tamanho Final**
- **~52-55 MB** (standalone completo)

### 9. **Distribuição**

1. Compactar `UltraDanfeXML_Portable/` em .zip
2. Distribuir para usuários finais
3. Usuário só precisa:
   - Extrair
   - Executar
   - Usar!

## 🔒 Segurança

**IMPORTANTE:** O executável contém as API_KEYs. 
- Não distribuir publicamente
- Apenas para uso interno/controlado
- API_KEYs ficam dentro do .exe (não visíveis externamente sem descompilar)

## 📝 Instruções para Atualizar API_KEYs

Se precisar mudar as chaves no futuro:

1. Editar `.env` no projeto
2. Executar `python build_exe.py`
3. Novo .exe terá as novas chaves

## ✨ Resultado

**Executável 100% standalone:**
- ✅ Zero configuração do usuário
- ✅ Todas as APIs embarcadas
- ✅ Interface completa
- ✅ Tema claro/escuro
- ✅ Pronto para produção
