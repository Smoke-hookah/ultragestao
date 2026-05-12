# Frontend UltraDanfeXML

Frontend React/Vite da tela `Processar em Lote`.

## Fluxo atual

- O frontend de desenvolvimento roda em `http://localhost:8080`.
- As chamadas `"/api/*"` usam proxy para o Flask em `http://localhost:5000`.
- O build de produção é gerado em `../static/dist` e servido pelo Flask.
- A aplicação atual tem uma única página útil: [`src/pages/ProcessarLote.tsx`](./src/pages/ProcessarLote.tsx).

## Comandos

```bash
npm install
npm run dev
npm run build
npm run lint
```

## Observações

- `npm run build` atualiza os assets que o backend serve no modo standalone/API.
- O `README` antigo do template Lovable foi removido porque não descrevia mais este projeto.
