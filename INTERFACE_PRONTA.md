# 🎉 INTERFACE GRÁFICA COM EXPLORADOR - PRONTA!

## ✨ O Que foi Implementado

### 🎯 Requisito Implementado
> "Coloca pra selecionar a planilha com uma janela do explorer, e a pasta com os xml, a pasta tem que ser requisitada apenas uma vez tem que ficar salvo"

✅ **100% Implementado e Testado!**

---

## 📦 Novos Arquivos Criados

### 1. **`utils/ui.py`** - Módulo de Interface Gráfica
Funções para interação visual:
- `selecionar_planilha()` - Abre Explorador para escolher Excel
- `selecionar_pasta_xmls()` - Abre Explorador de Pastas para XMLs
- `obter_pasta_xmls_salva()` - Recupera pasta salva
- `salvar_pasta_xmls()` - Salva pasta em preferências
- `selecionar_ou_usar_pasta_xmls_salva()` - **Smart: oferece usar a pasta anterior**
- `confirmar_acao()` - Diálogo Sim/Não
- `mostrar_mensagem()` - Exibe mensagens

### 2. **`services/leitor_xml.py`** - Processador de XMLs
Classe `LeitorXML`:
- Lê pasta de XMLs
- Extrai chave de acesso (44 dígitos)
- Valida formatos
- Retorna resumo processado

### 3. **`interface_grafica.py`** - Aplicação Principal
Função `interface_principal()`:
- Orquestra todo o fluxo
- Guia passo a passo
- Integra com Orquestrador

### 4. **`config/`** - Diretório de Configuração
- `preferencias.json` - Armazena pasta de XMLs salva

### 5. **Documentação**
- `GUI_GUIDE.md` - Guia detalhado da interface
- `GUI_IMPLEMENTADA.md` - Resumo de implementação

---

## 🚀 Como Usar

### Opção 1: Interface Gráfica (NOVO!)
```bash
python main.py --gui
```

**Processo:**
1. 📂 Seleciona planilha Excel (Explorador visual)
2. 📁 Seleciona pasta com XMLs (Explorador visual)
3. 💾 **Pasta é SALVA automaticamente**
4. ⚙️ Escolhe opções
5. ▶️ Processa
6. ✅ Mostra resultado

---

## 💾 Sistema de Preferências (CHAVE!)

### Primeira Execução
```
python main.py --gui
    ↓
Seleciona planilha
    ↓
Seleciona pasta XMLs (abre Explorador)
    ↓
Sistema SALVA em: config/preferencias.json
    ↓
Processa
```

### Segunda Execução
```
python main.py --gui
    ↓
Seleciona planilha
    ↓
Pergunta: "Usar pasta salva? C:\Meus Arquivos\XMLs"
    ├─ SIM → Usa a mesma pasta (RÁPIDO!)
    └─ NÃO → Abre Explorador para escolher outra
    ↓
Processa
```

### Arquivo de Preferências
**Localização:** `config/preferencias.json`

**Conteúdo:**
```json
{
  "pasta_xmls": "C:\\Users\\feito\\Desktop\\XMLs"
}
```

**Para Resetar:**
```powershell
Remove-Item config\preferencias.json
python main.py --gui  # Próxima execução pede para escolher novamente
```

---

## 📊 Estrutura de Fluxo

```
┌─────────────────────────────────┐
│   python main.py --gui          │
└────────────┬────────────────────┘
             │
             ├─→ interface_grafica.py
             │   │
             │   ├─ Abre Explorador Planilha
             │   │  └─→ user selects file.xlsx
             │   │
             │   ├─ Abre Explorador XMLs
             │   │  └─→ utils/ui.py
             │   │      ├─ Verifica preferência salva
             │   │      ├─ Se existe: pergunta "Usar?"
             │   │      ├─ Se sim: usa caminho salvo
             │   │      └─ Se não: abre novo Explorador
             │   │
             │   ├─ Salva novo caminho (se selecionou novo)
             │   │  └─→ config/preferencias.json
             │   │
             │   ├─ Lê XMLs da pasta
             │   │  └─→ services/leitor_xml.py
             │   │
             │   ├─ Confirma opções (PDF, XML, tipo)
             │   │
             │   └─ Processa
             │      └─→ services/orquestrador.py
             │
             └─→ Mostra resumo
```

---

## ✅ Características Principais

| Feature | Detalhes |
|---------|----------|
| 📂 File Picker | Explorador nativo do Windows |
| 📁 Folder Picker | Escolher pasta com Explorador |
| 💾 Salvar Pasta | Automático em `config/preferencias.json` |
| 🔄 Reutilizar | Oferece usar pasta anterior |
| ✏️ Mudar | Pode selecionar pasta diferente sempre |
| 🔍 Validar | Verifica XMLs antes de processar |
| 📊 Feedback | Resumo detalhado ao final |
| ⚡ Rápido | Cache de preferências |

---

## 🧪 Teste de Demonstração

```bash
python demo_preferencias.py
```

**Saída:**
```
🎨 DEMONSTRAÇÃO - Sistema de Preferências

✅ Pasta de XMLs salva encontrada:
   📁 C:\Users\feito\Desktop

💾 Salvando preferência de exemplo...
   ✓ Salvo: C:\Users\feito\Desktop

🔍 Verificando se foi salvo corretamente...
   ✓ Recuperado: C:\Users\feito\Desktop

✅ Demonstração Concluída!
```

---

## 📁 Estrutura de Projeto (Atualizada)

