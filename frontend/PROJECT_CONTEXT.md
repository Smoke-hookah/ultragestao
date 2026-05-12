# Contexto do Projeto Ultra Danfe

## Visão Geral
Sistema web para processamento e gestão de notas fiscais eletrônicas (NF-e), integrado com a API MeuDanFE. O sistema permite processar notas em lote, individualmente, converter XML para PDF, gerenciar boletos de clientes e visualizar histórico de processamentos.

## Tecnologias Utilizadas
- **Framework**: React 18.3.1 com TypeScript
- **Build Tool**: Vite
- **Estilização**: Tailwind CSS com sistema de design tokens semânticos
- **Componentes UI**: Shadcn/ui (Radix UI)
- **Roteamento**: React Router DOM v6
- **State Management**: React Query (TanStack Query)
- **Ícones**: Lucide React
- **Formulários**: React Hook Form + Zod
- **Notificações**: Sonner + Shadcn Toast

## Estrutura do Projeto

### Páginas Principais

#### 1. Dashboard (`/`)
- **Arquivo**: `src/pages/Dashboard.tsx`
- **Funcionalidade**: Página inicial com visão geral do sistema
- **Componentes**:
  - Cards de estatísticas (notas processadas, taxa de sucesso, clientes, valor total)
  - Lista de processamentos recentes
  - Status do sistema (API, armazenamento)
  - Informações de backup
- **Estado**: Usa dados mockados para demonstração

#### 2. Processar Lote (`/processar`)
- **Arquivo**: `src/pages/ProcessarLote.tsx`
- **Funcionalidade**: Upload e processamento em lote via planilha Excel
- **Recursos**:
  - Upload de arquivo Excel
  - Configurações de processamento (download automático de DANFE, XML, envio por email)
  - Filtros avançados (placas, rotas, clientes)
  - Barra de progresso durante processamento
  - Download de relatório após conclusão
- **Estado**: Gerencia file, processing, progress

#### 3. Nota Individual (`/individual`)
- **Arquivo**: `src/pages/Individual.tsx`
- **Funcionalidade**: Processamento de NF-e individual por chave de acesso
- **Recursos**:
  - Input de chave de acesso (44 dígitos)
  - Validação automática da chave
  - Extração de informações (UF, Ano/Mês, CNPJ, Modelo, Número)
  - Download individual de DANFE (PDF), XML ou ambos
  - Instruções de uso
- **Estado**: Gerencia chave, validating, valid

#### 4. Gestão de Boletos (`/boletos`)
- **Arquivo**: `src/pages/Boletos.tsx`
- **Funcionalidade**: Controle de clientes com/sem boletos
- **Recursos**:
  - Cards de estatísticas (com boleto, sem boleto, total)
  - Busca/filtro de clientes
  - Toggle de status de boleto por cliente
  - Botões de ação (importar planilha, exportar base, adicionar cliente)
  - Lista com informações de última atualização
- **Estado**: Gerencia searchTerm e dados mockados de clientes

#### 5. Converter XML (`/converter`)
- **Arquivo**: `src/pages/Converter.tsx`
- **Funcionalidade**: Conversão em lote de XML para PDF (DANFE)
- **Recursos**:
  - Upload múltiplo de arquivos XML
  - Lista de arquivos selecionados com tamanho
  - Barra de progresso durante conversão
  - Explicação do processo em 4 etapas
- **Estado**: Gerencia files, converting, progress

#### 6. Histórico (`/historico`)
- **Arquivo**: `src/pages/Historico.tsx`
- **Funcionalidade**: Visualização de histórico de processamentos
- **Recursos**:
  - Cards de resumo (total processamentos, total notas, taxa de sucesso)
  - Lista de processamentos recentes com detalhes
  - Informações por item (tipo, data, rotas, notas, sucessos/erros)
  - Botões de ação (ver detalhes, baixar relatório)
- **Estado**: Usa dados mockados

#### 7. Not Found (`/404`)
- **Arquivo**: `src/pages/NotFound.tsx`
- **Funcionalidade**: Página de erro 404
- **Recursos**: Mensagem de erro e link para retorno ao início

### Layout e Navegação

#### Layout Principal
- **Arquivo**: `src/pages/Layout.tsx`
- **Estrutura**:
  - Sidebar colapsável
  - Header fixo com status do sistema
  - Área de conteúdo principal (Outlet)
- **Estado**: Gerencia collapsed state do sidebar

#### Sidebar
- **Arquivo**: `src/components/Sidebar.tsx`
- **Funcionalidades**:
  - Navegação principal com 6 itens
  - Modo colapsado/expandido com animações
  - Logo responsivo (muda tamanho conforme estado)
  - Versão desktop (lateral fixa) e mobile (Sheet)
  - Highlight de rota ativa
  - Informações de versão e integração API
- **Itens de Navegação**:
  1. Dashboard (LayoutDashboard)
  2. Processar Lote (FileUp)
  3. Nota Individual (FileText)
  4. Gestão de Boletos (DollarSign)
  5. Converter XML (FileX2)
  6. Histórico (History)

### Componentes Compartilhados

#### StatsCard
- **Arquivo**: `src/components/StatsCard.tsx`
- **Props**: title, value, icon, description, trend
- **Uso**: Cards de estatísticas no Dashboard e Histórico

