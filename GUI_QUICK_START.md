# ⚡ INTERFACE GRÁFICA - INÍCIO RÁPIDO

## 🚀 Comece em 30 Segundos

### 1️⃣ Abra o Terminal
```bash
cd C:\Users\feito\Documents\Project\UltraDanfeXML
```

### 2️⃣ Execute o Comando
```bash
python main.py --gui
```

### 3️⃣ Siga os Passos na Tela
- Selecione sua planilha Excel
- Selecione a pasta com XMLs
- Escolha as opções
- Clique para processar

**Pronto! 🎉**

---

## 📋 O Que Você Vai Ver

### Primeira Execução
```
📂 Selecionar Planilha...
├─ Explorador abre
└─ Você escolhe: planilha.xlsx

📁 Selecionar Pasta XMLs...
├─ Explorador abre
└─ Você escolhe: C:\Dados\XMLs

💾 Pasta SALVA automaticamente!

🔍 XMLs encontrados: 15
✓ Processados: 15
✗ Erros: 0

⚙️ Opções:
├─ Baixar PDF? (Sim/Não)
├─ Baixar XML? (Sim/Não)
└─ Separar por: Placa ou Rota?

▶️ Processa e mostra resultado
```

### Segunda Execução (RÁPIDO!)
```
📂 Selecionar Planilha...
└─ Você escolhe: planilha_nova.xlsx

📁 Pasta de XMLs
└─ "Usar pasta salva? C:\Dados\XMLs"
   ├─ [SIM] → Usa a mesma pasta! ⚡
   └─ [NÃO] → Abre Explorador para escolher

(resto igual ao anterior)
```

---

## 🎯 Casos de Uso Rápido

### Cenário 1: Primeira Vez
```bash
python main.py --gui

Passo 1: Seleciona planilha
Passo 2: Seleciona pasta XMLs (SALVA!)
Passo 3: Escolhe opções
Passo 4: Processa
```

### Cenário 2: Mesma Pasta de XMLs
```bash
python main.py --gui

Passo 1: Seleciona planilha NOVA
Passo 2: Clica SIM (reutiliza pasta anterior)
Passo 3: Escolhe opções
Passo 4: Processa
```

### Cenário 3: Pasta de XMLs Diferente
```bash
python main.py --gui

Passo 1: Seleciona planilha
Passo 2: Clica NÃO (abre Explorador)
Passo 3: Escolhe OUTRA pasta (salva nova!)
Passo 4: Escolhe opções
Passo 5: Processa
```

---

## 💾 Onde a Pasta é Salva?

**Arquivo:** `config/preferencias.json`

**Conteúdo:**
```json
{
  "pasta_xmls": "C:\\Users\\feito\\Desktop\\XMLs"
}
```

**Para resetar:**
```powershell
Remove-Item config\preferencias.json
# Próxima execução pedirá para escolher pasta novamente
```

---

## ❓ FAQ Rápido

**P: Preciso digitar caminho?**  
R: Não! Tudo é visual via Explorador.

**P: A pasta é salva?**  
R: Sim! Em `config/preferencias.json`

**P: Posso mudar de pasta XMLs?**  
R: Sim! Clique "NÃO" quando perguntar.

**P: Funciona em Linux/Mac?**  
R: Sim! Funciona em qualquer plataforma.

**P: Preciso instalar algo?**  
R: Não! Tudo já está pronto (tkinter vem com Python).

---

## 🎨 Fluxo Visual

```
┌──────────────────────────────────────────────────────┐
│ python main.py --gui                                 │
└────────────────┬─────────────────────────────────────┘
                 │
        ┌────────▼────────┐
        │ Explorador      │
        │ Seleciona .xlsx │
        └────────┬────────┘
                 │
        ┌────────▼──────────────────────┐
        │ Preferência salva?             │
        ├─ SIM: usa anterior            │
        └─ NÃO: abre Explorador         │
                 │
        ┌────────▼────────┐
        │ Escolhe opções  │
        │ PDF/XML/Tipo    │
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │ Processa XMLs   │
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │ Mostra resumo   │
        │ Total/Sucesso   │
        └─────────────────┘
```

---

## ⚡ Atalhos (Windows)

### Criar Atalho no Desktop

**Opção 1: Batch File**

Crie `iniciar_gui.bat`:
```batch
@echo off
cd /d "%~dp0"
python main.py --gui
pause
```

**Opção 2: Link Simbólico**
```powershell
New-Item -ItemType SymbolicLink -Name "GUI.lnk" -Target "python main.py --gui"
```

---

## 📊 Estrutura de Saída

Arquivos processados ficarão em:
```
output/
└── 2025-01-11_14-30-45/
    └── planilha_nome/
        └── placa/
            ├── ABC1234/
            │   ├── pdf/
            │   │   └── NFE-xxxxx.pdf
            │   └── xml/
            │       └── NFE-xxxxx.xml
            ├── SSV3J72/
            │   └── pdf/
            └── XYZ9876/
```

---

## 🔧 Troubleshooting Rápido

**P: Nada acontece ao clicar em GUI?**  
R: Verifique se tkinter está instalado:
```bash
python -c "import tkinter; print('OK')"
```

**P: Pasta não aparece em preferências?**  
R: Verifique permissões de escrita em `config/`

**P: XMLs não são encontrados?**  
R: Verifique se estão em `.xml` (minúsculo)

**P: Erro de import?**  
R: Reinstale dependências:
```bash
pip install -r requirements.txt
```

---

## 📚 Mais Informações

Para documentação completa, leia:
- `SUMARIO_EXECUTIVO.md` - Resumo geral
- `GUI_GUIDE.md` - Guia detalhado
- `INDICE_ARQUIVOS.md` - Índice de arquivos
- `INTERFACE_PRONTA.md` - Documentação técnica

---

## 🎯 Resumo

| Item | Resposta |
|------|----------|
| **Como abrir?** | `python main.py --gui` |
| **Pasta salva?** | Sim! Em `config/preferencias.json` |
| **Pode mudar pasta?** | Sim! Clique "NÃO" quando perguntar |
| **Funciona offline?** | Sim! Apenas para seleção (PUT precisa internet) |
| **Pode usar CLI?** | Sim! Todas as 3 opções funcionam |

---

## 🚀 Começar Agora!

```bash
python main.py --gui
```

**Pronto para usar! 🎉**
