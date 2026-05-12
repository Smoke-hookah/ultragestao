# 🎨 INTERFACE GRÁFICA - Ultra Danfe XML

## Como Usar

### 1️⃣ Iniciar a Interface Gráfica

```bash
python main.py --gui
```

### 2️⃣ Processo Passo a Passo

#### 1. Selecionar Planilha
- Abre janela do **Explorador de Arquivos**
- Selecione seu arquivo `.xlsx` com as alocações

#### 2. Selecionar Pasta de XMLs
- Abre janela do **Explorador de Pastas**
- Selecione a pasta que contém seus arquivos XML
- ⭐ **Esta pasta será salva automaticamente**

#### 3. Usar Pasta Salva
- Na próxima execução, a interface pergunta se quer usar a pasta anterior
- Clique **SIM** para usar a mesma pasta (recomendado)
- Clique **NÃO** para selecionar uma pasta diferente

#### 4. Verificação de XMLs
- Sistema lista todos os XMLs encontrados
- Mostra erros de leitura (se houver)

#### 5. Selecionar Opções
- **Baixar PDFs?** - Sim ou Não
- **Baixar XMLs?** - Sim ou Não  
- **Organizar por Placa ou Rota?** - Escolha o critério

#### 6. Confirmar e Processar
- Revisa o resumo de operação
- Clique **SIM** para iniciar
- Sistema processa e mostra resultado final

---

## 📁 Armazenamento de Preferências

A pasta de XMLs é salva em:
```
config/preferencias.json
```

Conteúdo exemplo:
```json
{
  "pasta_xmls": "C:\\Users\\seu_usuario\\Desktop\\XMLs"
}
```

### Limpar Preferências
Se quiser resetar a pasta salva, delete o arquivo `config/preferencias.json`:

```powershell
Remove-Item config\preferencias.json -Force
```

---

## 🎯 Vantagens da Interface Gráfica

✅ Seleção visual de arquivos (sem digitar caminhos)  
✅ Pasta de XMLs salva automaticamente  
✅ Confirmações antes de processar  
✅ Feedback visual durante processamento  
✅ Resumo detalhado ao final  
✅ Sem necessidade de linha de comando  

---

## 🔧 Estrutura Interna

### Arquivo: `utils/ui.py`
Funções de interface gráfica:
- `selecionar_planilha()` - File picker para Excel
- `selecionar_pasta_xmls()` - Folder picker
- `selecionar_ou_usar_pasta_xmls_salva()` - Smart folder selector
- `salvar_pasta_xmls()` - Salva preferência
- `obter_pasta_xmls_salva()` - Recupera preferência
- `confirmar_acao()` - Diálogo Yes/No
- `mostrar_mensagem()` - Exibe mensagens

### Arquivo: `services/leitor_xml.py`
Classe `LeitorXML`:
- Lê arquivos XML de uma pasta
- Extrai chaves de acesso
- Valida formatos
- Processa XMLs em lote

### Arquivo: `interface_grafica.py`
Função principal:
- `interface_principal()` - Orquestra toda a interface
- Fluxo guiado passo a passo
- Integração com `Orquestrador`

---

## 📋 Exemplos de Uso

### Exemplo 1: Primeira Execução
```bash
python main.py --gui

# Resultado esperado:
# 1. Abre Explorador → Seleciona "planilha_jan.xlsx"
# 2. Abre Explorador de Pastas → Seleciona "C:\XMLs_Pendentes"
# 3. Encontra 15 XMLs na pasta
# 4. Pergunta opções de processamento
# 5. Processa e exibe resumo
```

### Exemplo 2: Execução Seguinte
```bash
python main.py --gui

# Resultado esperado:
# 1. Abre Explorador → Seleciona "planilha_fev.xlsx"
# 2. Pergunta: "Usar pasta salva? C:\XMLs_Pendentes"
# 3. Clica SIM → Usa a mesma pasta
# 4. Processa com nova planilha, XMLs anteriores
```

### Exemplo 3: Mudar Pasta de XMLs
```bash
python main.py --gui

# 1. Seleciona planilha
# 2. Pergunta: "Usar pasta salva?"
# 3. Clica NÃO → Abre novo Explorador de Pastas
# 4. Seleciona pasta diferente (salva automaticamente)
# 5. Processa com nova pasta
```

---

## ⚙️ Configuração

### Variáveis de Ambiente (.env)
```
API_KEY=sua_chave_aqui
API_URL=https://api.meudanfe.com.br
DELAY_BETWEEN_REQUESTS=1.5
MAX_REQUESTS_PER_SECOND=1
```

### Formato de Planilha
Colunas necessárias:
- Chave (44 dígitos)
- Placa (ou Rota)
- Cliente

### Formato de XML
XMLs devem ter formato:
- `NFE-35251247380171000157550020000825841972733416.xml`
- Contém a chave de acesso de 44 dígitos no nome

---

## 🐛 Troubleshooting

### Janelas não abrem
**Solução**: Verifique se tkinter está instalado:
```bash
python -c "import tkinter; print('✓ tkinter OK')"
```

### Pasta não é salva
**Solução**: Verifique permissões de escrita em `config/`
```bash
python -c "from pathlib import Path; Path('config').mkdir(exist_ok=True); print('✓ config criado')"
```

### XMLs não são encontrados
**Solução**: Verifique se estão em `.xml` minúsculo:
```powershell
Get-ChildItem "C:\pasta" -Filter "*.xml" | Measure-Object
```

---

## 💡 Dicas Úteis

1. **Atalho**: Crie um atalho no Desktop apontando para:
   ```
   python main.py --gui
   ```

2. **Batch File** (Windows): Crie `iniciar_gui.bat`:
   ```batch
   @echo off
   cd /d "%~dp0"
   python main.py --gui
   pause
   ```

3. **Backup de XMLs**: Copie a pasta de XMLs antes de processar

4. **Monitorar Logs**: Abra `logs/app.log` durante processamento

---

## 📞 Próximas Melhorias

- [ ] Drag & Drop de arquivos
- [ ] Visualização de XMLs antes de enviar
- [ ] Histórico de processamentos
- [ ] Retry automático de erros
- [ ] Cancelamento durante processamento
- [ ] Filtros por data nos XMLs