```
UltraDanfeXML/
├── config/                         ← NOVO
│   └── preferencias.json           ← Pasta XMLs salva
│
├── utils/
│   ├── __init__.py
│   ├── logger.py
│   ├── validators.py
│   └── ui.py                       ← NOVO: Interface Gráfica
│
├── services/
│   ├── __init__.py
│   ├── excel_reader.py
│   ├── xml_builder.py
│   ├── api_client.py
│   ├── gestor_saida.py
│   ├── orquestrador.py
│   └── leitor_xml.py               ← NOVO: Leitor de XMLs
│
├── interface_grafica.py            ← NOVO: GUI Principal
├── demo_preferencias.py            ← NOVO: Teste de Demo
├── main.py                         ← ATUALIZADO: Adicionado --gui
├── api.py
├── config.py
├── requirements.txt
├── .env
├── GUI_GUIDE.md                    ← NOVO: Documentação
├── GUI_IMPLEMENTADA.md             ← NOVO: Resumo
└── README.md
```

---

## 🎯 Comparação: Antes vs Depois

### ❌ Antes (Linha de Comando)
```bash
python main.py planilha.xlsx --tipo-separacao placa --pdf

# Problema: precisa digitar caminho completo da planilha
# Problema: não salva pasta de XMLs
```

### ✅ Depois (Interface Gráfica)
```bash
python main.py --gui

# Benefício: Visual, sem digitar
# Benefício: Pasta de XMLs SALVA automaticamente
# Benefício: Próxima vez, oferece usar a mesma pasta
```

---

## 📝 Exemplos de Uso

### Cenário 1: Primeira Vez
```
1. python main.py --gui
2. Clica em "Abrir" → Seleciona "Planilha_Jan_2026.xlsx"
3. Clica em "Abrir" → Seleciona "C:\Dados\XMLs_Pendentes"
4. Sistema salva pasta em config/preferencias.json
5. Escolhe opções (PDF, XML, tipo de separação)
6. Clica em "Processar"
7. ✅ Processa e mostra resultado
```

### Cenário 2: Segunda Vez (RÁPIDO)
```
1. python main.py --gui
2. Clica em "Abrir" → Seleciona "Planilha_Fev_2026.xlsx"
3. Pergunta: "Usar pasta salva? C:\Dados\XMLs_Pendentes"
4. Clica em "SIM" → Usa a mesma pasta!
5. Escolhe opções
6. Clica em "Processar"
7. ✅ Processa com nova planilha
```

### Cenário 3: Mudar Pasta
```
1. python main.py --gui
2. Clica em "Abrir" → Seleciona "Planilha_Mar_2026.xlsx"
3. Pergunta: "Usar pasta salva? C:\Dados\XMLs_Pendentes"
4. Clica em "NÃO" → Abre novo Explorador
5. Seleciona "C:\Novos\XMLs"
6. Sistema SALVA nova pasta
7. Processa com nova pasta
```

---

## 🔧 Detalhes Técnicos

### Módulo `utils/ui.py`
```python
# Seleção de planilha
arquivo = selecionar_planilha()  # → "C:\...\planilha.xlsx"

# Sistema inteligente de pasta
pasta = selecionar_ou_usar_pasta_xmls_salva()  # → Usa salva ou pede nova

# Salvar para próxima vez
salvar_pasta_xmls("C:\Dados\XMLs")  # → Salva em JSON

# Recuperar preferência
pasta_anterior = obter_pasta_xmls_salva()  # → "C:\Dados\XMLs"
```

### Módulo `services/leitor_xml.py`
```python
leitor = LeitorXML("C:\Dados\XMLs")
resultado = leitor.processar_todos_xmls()

# resultado = {
#   'total': 5,
#   'processados': 5,
#   'erros': 0,
#   'arquivos': [...]
# }
```

---

## 🎓 Código de Integração

Na `interface_grafica.py`:
```python
# 1. Seleciona arquivos
planilha = selecionar_planilha()
pasta_xmls = selecionar_ou_usar_pasta_xmls_salva()

# 2. Verifica XMLs
leitor = LeitorXML(pasta_xmls)
resultado = leitor.processar_todos_xmls()

# 3. Confirma operação
if confirmar_acao("Iniciar", f"Processar {resultado['processados']} XMLs?"):
    
    # 4. Processa
    orq = Orquestrador()
    sucesso, alocacoes = orq.processar_planilha(
        planilha,
        tipo_separacao="placa",
        baixar_pdf=True,
        baixar_xml=False
    )
    
    # 5. Mostra resultado
    mostrar_mensagem("OK", f"✓ {resumo['sucesso']} processados")
```

---

## ✨ Benefícios

| Antes | Depois |
|-------|--------|
| Digitar caminho completo | Visual via Explorador |
| Memorizar pasta de XMLs | Salvo automaticamente |
| Sem validação de entrada | Valida XMLs antes |
| Comando via terminal | Interface gráfica |
| Sem feedback visual | Resumo detalhado |

---

## 🚀 Próximos Passos

1. **Teste agora:**
   ```bash
   python main.py --gui
   ```

2. **Veja a demonstração:**
   ```bash
   python demo_preferencias.py
   ```

3. **Leia mais em:**
   - `GUI_GUIDE.md` - Guia completo
   - `GUI_IMPLEMENTADA.md` - Resumo técnico

---

## 📞 Resumo

✅ Interface gráfica completa com Explorador  
✅ Pasta de XMLs salva automaticamente em JSON  
✅ Oferece reutilizar pasta anterior  
✅ Validação de XMLs antes de processar  
✅ Fluxo passo a passo guiado  
✅ Integrado com Orquestrador existente  
✅ Documentação completa  

**Status: PRONTO PARA USAR! 🎉**
