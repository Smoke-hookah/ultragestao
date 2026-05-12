# UltraDanfeXML

Processador local de planilhas de alocacao com foco em um unico fluxo operacional:

- ler a planilha;
- localizar XMLs por chave;
- enviar ou baixar documentos pela API Meu Danfe quando necessario;
- gerar DANFE local em modo offline;
- separar boletos por PDF usando `pypdf + Docling`;
- organizar a saida por rota ou placa.

Hoje a aplicacao util e composta por:

- backend Flask em [`api.py`](./api.py);
- orquestracao principal em [`services/orquestrador.py`](./services/orquestrador.py);
- frontend React/Vite de uma unica tela em [`frontend/src/pages/ProcessarLote.tsx`](./frontend/src/pages/ProcessarLote.tsx);
- empacotamento standalone via PyInstaller em [`build_exe.py`](./build_exe.py).

## Fluxo atual

1. O usuario envia uma planilha para `/api/planilha-filtros`.
2. O backend le a planilha, devolve filtros e guarda um `planilha_token` temporario.
3. Opcionalmente, o frontend pode rodar a nova etapa `Extrair do Protheus`, que usa o subset filtrado da planilha, gera um `coleta_token` e persiste XMLs/PDF de boletos em staging.
4. O frontend chama `/api/processar-local` com o `planilha_token` e, quando existir, tambem com o `coleta_token`.
5. O orquestrador:
   - valida as linhas;
   - tenta localizar XMLs na pasta configurada;
   - ou reutiliza XMLs e boletos coletados do Protheus via staging;
   - usa API, geracao local ou fallback local conforme `metodo_pdf`;
   - separa boletos quando um PDF de boletos e enviado;
   - grava a saida em `output/<timestamp>/<tipo>/<grupo>/`.

## Endpoints reais

Os endpoints ativos hoje sao:

- `GET /api/progresso`
- `GET /api/ui/protheus-config`
- `GET /api/ui/pasta-xmls`
- `POST /api/ui/protheus-credenciais`
- `POST /api/ui/protheus-config`
- `POST /api/ui/pasta-xmls/set`
- `POST /api/ui/pasta-xmls/selecionar`
- `POST /api/ui/abrir-pasta`
- `POST /api/planilha-filtros`
- `POST /api/protheus/extrair`
- `POST /api/processar-local`

Os endpoints antigos `/api/status`, `/api/config`, `/api/processar`, `/api/resumo`, `/api/resultados` e `/api/validar-planilha` nao fazem mais parte do contrato atual.

## Requisitos

- Python 3.10+
- Node.js 18+
- Windows e o alvo principal do fluxo standalone

## Instalacao

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
cd frontend
npm install
cd ..
```

Crie `.env` a partir de `.env.example`.

Campos mais importantes:

```env
API_URL=https://api.meudanfe.com.br/v2
API_KEY=sua_api_key

# Opcional: multiplas chaves
# API_KEYS=key1,key2,key3

# Permite rodar smoke tests locais sem API
# ALLOW_NO_API_KEYS=1

MAX_UPLOAD_MB=2048
MAX_FORM_PARTS=20000
```

## Execucao

### Backend

```powershell
.\.venv\Scripts\python.exe main.py --api
```

Servidor padrao: `http://localhost:5000`

### Frontend de desenvolvimento

```powershell
cd frontend
npm run dev
```

Frontend padrao: `http://localhost:8080`

O Vite faz proxy de `"/api/*"` para o Flask local.

### Executavel standalone

```powershell
.\.venv\Scripts\python.exe build_exe.py
```

Saida esperada: `UltraDanfeXML_Portable/UltraDanfeXML.exe`

O build standalone agora:

- nao embute `.env` no bundle;
- copia `.env.example` para a pasta portatil;
- prepara e valida um `Chromium` empacotado em `playwright-browsers/` para a automacao Protheus;
- persiste preferencias e historicos em `config/`;
- grava saida em `output/` e logs em `logs/`, ao lado do `.exe`.

Se quiser usar a API Meu Danfe no executavel, coloque um `.env` externo ao lado do `.exe`.
Sem `.env`, o app ainda sobe em modo local para fluxos que nao dependem de `API_KEY/API_KEYS`.

## Modos de PDF

- `api`: faz PUT/GET na API Meu Danfe.
- `local`: gera DANFE a partir do XML local.
- `api_fallback_local`: tenta a API e, se falhar, gera localmente.

No modo `local`, o projeto agora escolhe automaticamente o executor para o lote:

- lotes pequenos usam `thread pool`;
- lotes grandes podem usar `process pool` para acelerar a geracao em CPU;
- voce pode forcar o comportamento com `LOCAL_PDF_EXECUTOR=thread|process|auto`;
- voce pode limitar concorrencia com `LOCAL_PDF_WORKERS=<n>`.

## Coleta Protheus

O v1 da automacao usa browser embutido com Playwright + Chromium e credenciais salvas no Windows Credential Manager.

Fluxo:

1. carregar a planilha e os filtros;
2. configurar `base_url`, `usuario` e o mapa `UF=filial`;
3. salvar a senha do Protheus;
4. executar `Extrair do Protheus`;
5. revisar o `coleta_token`, as contagens e os caminhos de staging;
6. processar normalmente, agora sem depender de pasta XML manual ou upload manual de boletos para essa execucao.

Contrato novo:

- `GET /api/ui/protheus-config`: retorna configuracao publica e campos pendentes.
- `POST /api/ui/protheus-config`: grava `base_url`, `protheus_user` e `uf_branch_map`.
- `POST /api/ui/protheus-credenciais`: grava usuario/senha no Credential Manager do Windows.
- `POST /api/protheus/extrair`: executa a coleta do subset filtrado e devolve `review.coleta_token`.
- `POST /api/processar-local`: aceita `coleta_token`; quando presente, usa o staging do Protheus e ignora XML/PDF manual nessa execucao.

## Estrutura de runtime

No modo desenvolvimento:

- `config/`
- `logs/`
- `output/`

No modo standalone:

- `UltraDanfeXML_Portable/config/`
- `UltraDanfeXML_Portable/logs/`
- `UltraDanfeXML_Portable/output/`

## Estrutura de saida

```text
output/
  2026-04-30_00-36-21/
    rota/
      26 GRU - BOM RETIRO/
        pdf/
        xml/
```

Durante uploads e processamentos o backend cria diretorios temporarios `ultradanfe_filtros_*` e `ultradanfe_local_*`.
Esses diretorios agora sao removidos ao final do fluxo e tambem passam por limpeza por TTL.

## Testes e validacao

### Smoke tests automatizados

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

### Smoke tests manuais

Com backend em execucao:

```powershell
.\.venv\Scripts\python.exe test_api.py
.\.venv\Scripts\python.exe test_frontend_flow.py
```

### Validacoes de frontend

```powershell
cd frontend
npm run lint
npm run build
```

## Estado da documentacao

Este README foi ajustado para o contrato vivo do projeto. Se o fluxo mudar, atualize primeiro:

- os endpoints documentados aqui;
- `test_api.py`;
- `test_frontend_flow.py`;
- `tests/`.
