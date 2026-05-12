# 🚀 GUIA RÁPIDO - Ultra Danfe XML

## ⚡ Início Rápido (3 Passos)

### 1️⃣ Configurar API Key

Abra o arquivo `.env` e adicione sua chave da API:

```
API_URL=https://api.meudanfe.com.br/v2
API_KEY=SUA_CHAVE_AQUI
LOG_LEVEL=INFO
DELAY_BETWEEN_REQUESTS=1.5
MAX_REQUESTS_PER_SECOND=1
```

**Modo local (teste) sem API Key (opcional):**
- Se você quer testar sem depender da API/rede, pode usar `metodo_pdf=local`.
- Nesse caso, adicione no `.env`:
    - `ALLOW_NO_API_KEYS=1`
- E instale a dependência opcional:
    - `pip install brazilfiscalreport`

**Como obter a API Key:**
- Acesse: https://www.meudanfe.com.br (Área do Cliente)
- Menu: API / Integração
- Copie sua Api-Key

### 2️⃣ Escolher Modo de Execução

#### Opção A: API REST (Para Frontend)

```bash
python main.py --api
```

A API estará em: `http://localhost:5000`

#### Opção B: Linha de Comando

```bash
python main.py exemplo_de_planilha.xlsx --tipo-separacao placa --pdf
```

Para teste local (sem API):

```bash
python main.py exemplo_de_planilha.xlsx --tipo-separacao placa --pdf --metodo-pdf local
```

### 3️⃣ Processar Planilha

Seu arquivo será processado e organizado em:

```
output/
└── 2025-01-11_10-30-45/
    └── exemplo_de_planilha/
        └── placa/
            └── SSV3J72/
                ├── pdf/
                │   └── NFE-35251247380171000157550020000825841972733416.pdf
                └── xml/
                    └── NFE-35251247380171000157550020000825841972733416.xml
```

---

## 🔗 API REST - Endpoints Principais

### Processar Planilha

```http
POST http://localhost:5000/api/processar
Content-Type: application/json

{
    "caminho_planilha": "/caminho/para/planilha.xlsx",
    "tipo_separacao": "placa",
    "baixar_pdf": true,
    "baixar_xml": false
}
```

**Resposta:**
```json
{
    "sucesso": true,
    "mensagem": "Processamento concluído",
    "resumo": {
        "total_alocacoes": 50,
        "sucesso": 48,
        "erros": 2,
        "taxa_sucesso": "96.0%"
    }
}
```

### Obter Resultados

```http
GET http://localhost:5000/api/resultados
```

### Validar Planilha (sem processar)

```http
POST http://localhost:5000/api/validar-planilha
Content-Type: application/json

{
    "caminho_planilha": "/caminho/para/planilha.xlsx",
    "tipo_separacao": "placa"
}
```

---

## 📊 Estrutura da Planilha

Sua planilha deve ter as seguintes colunas:

| Coluna | Obrigatória | Exemplo | Descrição |
|--------|:-----------:|---------|-----------|
| **CHAVE** | ✓ | 35251247380171000157550020000825841972733416 | Chave de acesso (44 dígitos) |
| **Placa** | Se usar tipo_separacao=placa | SSV3J72 | Placa do veículo |
| **Identificador da rota** | Se usar tipo_separacao=rota | 26 GRU - BOM RETIRO | Identificador da rota |
| **Pedido** | ✓ | 147047 | Número do pedido |
| **NF** | ✓ | 82584 | Número da NF |
| **Cliente** | ✓ | OXXO PITTA | Nome do cliente |
| **Cidade** | ✓ | São Paulo | Cidade de entrega |
| Tipo cliente | - | Piloto Oxxo | Tipo de cliente |
| Bairro | - | Cachoeirinha | Bairro |
| Endereço | - | Rua Principal | Endereço |
| Cep | - | 01234-567 | CEP |
| Valor total pedido | - | 376.09 | Valor total |
| Qtd. caixas | - | 0 | Quantidade de caixas |
| Peso bruto pedido | - | 55.198 | Peso bruto |
| Distância calculado | - | 46102 | Distância |
| Código cliente | - | 26563652048597 | Código do cliente |

---

## ⚙️ Tipos de Separação

