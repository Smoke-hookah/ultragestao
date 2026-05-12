# ✨ INTERFACE GRÁFICA - Implementada!

## O que foi adicionado

### 🎨 Nova Interface Gráfica com 3 Novos Arquivos:

#### 1. **`utils/ui.py`** - Módulo de Interface
Funções para:
- Abrir **Explorador de Arquivos** (selecionar planilha)
- Abrir **Explorador de Pastas** (selecionar XMLs)
- **Salvar pasta automaticamente** em `config/preferencias.json`
- **Usar pasta salva** na próxima execução
- Diálogos de confirmação
- Mensagens informativas

#### 2. **`services/leitor_xml.py`** - Leitor de XMLs
Classe `LeitorXML` que:
- Lê arquivos XML de uma pasta
- Extrai **chave de acesso** (44 dígitos) do nome do arquivo
- Processa todos os XMLs da pasta
- Retorna resumo com sucessos/erros

#### 3. **`interface_grafica.py`** - Aplicação Principal
Função `interface_principal()` que:
- Orquestra todo o fluxo da interface
- Guia o usuário passo a passo
- Seleciona planilha Excel
- Seleciona ou reutiliza pasta de XMLs
- Confirma opções de processamento
- Integra com o `Orquestrador` para processar

#### 4. **`config/`** - Diretório de Configuração
- Armazena `preferencias.json` com a pasta de XMLs salva

---

## 🚀 Como Usar

### Opção 1: Interface Gráfica (NOVO!)
```bash
python main.py --gui
```

Processo:
1. 📂 Seleciona planilha Excel (janela gráfica)
2. 📁 Seleciona pasta com XMLs (janela gráfica)
3. 💾 Pasta é **salva automaticamente**
4. ⚙️ Escolhe opções (PDF, XML, tipo de separação)
5. ▶️ Confirma e processa
6. ✅ Mostra resumo final

### Opção 2: API (já existente)
```bash
python main.py --api
```

### Opção 3: CLI com Parâmetros (já existente)
```bash
python main.py planilha.xlsx --tipo-separacao placa --pdf
```

---

## 💡 Funcionalidades Principais

### ✅ Seleção Visual de Arquivos
- Sem necessidade de digitar caminhos
- Explorador nativo do Windows
- Validação automática de extensões

### ✅ Pasta de XMLs Salva
- **Primeira vez**: Pede para escolher
- **Próximas vezes**: Oferece usar a pasta anterior
- **Configuração**: Salva em `config/preferencias.json`
- **Flexível**: Pode mudar sempre que quiser

### ✅ Fluxo Guiado Passo a Passo
```
1. Escolher Planilha
   ↓
2. Escolher (ou Reutilizar) Pasta XMLs
   ↓
3. Verificar XMLs Encontrados
   ↓
4. Escolher Opções
   ├─ Baixar PDF? (Sim/Não)
   ├─ Baixar XML? (Sim/Não)
   └─ Separar por Placa ou Rota?
   ↓
5. Confirmar Operação
   ↓
6. Processar (integrado com Orquestrador)
   ↓
7. Mostrar Resumo Final
```

### ✅ Feedback Detalhado
- Mostra total de XMLs encontrados
- Lista erros de leitura (se houver)
- Valida formatos de arquivos
- Exibe resumo com taxa de sucesso

---

## 📂 Estrutura de Diretórios (Atualizada)

```
UltraDanfeXML/
├── config/                  ← NOVO: Configurações
│   └── preferencias.json    ← NOVO: Pasta de XMLs salva
│
├── utils/
│   ├── __init__.py
│   ├── logger.py
│   ├── validators.py
│   └── ui.py               ← NOVO: Interface gráfica
│
├── services/
│   ├── __init__.py
│   ├── excel_reader.py
│   ├── xml_builder.py
│   ├── api_client.py
│   ├── gestor_saida.py
│   ├── orquestrador.py
│   └── leitor_xml.py       ← NOVO: Leitor de XMLs
│
├── interface_grafica.py     ← NOVO: Aplicação GUI
├── main.py                  ← ATUALIZADO: Adicionado --gui
├── api.py
├── config.py
├── requirements.txt
├── .env
├── README.md
├── QUICK_START.md
├── GUI_GUIDE.md            ← NOVO: Guia da Interface Gráfica
└── STATUS_PROJETO.md
```