### Sistema de Design

#### Tokens de Cor (HSL)
Definidos em `src/index.css`:
- **Primary**: Cor principal da marca
- **Secondary**: Cor secundária
- **Success**: Verde para sucessos
- **Destructive**: Vermelho para erros
- **Muted**: Cinza claro para elementos secundários
- **Accent**: Cor de destaque
- **Background/Foreground**: Cores base
- **Card**: Cores para cards
- **Sidebar**: Cores específicas do sidebar

#### Gradientes e Sombras
- `--gradient-primary`: Gradiente primário
- `--gradient-success`: Gradiente de sucesso
- `--shadow-card`: Sombra para cards
- `--shadow-elevated`: Sombra elevada

#### Configuração Tailwind
- **Arquivo**: `tailwind.config.ts`
- Extensões de cores usando tokens HSL
- Background images para gradientes
- Box shadows personalizadas
- Border radius baseado em variável CSS
- Animações (accordion-down, accordion-up)

### Componentes UI (Shadcn)
Localizados em `src/components/ui/`:
- **Formulários**: button, input, textarea, label, checkbox, radio-group, select, switch, slider
- **Feedback**: toast, alert, alert-dialog, progress, skeleton, sonner
- **Layout**: card, separator, tabs, accordion, collapsible, sheet, dialog, drawer
- **Navegação**: navigation-menu, menubar, breadcrumb, pagination
- **Dados**: table, calendar, chart, badge
- **Outros**: avatar, tooltip, popover, hover-card, dropdown-menu, context-menu, scroll-area

### Roteamento
- **Arquivo**: `src/App.tsx`
- **Estrutura**:
  ```
  / (Layout)
    ├─ / (Dashboard)
    ├─ /processar (ProcessarLote)
    ├─ /individual (Individual)
    ├─ /boletos (Boletos)
    ├─ /converter (Converter)
    └─ /historico (Historico)
  /* (NotFound)
  ```

### Utilitários
- **Arquivo**: `src/lib/utils.ts`
- Função `cn()`: Merge de classes Tailwind com clsx e tailwind-merge

### Hooks Customizados
- `use-mobile.tsx`: Detecta se está em dispositivo mobile
- `use-toast.ts`: Gerenciamento de notificações toast

### Assets
- **Logo**: `src/assets/logo.png` - Logo da Ultra Danfe (https://ultrapao.com.br/imagens/logo.png)

## Fluxos de Usuário

### Fluxo 1: Processar Lote
1. Usuário acessa `/processar`
2. Faz upload de planilha Excel
3. Configura opções de processamento
4. Define filtros avançados (opcional)
5. Clica em "Iniciar Processamento"
6. Visualiza progresso em tempo real
7. Baixa relatório ao final

### Fluxo 2: Nota Individual
1. Usuário acessa `/individual`
2. Insere chave de acesso de 44 dígitos
3. Sistema valida automaticamente
4. Visualiza informações extraídas
5. Escolhe formato para download (DANFE/XML/Ambos)
6. Realiza download

### Fluxo 3: Gestão de Boletos
1. Usuário acessa `/boletos`
2. Visualiza estatísticas de clientes
3. Busca cliente específico (opcional)
4. Adiciona/remove status de boleto
5. Exporta ou importa dados

### Fluxo 4: Conversão XML
1. Usuário acessa `/converter`
2. Seleciona múltiplos arquivos XML
3. Visualiza lista de arquivos
4. Clica em "Converter para PDF"
5. Acompanha progresso
6. Recebe arquivos convertidos

## Integrações Externas
- **API MeuDanFE**: API externa para processamento de notas fiscais (mencionada mas não implementada)
- Todos os processamentos atualmente usam dados mockados

## Estado da Aplicação
- **Dados mockados**: Todas as páginas usam dados estáticos para demonstração
- **Sem backend**: Não há integração real com APIs
- **Sem autenticação**: Sistema aberto sem login
- **Sem persistência**: Dados não são salvos

## Melhorias Futuras Sugeridas
1. Integração real com API MeuDanFE
2. Sistema de autenticação
3. Banco de dados para persistência
4. Upload real de arquivos
5. Processamento backend de notas
6. Relatórios em PDF
7. Sistema de notificações por email
8. Dashboard com dados reais/dinâmicos
9. Filtros avançados funcionais
10. Paginação nas listas

## Padrões de Código
- **Componentes funcionais** com TypeScript
- **Hooks** para gerenciamento de estado
- **Semantic tokens** para cores (nunca usar cores diretas)
- **Mobile-first** e responsivo
- **Acessibilidade** (aria-labels, semantic HTML)
- **SEO** (meta tags, títulos, descrições)
- **Componentização** (pequenos e focados)

## Comandos Úteis
```bash
# Desenvolvimento
npm run dev

# Build
npm run build

# Preview
npm run preview

# Lint
npm run lint
```

## Observações Importantes
- Sistema focado em gestão de notas fiscais eletrônicas
- Design limpo e profissional
- Interface intuitiva e responsiva
- Feedback visual constante (toasts, progress bars)
- Status do sistema sempre visível
- Dados mockados aguardando integração real