### 1. Por Placa (padrão)
```
output/2025-01-11_10-30-45/exemplo_de_planilha/placa/
├── SSV3J72/
├── XYZ9876/
└── ABC1234/
```

### 2. Por Rota
```
output/2025-01-11_10-30-45/exemplo_de_planilha/rota/
├── 26 GRU - BOM RETIRO/
├── 32 GRU - CENTRO/
└── 40 SJC - NORTE/
```

---

## 🎯 Exemplos de Uso

### JavaScript/Frontend

```javascript
// Conectar com API
const response = await fetch('http://localhost:5000/api/processar', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        caminho_planilha: 'C:\\Users\\feito\\Documents\\exemplo.xlsx',
        tipo_separacao: 'placa',
        baixar_pdf: true,
        baixar_xml: false
    })
});

const resultado = await response.json();
if (resultado.sucesso) {
    console.log(`✓ ${resultado.resumo.sucesso}/${resultado.resumo.total_alocacoes}`);
}
```

### Python

```python
from services.orquestrador import Orquestrador

orq = Orquestrador()
sucesso, resultados = orq.processar_planilha(
    "exemplo_de_planilha.xlsx",
    tipo_separacao="placa",
    baixar_pdf=True,
    baixar_xml=False
)

for r in orq.obter_resumo()['resultados']:
    print(f"{'✓' if r['sucesso'] else '✗'} {r['chave']}")
```

---

## 🐛 Troubleshooting

### ❌ "Api-Key não configurada"
- Abra o arquivo `.env` na raiz do projeto
- Certifique-se de que `API_KEY` está preenchida

### ❌ "Arquivo não encontrado"
- Use o caminho completo do arquivo
- Exemplo: `C:\Users\feito\Documents\exemplo.xlsx`
- Não use caminhos relativos

### ❌ "XML inválido"
- Se você estiver fornecendo XML manualmente
- Valide o XML em um editor XML online

### ❌ "Timeout nas requisições"
- Aumente `DELAY_BETWEEN_REQUESTS` no `.env`
- De: `DELAY_BETWEEN_REQUESTS=1.5` para `3.0`

### ❌ Muitos erros "429 - Too Many Requests"
- Você está enviando muitas requisições por segundo
- Aumente `DELAY_BETWEEN_REQUESTS` ainda mais

---

## 📁 Estrutura Completa do Projeto

```
UltraDanfeXML/
├── main.py                  # ← Executar aqui
├── api.py                   # API REST
├── config.py                # Configurações
├── .env                     # ← Adicione sua API_KEY aqui
├── requirements.txt
├── README.md
├── QUICK_START.md           # Este arquivo
│
├── models/
│   ├── alocacao.py
│   └── resposta_api.py
│
├── services/
│   ├── excel_reader.py
│   ├── xml_builder.py
│   ├── api_client.py
│   ├── gestor_saida.py
│   └── orquestrador.py
│
├── utils/
│   ├── logger.py
│   └── validators.py
│
├── logs/                    # Arquivos de log
├── output/                  # Arquivos processados ← Encontre aqui seus PDFs
└── exemplo_de_planilha.xlsx # Planilha de teste
```

---

## 💡 Dicas Úteis

1. **Testar conectividade**: `python -c "import requests; print(requests.get('https://api.meudanfe.com.br/v2').status_code)"`

2. **Validar planilha antes de processar**:
   ```bash
   python main.py exemplo_de_planilha.xlsx --validate-only
   ```

3. **Aumentar verbosidade de logs**: Altere em `.env`:
   ```
   LOG_LEVEL=DEBUG
   ```

4. **Encontrar arquivos processados**:
   - Windows Explorer: `output/`
   - Terminal: `python -c "from config import OUTPUT_DIR; print(OUTPUT_DIR)"`

---

## 📞 Próximos Passos

1. ✅ Adicione sua API_KEY em `.env`
2. ✅ Execute `python main.py --api` para iniciar servidor
3. ✅ Conecte seu frontend em `http://localhost:5000`
4. ✅ Comece a processar planilhas!

**Dúvidas sobre a API Meu Danfe?**
- Documentação: https://api.meudanfe.com.br
- Área do Cliente: https://www.meudanfe.com.br

---

**Versão:** 1.0.0  
**Data:** Janeiro 2025  
**Status:** ✓ Pronto para produção