---

## 🔄 Fluxo de Dados

```
┌─────────────────────────┐
│  interface_grafica.py   │  Orquestra UI
└────────┬────────────────┘
         │
         ├─→ utils/ui.py (Seleção visual)
         │   ├─ selecionar_planilha()
         │   ├─ selecionar_ou_usar_pasta_xmls_salva()
         │   └─ confirmar_acao()
         │
         ├─→ services/leitor_xml.py (Validação XMLs)
         │   └─ LeitorXML.processar_todos_xmls()
         │
         └─→ services/orquestrador.py (Processamento)
             └─ Orquestrador.processar_planilha()
```

---

## 📝 Arquivo: `config/preferencias.json`

Exemplo de conteúdo após primeira execução:
```json
{
  "pasta_xmls": "C:\\Users\\feito\\Desktop\\XMLs_Pendentes"
}
```

Como **limpar preferências**:
```powershell
# Windows PowerShell
Remove-Item config\preferencias.json -Force

# Próxima execução pedirá para escolher pasta novamente
python main.py --gui
```

---

## 🎯 Benefícios

| Antes | Depois |
|-------|--------|
| Digitar caminhos de arquivo | Clique no Explorador |
| Memorizar caminho de XMLs | Pasta salva automaticamente |
| Sem validação visual | Verifica XMLs antes de processar |
| Sem confirmação | Diálogos antes de cada ação |
| Sem feedback | Resumo detalhado ao final |

---

## 🧪 Testando a Interface

### Pré-requisitos
✓ Python 3.8+  
✓ tkinter (já vem com Python no Windows)  
✓ Dependências instaladas (`pip install -r requirements.txt`)

### Teste Rápido
```bash
# 1. Abra a interface
python main.py --gui

# 2. Selecione um Excel na pasta Documents
# 3. Selecione uma pasta com XMLs
# 4. Escolha as opções
# 5. Confirme e processe
```

### Validar Preferências Salvas
```bash
# 1. Execute interface_grafica.py novamente
python main.py --gui

# 2. Deve perguntar: "Usar pasta salva?"
# 3. Clique SIM para reutilizar
```

---

## 🔧 Customização

### Mudar Texto dos Diálogos
Edite `utils/ui.py`:
```python
# Linha 45 aproximadamente
filedialog.askopenfilename(
    title="Seu Texto Aqui",  ← Customize
    # ...
)
```

### Salvar Mais Preferências
Edite `utils/ui.py`:
```python
prefs = {
    'pasta_xmls': str(pasta),
    'tipo_separacao': 'placa',    # ← Novo
    'baixar_pdf': True,            # ← Novo
}
```

### Adicionar Validação Customizada
Edite `services/leitor_xml.py`:
```python
def validar_xml_customizado(self, arquivo):
    # Sua validação aqui
    pass
```

---

## ❓ FAQ

**P: A pasta é salva em texto limpo?**  
R: Sim, em `config/preferencias.json` (JSON simples). Você pode editar manualmente.

**P: Como resetar a pasta salva?**  
R: Delete `config/preferencias.json` e execute novamente.

**P: Funciona sem Internet?**  
R: Sim! A seleção de arquivos/pastas funciona offline. Só precisa de internet para enviar XMLs à API.

**P: Posso usar em Linux/Mac?**  
R: Sim! tkinter é multiplataforma. Caminhos funcionam nativamente no sistema.

**P: Como executar sem linha de comando?**  
R: Crie um atalho/batch apontando para `python main.py --gui`

---

## 📞 Próximas Melhorias Possíveis

- [ ] Drag & Drop de arquivos
- [ ] Preview de XMLs
- [ ] Histórico de processamentos
- [ ] Retentativas automáticas
- [ ] Barra de progresso visual
- [ ] Filtros por data/valor nos XMLs
- [ ] Exportar log em PDF

---

## ✅ RESUMO

**Adicionado:**
- ✅ Interface gráfica com file picker
- ✅ Pasta de XMLs salva automaticamente
- ✅ Leitor de XMLs com validação
- ✅ Fluxo guiado passo a passo
- ✅ Documentação completa (`GUI_GUIDE.md`)

**Como Usar:**
```bash
python main.py --gui
```

**Pronto para usar!** 🎉
