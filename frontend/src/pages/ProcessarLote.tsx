import { useEffect, useMemo, useRef, useState } from "react";
import { API_URL } from "@/config";
import {
  Upload,
  Play,
  FileText,
  CheckCircle2,
  XCircle,
  Receipt,
  History,
  TrendingUp,
  FolderOpen,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { MultiSelect, type MultiSelectOption } from "@/components/MultiSelect";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Checkbox } from "@/components/ui/checkbox";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

type BoletoMatchResumo = {
  chave?: string;
  nf?: string;
  cliente?: string;
  score?: number;
  suffix?: number;
  motivos?: string[];
};

type BoletoMatchDebug = {
  doc_digits?: string | null;
  doc_candidates?: string[];
  melhor?: BoletoMatchResumo | null;
  segundo?: BoletoMatchResumo | null;
};

type BoletoListaItem = {
  chave: string;
  nf?: string;
  cliente?: string;
  paginas?: number[];
  doc_digits?: string | null;
  doc_candidates?: string[];
  pagador?: string | null;
  pagador_cnpj?: string | null;
  valor_documento?: number | null;
  match_debug?: BoletoMatchDebug | null;
};

type BoletoPdfProblema = {
  doc: string;
  motivo: string;
  paginas?: number;
  doc_digits?: string | null;
  doc_candidates?: string[];
  pagador?: string | null;
  pagador_cnpj?: string | null;
  valor_documento?: number | null;
  match_debug?: BoletoMatchDebug | null;
};

type ApiResumo = {
  total_alocacoes: number;
  sucesso: number;
  erros: number;
  taxa_sucesso: string;
  caminho_saida_base?: string;
  execucao_timestamp?: string;
  boletos?: {
    // PDF de boletos (denominador)
    pdf_total_documentos?: number;
    pdf_paginas_nao_identificadas?: number;
    pdf_separados?: number;
    pdf_sem_correspondencia?: number;
    pdf_ambiguos?: number;
    pdf_sem_nf?: number;
    pdf_falha_salvar?: number;
    pdf_ok?: boolean;
    pdf_extracao_cache_hit?: boolean;
    pdf_source_hash?: string | null;
    pdf_problemas?: BoletoPdfProblema[];

    // Apenas chaves esperadas pelo PDF (PDF -> planilha)
    esperados_total?: number;
    anexados_total?: number;
    anexados_pdf?: number;
    anexados_historico?: number;
    faltando_total?: number;
    todos_ok?: boolean;
    faltando?: BoletoListaItem[];
    do_historico?: BoletoListaItem[];
    do_pdf?: BoletoListaItem[];
  } | null;
  resultados: Array<{
    chave: string;
    nf?: string;
    cliente?: string;
    sucesso: boolean;
    etapa: string;
    mensagem: string;
    arquivo_pdf?: string | null;
    arquivo_xml?: string | null;
  }>;
};

type ApiProgresso = {
  processamento_ativo?: boolean;
  etapa?: string;
  percentual?: number;
  mensagem?: string;
  detalhes?: string;
};

type ApiFiltros = {
  sucesso: boolean;
  mensagem?: string;
  rotas?: string[];
  placas?: string[];
  clientes?: string[];
  rota_clientes?: Record<string, string[]>;
  placa_clientes?: Record<string, string[]>;
  total_alocacoes?: number;
  planilha_token?: string;
};

type ProtheusConfig = {
  base_url: string;
  selector_version: number;
  protheus_user: string;
  uf_branch_map: Record<string, string>;
  has_password: boolean;
  config_path: string;
  advanced_config_ready: boolean;
  pending_fields: string[];
};

type ProtheusReview = {
  coleta_token: string;
  uf: string;
  branch_code: string;
  subset_total: number;
  nf_range: {
    inicio: string;
    fim: string;
  };
  xml: {
    esperados: number;
    encontrados: number;
    extras_ignorados: number;
    ausentes: number;
    staging_dir: string;
    processing_dir: string;
  };
  boletos: {
    pdf_disponivel: boolean;
    pdf_path?: string | null;
  };
  paths: {
    staging_root: string;
    diagnostics_dir: string;
    config_path?: string | null;
  };
  pending_fields: string[];
  failures: string[];
  ready_for_processing: boolean;
};

type CoverageRouteResumo = {
  rota: string;
  esperadas: number;
  com_xml: number;
  com_pdf: number;
  faltantes: number;
};

type CoverageItem = {
  chave: string;
  nf?: string;
  rota?: string;
  placa?: string;
  cliente?: string;
  xml_status:
    | "found_local"
    | "recovered_protheus"
    | "missing"
    | "duplicate"
    | "non_renderable"
    | "invalid_key";
  pdf_status: "ready" | "generated_api" | "generated_local_fallback" | "missing";
  source?: string | null;
  reason?: string;
};

type CoverageReview = {
  coverage_token: string;
  ready_for_processing: boolean;
  totals: {
    esperadas: number;
    validas: number;
    com_xml: number;
    com_pdf: number;
    encontradas_local: number;
    recuperadas_protheus: number;
    faltantes: number;
    invalidas: number;
    duplicadas: number;
    nao_renderizaveis: number;
  };
  routes: CoverageRouteResumo[];
  items: CoverageItem[];
  failures: string[];
  paths: {
    staging_root: string;
    processing_xml_dir: string;
    planilha_path: string;
    boleto_pdf_path?: string | null;
  };
  metodo_pdf: {
    requested: string;
    resolved: string;
  };
  recovery_reviews?: ProtheusReview[];
};

const formatadorMoeda = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});

const limparValores = (values?: Array<string | null | undefined>) =>
  Array.from(
    new Set(
      (values ?? [])
        .map((value) => String(value ?? "").trim())
        .filter(Boolean),
    ),
  );

const formatPaginas = (paginas?: number[]) => {
  if (!paginas?.length) return "-";
  return paginas.join(", ");
};

const formatValorDocumento = (valor?: number | null) => {
  if (typeof valor !== "number" || Number.isNaN(valor)) return null;
  return formatadorMoeda.format(valor);
};

const resumirHash = (hash?: string | null, maxLen = 14) => {
  const value = String(hash ?? "").trim();
  if (!value) return null;
  if (value.length <= maxLen) return value;
  return `${value.slice(0, 8)}...${value.slice(-4)}`;
};

const responsePath = (response: Response) => {
  try {
    return new URL(response.url).pathname || response.url;
  } catch {
    return response.url || "rota desconhecida";
  }
};

const parseApiPayload = async <T,>(response: Response): Promise<T | null> => {
  const raw = await response.text();
  if (!raw) return null;

  const contentType = String(response.headers.get("content-type") || "").toLowerCase();
  const trimmed = raw.trim();

  if (contentType.includes("application/json")) {
    try {
      return JSON.parse(trimmed) as T;
    } catch {
      throw new Error(`A API retornou JSON invalido em ${responsePath(response)}.`);
    }
  }

  if (trimmed.startsWith("<!doctype") || trimmed.startsWith("<html")) {
    const path = responsePath(response);
    if (path.includes("/api/ui/protheus")) {
      throw new Error(
        `A API respondeu HTML em ${path} (HTTP ${response.status}). O backend em :5000 provavelmente esta desatualizado. Reinicie a API atual ou gere um novo EXE.`,
      );
    }
    throw new Error(`A API respondeu HTML em ${path} (HTTP ${response.status}).`);
  }

  try {
    return JSON.parse(trimmed) as T;
  } catch {
    return { mensagem: trimmed } as T;
  }
};

const branchMapToText = (value?: Record<string, string> | null) =>
  Object.entries(value || {})
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([uf, branch]) => `${uf}=${branch}`)
    .join("\n");

const parseBranchMapText = (value: string) => {
  const result: Record<string, string> = {};
  for (const rawLine of value.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line) continue;
    const parts = line.split(/[:=]/, 2);
    const uf = String(parts[0] || "").trim().toUpperCase();
    const branch = String(parts[1] || "").trim();
    if (uf && branch) {
      result[uf] = branch;
    }
  }
  return result;
};

const normalizeSignatureList = (values: string[]) => limparValores(values).sort((a, b) => a.localeCompare(b));

const coverageXmlStatusLabel: Record<CoverageItem["xml_status"], string> = {
  found_local: "Local",
  recovered_protheus: "Recuperado",
  missing: "Faltante",
  duplicate: "Duplicado",
  non_renderable: "Nao renderizavel",
  invalid_key: "Chave invalida",
};

const coveragePdfStatusLabel: Record<CoverageItem["pdf_status"], string> = {
  ready: "Pronto",
  generated_api: "Gerado via API",
  generated_local_fallback: "Fallback local",
  missing: "Pendente",
};

const termosBuscaMatch = (match?: BoletoMatchDebug | null) => {
  const melhor = match?.melhor;
  const segundo = match?.segundo;
  return [
    match?.doc_digits,
    ...(match?.doc_candidates ?? []),
    melhor?.nf,
    melhor?.cliente,
    ...(melhor?.motivos ?? []),
    segundo?.nf,
    segundo?.cliente,
    ...(segundo?.motivos ?? []),
  ]
    .filter(Boolean)
    .join(" ");
};

const resumoMatch = (match?: BoletoMatchResumo | null) => {
  if (!match) return null;
  const motivos = limparValores(match.motivos);
  return {
    nf: match.nf || "-",
    cliente: match.cliente || "-",
    score: typeof match.score === "number" ? match.score : null,
    suffix: typeof match.suffix === "number" ? match.suffix : null,
    motivos,
  };
};

const renderResumoMatch = (label: string, match?: BoletoMatchResumo | null) => {
  const resumo = resumoMatch(match);
  if (!resumo) return null;

  return (
    <div className="rounded-md border border-border/60 bg-muted/30 px-2 py-1.5">
      <div className="flex flex-wrap items-center gap-1">
        <span className="font-medium text-foreground">{label}</span>
        {resumo.score !== null ? (
          <Badge variant="outline" className="h-5 px-1.5 text-[11px] font-normal">
            score {resumo.score}
          </Badge>
        ) : null}
        {resumo.suffix !== null && resumo.suffix > 0 ? (
          <Badge variant="outline" className="h-5 px-1.5 text-[11px] font-normal">
            sufixo {resumo.suffix}
          </Badge>
        ) : null}
      </div>
      <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
        <span className="font-mono">{resumo.nf}</span>
        {resumo.cliente !== "-" ? <span className="break-words">{resumo.cliente}</span> : null}
      </div>
      {resumo.motivos.length ? (
        <div className="mt-1 flex flex-wrap gap-1">
          {resumo.motivos.map((motivo) => (
            <Badge key={`${label}-${motivo}`} variant="outline" className="h-5 px-1.5 text-[11px] font-normal">
              {motivo}
            </Badge>
          ))}
        </div>
      ) : null}
    </div>
  );
};

const renderBoletoAuditoria = (
  item: {
    doc_digits?: string | null;
    doc_candidates?: string[];
    pagador?: string | null;
    pagador_cnpj?: string | null;
    valor_documento?: number | null;
    match_debug?: BoletoMatchDebug | null;
  },
  emptyLabel = "Sem sinais extras",
) => {
  const docs = limparValores([item.doc_digits, ...(item.doc_candidates ?? [])]);
  const valor = formatValorDocumento(item.valor_documento);
  const melhor = renderResumoMatch("Melhor match", item.match_debug?.melhor);
  const segundo = renderResumoMatch("Segundo match", item.match_debug?.segundo);
  const hasMeta = docs.length || item.pagador || item.pagador_cnpj || valor;

  if (!hasMeta && !melhor && !segundo) {
    return <span className="text-xs text-muted-foreground">{emptyLabel}</span>;
  }

  return (
    <div className="space-y-1.5 text-xs">
      {docs.length ? (
        <div className="flex flex-wrap items-center gap-1">
          <span className="text-muted-foreground">Doc:</span>
          <span className="font-mono break-all">{docs.join(", ")}</span>
        </div>
      ) : null}
      {item.pagador ? (
        <div className="flex flex-wrap items-center gap-1">
          <span className="text-muted-foreground">Pagador:</span>
          <span className="break-words">{item.pagador}</span>
        </div>
      ) : null}
      {item.pagador_cnpj ? (
        <div className="flex flex-wrap items-center gap-1">
          <span className="text-muted-foreground">CNPJ:</span>
          <span className="font-mono">{item.pagador_cnpj}</span>
        </div>
      ) : null}
      {valor ? (
        <div className="flex flex-wrap items-center gap-1">
          <span className="text-muted-foreground">Valor:</span>
          <span>{valor}</span>
        </div>
      ) : null}
      {melhor}
      {segundo}
    </div>
  );
};

export default function ProcessarLote() {
  const [planilhaFile, setPlanilhaFile] = useState<File | null>(null);
  const [planilhaToken, setPlanilhaToken] = useState<string | null>(null);
  const [coletaToken, setColetaToken] = useState<string | null>(null);
  const [coverageToken, setCoverageToken] = useState<string | null>(null);
  const [boletosPdfFile, setBoletosPdfFile] = useState<File | null>(null);
  const [pastaXmls, setPastaXmls] = useState<string | null>(null);
  const [pastaXmlsEdit, setPastaXmlsEdit] = useState<string>("");
  const [tipoSeparacao, setTipoSeparacao] = useState<"placa" | "rota">("placa");
  const [baixarPdf, setBaixarPdf] = useState(true);
  const [baixarXml, setBaixarXml] = useState(false);
  const [juntarPdfs, setJuntarPdfs] = useState(true);
  const [separarEmPastas, setSepararEmPastas] = useState(true);
  const [metodoPdf, setMetodoPdf] = useState<"api" | "local" | "api_fallback_local">("api");

  const [filtrosCarregando, setFiltrosCarregando] = useState(false);
  const [opRotas, setOpRotas] = useState<string[]>([]);
  const [opPlacas, setOpPlacas] = useState<string[]>([]);
  const [opClientes, setOpClientes] = useState<string[]>([]);
  const [rotaClientes, setRotaClientes] = useState<Record<string, string[]>>({});
  const [placaClientes, setPlacaClientes] = useState<Record<string, string[]>>({});
  const [protheusConfig, setProtheusConfig] = useState<ProtheusConfig | null>(null);
  const [protheusBaseUrl, setProtheusBaseUrl] = useState("");
  const [protheusUser, setProtheusUser] = useState("");
  const [protheusPassword, setProtheusPassword] = useState("");
  const [protheusUfMapText, setProtheusUfMapText] = useState("MG=0202\nRJ=0101\nSP=0201");
  const [protheusUf, setProtheusUf] = useState("MG");
  const [protheusExtraindo, setProtheusExtraindo] = useState(false);
  const [protheusSalvandoConfig, setProtheusSalvandoConfig] = useState(false);
  const [protheusSalvandoCredenciais, setProtheusSalvandoCredenciais] = useState(false);
  const [protheusReview, setProtheusReview] = useState<ProtheusReview | null>(null);
  const [coverageValidando, setCoverageValidando] = useState(false);
  const [coverageReview, setCoverageReview] = useState<CoverageReview | null>(null);
  const [coverageResolvedSignature, setCoverageResolvedSignature] = useState<string | null>(null);
  const autoCoverageTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const validarCoberturaRef = useRef<
    ((options?: { silent?: boolean; tokenOverride?: string | null; signatureOverride?: string | null }) => Promise<void>) | null
  >(null);

  const [selRotas, setSelRotas] = useState<string[]>([]);
  const [selPlacas, setSelPlacas] = useState<string[]>([]);
  const [selClientes, setSelClientes] = useState<string[]>([]);
const [processing, setProcessing] = useState(false);
const [progress, setProgress] = useState(0);
const [progressoInfo, setProgressoInfo] = useState<ApiProgresso | null>(null);
const [resumo, setResumo] = useState<ApiResumo | null>(null);
const [relatorioOpen, setRelatorioOpen] = useState(false);
const [coverageRoutesOpen, setCoverageRoutesOpen] = useState(false);
  const { toast } = useToast();

  const [qFalhas, setQFalhas] = useState("");
  const [qBoletosFaltando, setQBoletosFaltando] = useState("");
  const [qBoletosHistorico, setQBoletosHistorico] = useState("");
  const [qBoletosPdfProblemas, setQBoletosPdfProblemas] = useState("");
  const [qBoletosPdfSeparados, setQBoletosPdfSeparados] = useState("");

  const truncarMeio = (texto: string, maxLen = 64) => {
    const s = String(texto);
    if (s.length <= maxLen) return s;
    const keepStart = Math.max(16, Math.floor(maxLen * 0.55));
    const keepEnd = Math.max(12, maxLen - keepStart - 1);
    return `${s.slice(0, keepStart)}â€¦${s.slice(-keepEnd)}`;
  };

  const relatorio = useMemo(() => {
    const cmp = (a?: unknown, b?: unknown) =>
      String(a ?? "").localeCompare(String(b ?? ""), undefined, {
        numeric: true,
        sensitivity: "base",
      });

    const falhas = (resumo?.resultados?.filter((r) => !r.sucesso) ?? [])
      .slice()
      .sort((a, b) => cmp(a.nf, b.nf) || cmp(a.cliente, b.cliente) || cmp(a.chave, b.chave));
    const boletos = resumo?.boletos ?? null;
    const boletosFaltando = (boletos?.faltando ?? []).slice().sort((a, b) => cmp(a.nf, b.nf) || cmp(a.cliente, b.cliente));
    const boletosHistorico = (boletos?.do_historico ?? [])
      .slice()
      .sort((a, b) => cmp(a.nf, b.nf) || cmp(a.cliente, b.cliente));
    const boletosPdfSeparados = (boletos?.do_pdf ?? [])
      .slice()
      .sort((a, b) => cmp(a.nf, b.nf) || cmp(a.cliente, b.cliente));
    const boletosPdfProblemas = (boletos?.pdf_problemas ?? [])
      .slice()
      .sort((a, b) => cmp(a.doc, b.doc) || cmp(a.motivo, b.motivo));
    const execucao = resumo?.execucao_timestamp ? String(resumo.execucao_timestamp).replace("_", " ") : null;
    const saida = resumo?.caminho_saida_base ?? null;
    const saidaCurta = saida ? truncarMeio(saida, 68) : null;

    return {
      falhas,
      boletos,
      boletosFaltando,
      boletosHistorico,
      boletosPdfSeparados,
      boletosPdfProblemas,
      execucao,
      saida,
      saidaCurta,
    };
  }, [resumo]);

  const relatorioFiltrado = useMemo(() => {
    const norm = (s: string) => s.trim().toLowerCase();

    const q1 = norm(qFalhas);
    const q2 = norm(qBoletosFaltando);
    const q3 = norm(qBoletosHistorico);
    const q4 = norm(qBoletosPdfProblemas);
    const q5 = norm(qBoletosPdfSeparados);

    const falhas = q1
      ? relatorio.falhas.filter((r) =>
          [r.nf, r.cliente, r.mensagem, r.etapa]
            .filter(Boolean)
            .some((v) => String(v).toLowerCase().includes(q1)),
        )
      : relatorio.falhas;

    const boletosFaltando = q2
      ? relatorio.boletosFaltando.filter((b) =>
          [
            b.nf,
            b.cliente,
            b.doc_digits,
            ...(b.doc_candidates ?? []),
            b.pagador,
            b.pagador_cnpj,
            termosBuscaMatch(b.match_debug),
          ]
            .filter(Boolean)
            .some((v) => String(v).toLowerCase().includes(q2)),
        )
      : relatorio.boletosFaltando;

    const boletosHistorico = q3
      ? relatorio.boletosHistorico.filter((b) =>
          [
            b.nf,
            b.cliente,
            b.doc_digits,
            ...(b.doc_candidates ?? []),
            b.pagador,
            b.pagador_cnpj,
            termosBuscaMatch(b.match_debug),
          ]
            .filter(Boolean)
            .some((v) => String(v).toLowerCase().includes(q3)),
        )
      : relatorio.boletosHistorico;

    const boletosPdfProblemas = q4
      ? relatorio.boletosPdfProblemas.filter((p) =>
          [
            p.doc,
            p.motivo,
            p.doc_digits,
            ...(p.doc_candidates ?? []),
            p.pagador,
            p.pagador_cnpj,
            termosBuscaMatch(p.match_debug),
          ]
            .filter(Boolean)
            .some((v) => String(v).toLowerCase().includes(q4)),
        )
      : relatorio.boletosPdfProblemas;

    const boletosPdfSeparados = q5
      ? relatorio.boletosPdfSeparados.filter((b) =>
          [
            b.nf,
            b.cliente,
            b.doc_digits,
            ...(b.doc_candidates ?? []),
            b.pagador,
            b.pagador_cnpj,
            termosBuscaMatch(b.match_debug),
          ]
            .filter(Boolean)
            .some((v) => String(v).toLowerCase().includes(q5)),
        )
      : relatorio.boletosPdfSeparados;

    return { falhas, boletosFaltando, boletosHistorico, boletosPdfProblemas, boletosPdfSeparados };
  }, [qBoletosFaltando, qBoletosHistorico, qBoletosPdfProblemas, qBoletosPdfSeparados, qFalhas, relatorio]);

  const hasPdfBoletos =
    (relatorio.boletos?.pdf_total_documentos ?? 0) > 0 ||
    (relatorio.boletos?.pdf_paginas_nao_identificadas ?? 0) > 0 ||
    (relatorio.boletos?.anexados_pdf ?? 0) > 0 ||
    (relatorio.boletos?.anexados_total ?? 0) > 0 ||
    (relatorio.boletos?.faltando_total ?? 0) > 0 ||
    (relatorio.boletos?.esperados_total ?? 0) > 0;

  const workflowBusy = processing || protheusExtraindo || coverageValidando;
  const coverageRequestSignature = useMemo(() => {
    if (!planilhaFile || !planilhaToken) return null;
    return JSON.stringify({
      planilha_token: planilhaToken,
      origem_xml: coletaToken ? `coleta:${coletaToken}` : `pasta:${String(pastaXmls ?? "").trim()}`,
      uf: String(protheusUf ?? "").trim().toUpperCase(),
      filtro_rotas: normalizeSignatureList(selRotas),
      filtro_placas: normalizeSignatureList(selPlacas),
      filtro_clientes: normalizeSignatureList(selClientes),
      baixar_pdf: Boolean(baixarPdf),
      metodo_pdf: baixarPdf ? metodoPdf : "skip",
    });
  }, [baixarPdf, coletaToken, metodoPdf, pastaXmls, planilhaFile, planilhaToken, protheusUf, selClientes, selPlacas, selRotas]);
  const coverageCanAutoValidate = Boolean(planilhaFile && planilhaToken && (coletaToken || pastaXmls) && !filtrosCarregando);
  const coverageReadyForCurrentInputs = Boolean(
    coverageReview?.ready_for_processing &&
      coverageRequestSignature &&
      coverageResolvedSignature === coverageRequestSignature,
  );
  const coverageStale = Boolean(
    coverageReview &&
      coverageRequestSignature &&
      coverageResolvedSignature &&
      coverageResolvedSignature !== coverageRequestSignature,
  );
  const protheusUfOptions = useMemo(
    () => Object.keys(parseBranchMapText(protheusUfMapText)).sort(),
    [protheusUfMapText],
  );
  const filtrosSelecionados = selRotas.length + selPlacas.length + selClientes.length;
  const origemXmlResumo = coletaToken
    ? "Usando staging da coleta Protheus."
    : pastaXmls
      ? `Base local salva em ${pastaXmls}.`
      : "Selecione a pasta de XMLs ou use a coleta Protheus.";
  const coverageStatusLabel = coverageValidando
    ? coverageReview
      ? "Atualizando cobertura"
      : "Validando cobertura"
    : coverageReview
      ? coverageStale
        ? "Revalidacao pendente"
        : coverageReview.ready_for_processing
          ? "Cobertura pronta"
          : "Cobertura bloqueada"
      : coverageCanAutoValidate
        ? "Aguardando validacao"
        : "Nao validada";
  const coveragePendencias = coverageReview
    ? coverageReview.totals.faltantes +
      coverageReview.totals.invalidas +
      coverageReview.totals.duplicadas +
      coverageReview.totals.nao_renderizaveis
    : 0;
  const coverageProblemItems = useMemo(
    () =>
      (coverageReview?.items || []).filter(
        (item) =>
          !["found_local", "recovered_protheus"].includes(item.xml_status) || item.pdf_status === "missing",
      ),
    [coverageReview],
  );
  const clienteOptionsFiltrados = useMemo(() => {
    if (selRotas.length > 0) {
      const values = new Set<string>();
      for (const rota of selRotas) {
        for (const cliente of rotaClientes[rota] || []) values.add(cliente);
      }
      return Array.from(values).sort((a, b) => a.localeCompare(b));
    }
    if (selPlacas.length > 0) {
      const values = new Set<string>();
      for (const placa of selPlacas) {
        for (const cliente of placaClientes[placa] || []) values.add(cliente);
      }
      return Array.from(values).sort((a, b) => a.localeCompare(b));
    }
    return [...opClientes].sort((a, b) => a.localeCompare(b));
  }, [opClientes, placaClientes, rotaClientes, selPlacas, selRotas]);

  const applyProtheusConfig = (config?: ProtheusConfig | null) => {
    if (!config) return;
    setProtheusConfig(config);
    setProtheusBaseUrl(config.base_url || "");
    setProtheusUser(config.protheus_user || "");
    setProtheusUfMapText(branchMapToText(config.uf_branch_map));

    const currentMap = config.uf_branch_map || {};
    const preferredUf =
      (protheusUf && currentMap[protheusUf] ? protheusUf : "") ||
      Object.keys(currentMap).sort()[0] ||
      "MG";
    setProtheusUf(preferredUf);
  };

  const pollProgresso = () =>
    setInterval(async () => {
      try {
        const progResp = await fetch(API_URL + "/api/progresso", { cache: "no-store" });
        const progData = ((await parseApiPayload<ApiProgresso>(progResp)) || {}) as ApiProgresso;
        setProgressoInfo(progData);

        const pct = typeof progData?.percentual === "number" ? progData.percentual : 0;
        if (pct > 0) setProgress(Math.min(pct, 99));
      } catch {
        // ignora falhas momentaneas
      }
    }, 500);

  const abrirPastaLocal = async (path: string, successTitle = "Pasta aberta") => {
    const response = await fetch(API_URL + "/api/ui/abrir-pasta", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path }),
    });
    const payload = await parseApiPayload<{ sucesso?: boolean; mensagem?: string }>(response);
    if (!response.ok || !payload?.sucesso) {
      throw new Error(payload?.mensagem || "Falha ao abrir a pasta");
    }
    toast({ title: successTitle, description: path });
  };

  const abrirPastaSaida = async () => {
    if (!relatorio.saida) return;
    try {
      await abrirPastaLocal(relatorio.saida, "Pasta de saida aberta");
    } catch {
      toast({
        title: "NÃ£o foi possÃ­vel abrir",
        description: "Falha ao abrir a pasta de saÃ­da.",
        variant: "destructive",
      });
    }
  };

  useEffect(() => {
    // Carregar a pasta de XML salva no backend
    (async () => {
      try {
        const r = await fetch(API_URL + "/api/ui/pasta-xmls");
        const j = await parseApiPayload<{ sucesso?: boolean; pasta_xmls?: string | null }>(r);
        if (r.ok && j?.sucesso) {
          const p = j.pasta_xmls || null;
          setPastaXmls(p);
          setPastaXmlsEdit(p || "");
        }
      } catch {
        // sem toast aqui para nÃ£o poluir a tela
      }
      try {
        const r = await fetch(API_URL + "/api/ui/protheus-config");
        const j = await parseApiPayload<{ sucesso?: boolean; config?: ProtheusConfig }>(r);
        if (r.ok && j?.sucesso && j.config) {
          applyProtheusConfig(j.config as ProtheusConfig);
        }
      } catch {
        // sem toast aqui para nao poluir a tela
      }
    })();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    // Ajustar clientes selecionados quando o escopo (rota/placa) mudar
    const allowed = new Set<string>();

    if (selRotas.length > 0) {
      for (const r of selRotas) for (const c of rotaClientes[r] || []) allowed.add(c);
    } else if (selPlacas.length > 0) {
      for (const p of selPlacas) for (const c of placaClientes[p] || []) allowed.add(c);
    } else {
      for (const c of opClientes) allowed.add(c);
    }

    if (selClientes.some((c) => !allowed.has(c))) {
      setSelClientes(selClientes.filter((c) => allowed.has(c)));
    }
  }, [selRotas, selPlacas, selClientes, rotaClientes, placaClientes, opClientes]);

  useEffect(() => {
    if (!planilhaFile) {
      setColetaToken(null);
      setProtheusReview(null);
      setCoverageToken(null);
      setCoverageReview(null);
      setCoverageResolvedSignature(null);
      return;
    }
    setColetaToken(null);
    setProtheusReview(null);
  }, [planilhaFile, selRotas, selPlacas, selClientes]);

  useEffect(() => {
    return () => {
      if (autoCoverageTimerRef.current) {
        clearTimeout(autoCoverageTimerRef.current);
        autoCoverageTimerRef.current = null;
      }
    };
  }, []);

  const selecionarPastaXmls = async () => {
    try {
      const r = await fetch(API_URL + "/api/ui/pasta-xmls/selecionar", {
        method: "POST",
      });
      const j = await parseApiPayload<{ sucesso?: boolean; mensagem?: string; pasta_xmls?: string }>(r);
      if (!r.ok || !j?.sucesso) throw new Error(j?.mensagem || "SeleÃ§Ã£o cancelada");
      setPastaXmls(j.pasta_xmls);
      setPastaXmlsEdit(j.pasta_xmls || "");
      setResumo(null);
      toast({
        title: "Pasta selecionada",
        description: j.pasta_xmls,
      });
    } catch (err) {
      toast({
        title: "Erro",
        description: err instanceof Error ? err.message : "Falha ao selecionar pasta",
        variant: "destructive",
      });
    }
  };

  const salvarPastaXmls = async () => {
    try {
      const r = await fetch(API_URL + "/api/ui/pasta-xmls/set", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pasta_xmls: pastaXmlsEdit }),
      });
      const j = await parseApiPayload<{ sucesso?: boolean; mensagem?: string; pasta_xmls?: string }>(r);
      if (!r.ok || !j?.sucesso) throw new Error(j?.mensagem || "SeleÃ§Ã£o cancelada");
      setPastaXmls(j.pasta_xmls);
      setPastaXmlsEdit(j.pasta_xmls || "");
      setResumo(null);
      toast({
        title: "Pasta atualizada",
        description: j.pasta_xmls,
      });
    } catch (err) {
      toast({
        title: "Erro",
        description: err instanceof Error ? err.message : "Falha ao selecionar pasta",
        variant: "destructive",
      });
    }
  };

  const prepararPlanilhaBackend = async (
    arquivo: File,
    options?: {
      resetSelections?: boolean;
    },
  ) => {
    setFiltrosCarregando(true);
    try {
      const form = new FormData();
      form.append("planilha", arquivo);
      const r = await fetch(API_URL + "/api/planilha-filtros", { method: "POST", body: form });
      const j = ((await parseApiPayload<ApiFiltros>(r)) || {}) as ApiFiltros;
      if (!r.ok || !j?.sucesso) throw new Error(j?.mensagem || `Erro HTTP ${r.status}`);

      setOpRotas((j.rotas || []).filter(Boolean));
      setOpPlacas((j.placas || []).filter(Boolean));
      setOpClientes((j.clientes || []).filter(Boolean));
      setRotaClientes(j.rota_clientes || {});
      setPlacaClientes(j.placa_clientes || {});
      setPlanilhaToken(j.planilha_token || null);

      if (options?.resetSelections ?? true) {
        setSelRotas([]);
        setSelPlacas([]);
        setSelClientes([]);
      }

      return j.planilha_token || null;
    } finally {
      setFiltrosCarregando(false);
    }
  };

  const extrairDoProtheus = async () => {
    setProtheusExtraindo(true);
    setResumo(null);
    setProgress(0);
    setProgressoInfo(null);

    let progressInterval: NodeJS.Timeout | null = null;

    try {
      if (!planilhaFile) {
        throw new Error("Selecione a planilha antes de extrair do Protheus");
      }
      if (filtrosCarregando) {
        throw new Error("Aguarde a leitura da planilha terminar para extrair o subset correto");
      }
      if (!protheusUf) {
        throw new Error("Selecione a UF da execucao");
      }

      let tokenAtual = planilhaToken;
      if (!tokenAtual) {
        tokenAtual = await prepararPlanilhaBackend(planilhaFile, { resetSelections: false });
      }
      if (!tokenAtual) {
        throw new Error("Nao foi possivel preparar a planilha no backend para iniciar a coleta");
      }

      progressInterval = pollProgresso();
      const response = await fetch(API_URL + "/api/protheus/extrair", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          planilha_token: tokenAtual,
          uf: protheusUf,
          filtro_rotas: selRotas,
          filtro_placas: selPlacas,
          filtro_clientes: selClientes,
        }),
      });
      const payload = await parseApiPayload<{ sucesso?: boolean; mensagem?: string; review?: ProtheusReview }>(response);

      if (progressInterval) clearInterval(progressInterval);
      setProgress(100);

      if (!response.ok || !payload?.sucesso) {
        throw new Error(payload?.mensagem || `Erro HTTP ${response.status}`);
      }

      const review = payload.review as ProtheusReview;
      setColetaToken(review.coleta_token);
      setProtheusReview(review);
      toast({
        title: "Coleta Protheus concluida",
        description: review.ready_for_processing
          ? "Os artefatos foram revisados e estao prontos para processamento."
          : "A coleta terminou, mas a revisao indica pendencias antes do processamento.",
      });
    } catch (err) {
      setProgress(0);
      toast({
        title: "Erro",
        description: err instanceof Error ? err.message : "Falha ao extrair do Protheus",
        variant: "destructive",
      });
    } finally {
      if (progressInterval) clearInterval(progressInterval);
      setProtheusExtraindo(false);
    }
  };

  const handlePlanilhaChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] || null;
    setPlanilhaFile(f);
    setPlanilhaToken(null);
    setCoverageToken(null);
    setCoverageReview(null);
    setCoverageResolvedSignature(null);
    setResumo(null);
    if (f) {
      toast({
        title: "Planilha carregada",
        description: f.name,
      });

      // Carregar opÃ§Ãµes de filtros automaticamente
      (async () => {
        try {
          await prepararPlanilhaBackend(f, { resetSelections: true });
        } catch (err) {
          toast({
            title: "Erro ao carregar filtros",
            description: err instanceof Error ? err.message : "Falha ao ler a planilha",
            variant: "destructive",
          });
        }
      })();
    }
  };

  const handleBoletosChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] || null;
    setBoletosPdfFile(f);
    setResumo(null);
    if (f) {
      toast({
        title: "PDF de boletos carregado",
        description: f.name,
      });
    }
  };

  const salvarConfigProtheus = async () => {
    setProtheusSalvandoConfig(true);
    try {
      const ufBranchMap = parseBranchMapText(protheusUfMapText);
      if (Object.keys(ufBranchMap).length === 0) {
        throw new Error("Informe ao menos um mapeamento UF=filial");
      }

      const r = await fetch(API_URL + "/api/ui/protheus-config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          base_url: protheusBaseUrl,
          protheus_user: protheusUser,
          uf_branch_map: ufBranchMap,
        }),
      });
      const j = await parseApiPayload<{ sucesso?: boolean; mensagem?: string; config?: ProtheusConfig }>(r);
      if (!r.ok || !j?.sucesso) throw new Error(j?.mensagem || "Falha ao salvar configuracao do Protheus");

      applyProtheusConfig(j.config as ProtheusConfig);
      toast({
        title: "Configuracao salva",
        description: "Mapa UF -> filial e dados publicos do Protheus atualizados.",
      });
    } catch (err) {
      toast({
        title: "Erro",
        description: err instanceof Error ? err.message : "Falha ao salvar configuracao do Protheus",
        variant: "destructive",
      });
    } finally {
      setProtheusSalvandoConfig(false);
    }
  };

  const salvarCredenciaisProtheus = async () => {
    setProtheusSalvandoCredenciais(true);
    try {
      if (!protheusUser.trim()) {
        throw new Error("Informe o usuario do Protheus antes de salvar a senha");
      }
      if (!protheusPassword) {
        throw new Error("Informe a senha do Protheus");
      }

      const r = await fetch(API_URL + "/api/ui/protheus-credenciais", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: protheusUser,
          password: protheusPassword,
        }),
      });
      const j = await parseApiPayload<{ sucesso?: boolean; mensagem?: string; config?: ProtheusConfig }>(r);
      if (!r.ok || !j?.sucesso) throw new Error(j?.mensagem || "Falha ao salvar credenciais");

      setProtheusPassword("");
      applyProtheusConfig(j.config as ProtheusConfig);
      toast({
        title: "Credenciais salvas",
        description: "A senha do Protheus foi salva no Windows Credential Manager.",
      });
    } catch (err) {
      toast({
        title: "Erro",
        description: err instanceof Error ? err.message : "Falha ao salvar credenciais do Protheus",
        variant: "destructive",
      });
    } finally {
      setProtheusSalvandoCredenciais(false);
    }
  };

  const renderCoverageXmlBadge = (status: CoverageItem["xml_status"]) => {
    const variant =
      status === "found_local" || status === "recovered_protheus"
        ? "secondary"
        : status === "missing" || status === "invalid_key"
          ? "destructive"
          : "outline";
    return <Badge variant={variant}>{coverageXmlStatusLabel[status]}</Badge>;
  };

  const renderCoveragePdfBadge = (status: CoverageItem["pdf_status"]) => {
    const variant = status === "missing" ? "destructive" : status === "ready" ? "secondary" : "outline";
    return <Badge variant={variant}>{coveragePdfStatusLabel[status]}</Badge>;
  };

  const validarCobertura = async (options?: {
    silent?: boolean;
    tokenOverride?: string | null;
    signatureOverride?: string | null;
  }) => {
    if (autoCoverageTimerRef.current) {
      clearTimeout(autoCoverageTimerRef.current);
      autoCoverageTimerRef.current = null;
    }
    setCoverageValidando(true);
    setProgress(0);
    setProgressoInfo(null);
    setResumo(null);

    let progressInterval: NodeJS.Timeout | null = null;

    try {
      if (!planilhaFile) {
        throw new Error("Selecione a planilha antes de validar a cobertura");
      }
      if (filtrosCarregando) {
        throw new Error("Aguarde a leitura da planilha terminar para validar o subset correto");
      }

      let tokenAtual = options?.tokenOverride ?? planilhaToken;
      if (!tokenAtual) {
        tokenAtual = await prepararPlanilhaBackend(planilhaFile, { resetSelections: false });
      }
      if (!tokenAtual) {
        throw new Error("Nao foi possivel preparar a planilha no backend para validar a cobertura");
      }
      const signatureAtual =
        options?.signatureOverride ??
        JSON.stringify({
          planilha_token: tokenAtual,
          origem_xml: coletaToken ? `coleta:${coletaToken}` : `pasta:${String(pastaXmls ?? "").trim()}`,
          uf: String(protheusUf ?? "").trim().toUpperCase(),
          filtro_rotas: normalizeSignatureList(selRotas),
          filtro_placas: normalizeSignatureList(selPlacas),
          filtro_clientes: normalizeSignatureList(selClientes),
          baixar_pdf: Boolean(baixarPdf),
          metodo_pdf: baixarPdf ? metodoPdf : "skip",
        });

      progressInterval = pollProgresso();
      const response = await fetch(API_URL + "/api/cobertura-lote", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          planilha_token: tokenAtual,
          coleta_token: coletaToken,
          uf: protheusUf || undefined,
          pasta_xmls: coletaToken ? undefined : pastaXmls,
          filtro_rotas: selRotas,
          filtro_placas: selPlacas,
          filtro_clientes: selClientes,
          garantir_pdf: true,
          baixar_pdf: baixarPdf,
          metodo_pdf: metodoPdf,
        }),
      });
      const payload = await parseApiPayload<{ sucesso?: boolean; mensagem?: string; review?: CoverageReview }>(response);

      if (progressInterval) clearInterval(progressInterval);
      setProgress(100);

      if (!response.ok || !payload?.sucesso || !payload.review) {
        throw new Error(payload?.mensagem || `Erro HTTP ${response.status}`);
      }

      setCoverageToken(payload.review.coverage_token);
      setCoverageReview(payload.review);
      setCoverageResolvedSignature(signatureAtual);
      if (!options?.silent) {
        toast({
          title: payload.review.ready_for_processing ? "Cobertura pronta" : "Cobertura bloqueada",
          description: payload.review.ready_for_processing
            ? "Todas as notas do subset ficaram auditadas e prontas para processamento."
            : payload.mensagem || "O lote ainda tem pendencias antes do processamento.",
          variant: payload.review.ready_for_processing ? undefined : "destructive",
        });
      }
    } catch (err) {
      setProgress(0);
      if (!options?.silent) {
        toast({
          title: "Erro",
          description: err instanceof Error ? err.message : "Falha ao validar a cobertura do lote",
          variant: "destructive",
        });
      }
    } finally {
      if (progressInterval) clearInterval(progressInterval);
      setCoverageValidando(false);
    }
  };

  validarCoberturaRef.current = validarCobertura;

  useEffect(() => {
    if (autoCoverageTimerRef.current) {
      clearTimeout(autoCoverageTimerRef.current);
      autoCoverageTimerRef.current = null;
    }
    if (!coverageCanAutoValidate || !coverageRequestSignature) {
      return;
    }
    if (coverageResolvedSignature === coverageRequestSignature || processing || protheusExtraindo || coverageValidando) {
      return;
    }
    autoCoverageTimerRef.current = setTimeout(() => {
      void validarCoberturaRef.current?.({
        silent: true,
        tokenOverride: planilhaToken,
        signatureOverride: coverageRequestSignature,
      });
    }, 250);
    return () => {
      if (autoCoverageTimerRef.current) {
        clearTimeout(autoCoverageTimerRef.current);
        autoCoverageTimerRef.current = null;
      }
    };
  }, [
    coverageCanAutoValidate,
    coverageRequestSignature,
    coverageResolvedSignature,
    coverageValidando,
    planilhaToken,
    processing,
    protheusExtraindo,
  ]);

  const handleProcess = async () => {
    setProcessing(true);
    setProgress(0);
    setProgressoInfo(null);
    setResumo(null);

    let progressInterval: NodeJS.Timeout | null = null;


    try {
      if (!planilhaFile) {
        throw new Error("Selecione a planilha (.xlsx) para processar");
      }
      if (!coverageToken || !coverageReview) {
        throw new Error("Valide a cobertura do lote antes de processar");
      }
      if (!coverageReadyForCurrentInputs) {
        throw new Error("A cobertura exibida nao corresponde mais as configuracoes atuais. Aguarde a revalidacao automatica terminar.");
      }
      if (!coverageReview.ready_for_processing) {
        throw new Error("A cobertura ainda esta bloqueada. Resolva as pendencias antes de processar.");
      }
      if (filtrosCarregando) {
        throw new Error("Aguarde: ainda estou lendo a planilha para carregar os filtros");
      }
      let tokenAtual = planilhaToken;
      if (!tokenAtual) {
        tokenAtual = await prepararPlanilhaBackend(planilhaFile, { resetSelections: false });
      }
      if (!tokenAtual) {
        throw new Error("Planilha ainda nÃ£o foi preparada no backend. Selecione a planilha novamente.");
      }

      const criarFormProcessamento = (token: string) => {
        const form = new FormData();
        form.append("planilha_token", token);
        form.append("coverage_token", coverageToken);
        if (!coverageReview.paths?.boleto_pdf_path && boletosPdfFile) {
          form.append("boletos_pdf", boletosPdfFile);
        }
        form.append("tipo_separacao", tipoSeparacao);
        form.append("baixar_pdf", String(baixarPdf));
        form.append("baixar_xml", String(baixarXml));
        form.append("juntar_pdfs", String(juntarPdfs));
        form.append("separar_em_pastas", String(separarEmPastas));
        form.append("metodo_pdf", metodoPdf);
        form.append("filtro_rotas", JSON.stringify(selRotas));
        form.append("filtro_placas", JSON.stringify(selPlacas));
        form.append("filtro_clientes", JSON.stringify(selClientes));
        return form;
      };

      const executarProcessamento = async (token: string) => {
        const resp = await fetch(API_URL + "/api/processar-local", {
          method: "POST",
          body: criarFormProcessamento(token),
        });
        const data = await parseApiPayload<{ sucesso?: boolean; mensagem?: string; resumo?: ApiResumo }>(resp);
        return { resp, data };
      };

      // Polling de progresso em tempo real
      progressInterval = pollProgresso();

      let { resp, data } = await executarProcessamento(tokenAtual);
      const mensagem = String(data?.mensagem || "");
      const tokenExpirado =
        resp.status === 400 &&
        (mensagem.includes("Token de planilha expirou") || mensagem.includes("planilha_token valido"));

      if (tokenExpirado && !coverageToken) {
        tokenAtual = await prepararPlanilhaBackend(planilhaFile, { resetSelections: false });
        if (!tokenAtual) {
          throw new Error("Token da planilha expirou e nÃ£o foi possÃ­vel renovar automaticamente.");
        }
        ({ resp, data } = await executarProcessamento(tokenAtual));
      }

      if (progressInterval) clearInterval(progressInterval);
      setProgress(100);

      if (!resp.ok || !data?.sucesso) {
        throw new Error(data?.mensagem || `Erro HTTP ${resp.status}`);
      }

      setResumo(data.resumo as ApiResumo);
      setRelatorioOpen(true);
      toast({
        title: "Processamento concluÃ­do!",
        description: data?.mensagem || "ConcluÃ­do",
      });

      // Abrir a pasta de saÃ­da automaticamente (executÃ¡vel/local)
      const saida = data?.resumo?.caminho_saida_base;
      if (saida) {
        try {
          await fetch(API_URL + "/api/ui/abrir-pasta", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path: saida }),
          });
        } catch {
          // se falhar, nÃ£o quebra o fluxo
        }
      }
    } catch (err) {
      setProgress(0);
      toast({
        title: "Erro",
        description: err instanceof Error ? err.message : "Falha ao processar",
        variant: "destructive",
      });
    } finally {
      if (progressInterval) clearInterval(progressInterval);
      setProcessing(false);
    }
  };

  return (
    <div className="w-full overflow-x-hidden">
      <Dialog open={relatorioOpen} onOpenChange={setRelatorioOpen}>
        <DialogContent className="flex max-w-5xl flex-col gap-0 overflow-hidden p-0 sm:rounded-xl max-h-[90vh]">
          <div className="border-b border-border px-6 py-4 pr-12">
            <DialogHeader className="space-y-0">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0">
                  <DialogTitle className="text-xl">RelatÃ³rio do processamento</DialogTitle>
                  <DialogDescription className="mt-1">
                    {resumo ? (
                      <span className="inline-flex flex-wrap items-center gap-2">
                        <span className="text-muted-foreground">Total</span>
                        <Badge variant="secondary">{resumo.total_alocacoes}</Badge>
                        <span className="text-muted-foreground">Sucesso</span>
                        <Badge variant="secondary">{resumo.sucesso}</Badge>
                        <span className="text-muted-foreground">Falhas</span>
                        <Badge variant={resumo.erros > 0 ? "destructive" : "secondary"}>{resumo.erros}</Badge>
                        <span className="text-muted-foreground">Taxa</span>
                        <Badge variant={resumo.erros > 0 ? "outline" : "secondary"}>{resumo.taxa_sucesso}</Badge>
                      </span>
                    ) : (
                      ""
                    )}
                  </DialogDescription>
                </div>

                {resumo?.boletos ? (
                  <div className="flex flex-wrap items-center gap-2 sm:justify-end">
                    {(resumo.boletos.pdf_total_documentos ?? 0) > 0 ? (
                      <Badge variant={resumo.boletos.pdf_ok ? "secondary" : "outline"} className="mr-8 sm:mr-0">
                        Boletos (PDF): {(resumo.boletos.pdf_separados ?? resumo.boletos.anexados_pdf ?? 0)}/{resumo.boletos.pdf_total_documentos ?? 0}
                      </Badge>
                    ) : (resumo.boletos.anexados_pdf ?? 0) > 0 ? (
                      <Badge variant={resumo.boletos.todos_ok ? "secondary" : "outline"}>
                        Boletos separados (PDF): {resumo.boletos.anexados_pdf}
                      </Badge>
                    ) : null}

                    {resumo.boletos.pdf_paginas_nao_identificadas ? (
                      <Badge variant="outline">PÃ¡ginas sem NF: {resumo.boletos.pdf_paginas_nao_identificadas}</Badge>
                    ) : null}
                    {resumo.boletos.anexados_historico ? (
                      <Badge variant="outline">HistÃ³rico usado: {resumo.boletos.anexados_historico}</Badge>
                    ) : null}
                    {typeof resumo.boletos.pdf_extracao_cache_hit === "boolean" ? (
                      <Badge variant={resumo.boletos.pdf_extracao_cache_hit ? "secondary" : "outline"}>
                        {resumo.boletos.pdf_extracao_cache_hit ? "ExtraÃ§Ã£o reaproveitada" : "ExtraÃ§Ã£o nova"}
                      </Badge>
                    ) : null}
                  </div>
                ) : null}
              </div>

              {resumo && relatorio.saida ? (
                <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                  {relatorio.execucao ? (
                    <div className="text-xs text-muted-foreground truncate">
                      ExecuÃ§Ã£o: <span className="font-mono">{relatorio.execucao}</span>
                    </div>
                  ) : (
                    <div />
                  )}
                  <Button size="sm" variant="outline" onClick={abrirPastaSaida}>
                    <FolderOpen className="h-4 w-4" /> Abrir pasta
                  </Button>
                </div>
              ) : null}
            </DialogHeader>
          </div>

          {!resumo ? (
            <div className="px-6 py-6 text-sm text-muted-foreground">Sem dados do relatÃ³rio.</div>
          ) : (
            <div className="flex flex-col min-h-0 flex-1 overflow-hidden">
              <div className="flex h-full min-h-0 flex-col gap-4 p-6">
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <Card className="shadow-card">
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="text-xs text-muted-foreground">Processadas</div>
                          <div className="mt-1 text-2xl font-semibold text-foreground">{resumo.total_alocacoes}</div>
                        </div>
                        <div className="rounded-lg bg-primary/10 p-2 text-primary">
                          <FileText className="h-5 w-5" />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                  <Card className="shadow-card">
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="text-xs text-muted-foreground">Sucesso</div>
                          <div className="mt-1 text-2xl font-semibold text-foreground">{resumo.sucesso}</div>
                        </div>
                        <div className="rounded-lg bg-success/10 p-2 text-success">
                          <CheckCircle2 className="h-5 w-5" />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                  <Card className="shadow-card">
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="text-xs text-muted-foreground">Falhas</div>
                          <div className="mt-1 text-2xl font-semibold text-foreground">{resumo.erros}</div>
                        </div>
                        <div className="rounded-lg bg-destructive/10 p-2 text-destructive">
                          <XCircle className="h-5 w-5" />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                  <Card className="shadow-card">
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="text-xs text-muted-foreground">Taxa de sucesso</div>
                          <div className="mt-1 text-2xl font-semibold text-foreground">{resumo.taxa_sucesso}</div>
                        </div>
                        <div className="rounded-lg bg-accent/30 p-2 text-accent">
                          <TrendingUp className="h-5 w-5" />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                <Tabs defaultValue="falhas" className="flex min-h-0 flex-1 flex-col w-full">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <TabsList className="w-full justify-start sm:w-auto">
                      <TabsTrigger value="falhas">Falhas ({relatorio.falhas.length})</TabsTrigger>
                      <TabsTrigger value="boletos_pdf" disabled={!hasPdfBoletos}>
                        Separados (PDF) ({relatorio.boletosPdfSeparados.length})
                      </TabsTrigger>
                      <TabsTrigger value="boletos_pdf_problemas" disabled={!hasPdfBoletos}>
                        Problemas PDF ({relatorio.boletosPdfProblemas.length + (relatorio.boletos?.pdf_paginas_nao_identificadas ?? 0)})
                      </TabsTrigger>
                      <TabsTrigger value="boletos_faltando" disabled={!hasPdfBoletos}>
                        Faltando (NF) ({relatorio.boletosFaltando.length})
                      </TabsTrigger>
                      <TabsTrigger value="boletos_historico" disabled={!hasPdfBoletos}>
                        Do histÃ³rico ({relatorio.boletosHistorico.length})
                      </TabsTrigger>
                    </TabsList>

                    {hasPdfBoletos ? (
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="outline">
                          <Receipt className="mr-1 h-3.5 w-3.5" /> PDF: {(relatorio.boletos?.pdf_separados ?? relatorio.boletos?.anexados_pdf ?? 0)}/{relatorio.boletos?.pdf_total_documentos ?? 0}
                        </Badge>
                        <Badge variant={relatorio.boletos?.pdf_ok ? "secondary" : "outline"}>
                          {relatorio.boletos?.pdf_ok ? "PDF OK" : "PDF com pendÃªncias"}
                        </Badge>
                        <Badge variant="outline">
                          <History className="mr-1 h-3.5 w-3.5" /> HistÃ³rico: {relatorio.boletos?.anexados_historico ?? 0}
                        </Badge>
                        {typeof relatorio.boletos?.pdf_extracao_cache_hit === "boolean" ? (
                          <Badge variant={relatorio.boletos.pdf_extracao_cache_hit ? "secondary" : "outline"}>
                            {relatorio.boletos.pdf_extracao_cache_hit ? "Cache da extraÃ§Ã£o: hit" : "Cache da extraÃ§Ã£o: miss"}
                          </Badge>
                        ) : null}
                        {relatorio.boletos?.pdf_source_hash ? (
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Badge variant="outline" className="font-mono text-[11px]">
                                  PDF hash: {resumirHash(relatorio.boletos.pdf_source_hash)}
                                </Badge>
                              </TooltipTrigger>
                              <TooltipContent side="bottom" className="max-w-[360px] break-all font-mono text-[11px]">
                                {relatorio.boletos.pdf_source_hash}
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        ) : null}
                      </div>
                    ) : null}
                  </div>

                  <TabsContent value="falhas" className="mt-4 flex min-h-0 flex-1 flex-col">
                    <Card className="shadow-card flex min-h-0 flex-1 flex-col">
                      <CardHeader className="pb-2">
                        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                          <CardTitle className="text-base">NFs com erro</CardTitle>
                          <div className="w-full sm:w-80">
                            <Input
                              value={qFalhas}
                              onChange={(e) => setQFalhas(e.target.value)}
                              placeholder="Buscar por NF, cliente ou motivoâ€¦"
                              className="h-9"
                            />
                          </div>
                        </div>
                        {relatorio.falhas.length > 0 ? (
                          <div className="text-xs text-muted-foreground">
                            Exibindo {relatorioFiltrado.falhas.length} de {relatorio.falhas.length}
                          </div>
                        ) : null}
                      </CardHeader>
                      <CardContent className="flex min-h-0 flex-1 flex-col p-4">
                        {relatorioFiltrado.falhas.length === 0 ? (
                          <Alert>
                            <AlertTitle>{relatorio.falhas.length === 0 ? "Sem falhas" : "Nenhum resultado"}</AlertTitle>
                            <AlertDescription>
                              {relatorio.falhas.length === 0
                                ? "Todas as NFs foram processadas com sucesso."
                                : "A busca nÃ£o encontrou itens para este filtro."}
                            </AlertDescription>
                          </Alert>
                        ) : (
                          <div className="rounded-lg border overflow-hidden flex flex-col flex-1 min-h-[200px]">
                            <ScrollArea className="h-full">
                              <Table>
                              <TableHeader>
                                <TableRow>
                                  <TableHead className="h-10 w-[120px] px-3">NF</TableHead>
                                  <TableHead className="h-10 min-w-[220px] px-3">Cliente</TableHead>
                                  <TableHead>Motivo</TableHead>
                                </TableRow>
                              </TableHeader>
                              <TableBody>
                                {relatorioFiltrado.falhas.map((r) => (
                                  <TableRow key={r.chave}>
                                    <TableCell className="px-3 py-2 font-mono text-xs">{r.nf || "-"}</TableCell>
                                    <TableCell className="min-w-[220px] px-3 py-2">{r.cliente || "-"}</TableCell>
                                    <TableCell className="px-3 py-2 break-words">{r.mensagem || r.etapa}</TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                              </Table>
                            </ScrollArea>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  </TabsContent>

                  <TabsContent value="boletos_pdf" className="mt-4 flex min-h-0 flex-1 flex-col">
                    <Card className="shadow-card flex min-h-0 flex-1 flex-col">
                      <CardHeader className="pb-2">
                        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                          <CardTitle className="text-base">Boletos separados do PDF</CardTitle>
                          <div className="w-full sm:w-80">
                            <Input
                              value={qBoletosPdfSeparados}
                              onChange={(e) => setQBoletosPdfSeparados(e.target.value)}
                              placeholder="Buscar por NF, cliente ou docâ€¦"
                              className="h-9"
                              disabled={!hasPdfBoletos}
                            />
                          </div>
                        </div>
                        {hasPdfBoletos ? (
                          <div className="text-xs text-muted-foreground">
                            Exibindo {relatorioFiltrado.boletosPdfSeparados.length} de {relatorio.boletosPdfSeparados.length}
                          </div>
                        ) : null}
                      </CardHeader>
                      <CardContent className="flex min-h-0 flex-1 flex-col p-4">
                        {!hasPdfBoletos ? (
                          <Alert>
                            <AlertTitle>Sem boletos</AlertTitle>
                            <AlertDescription>VocÃª nÃ£o informou um PDF de boletos neste processamento.</AlertDescription>
                          </Alert>
                        ) : relatorioFiltrado.boletosPdfSeparados.length === 0 ? (
                          <Alert>
                            <AlertTitle>{relatorio.boletosPdfSeparados.length === 0 ? "Nenhum item" : "Nenhum resultado"}</AlertTitle>
                            <AlertDescription>
                              {relatorio.boletosPdfSeparados.length === 0
                                ? "Nenhum boleto foi separado do PDF neste processamento."
                                : "A busca nÃ£o encontrou itens para este filtro."}
                            </AlertDescription>
                          </Alert>
                        ) : (
                          <div className="rounded-lg border overflow-hidden flex flex-col flex-1 min-h-[200px]">
                            <ScrollArea className="h-full">
                              <Table>
                              <TableHeader>
                                <TableRow>
                                  <TableHead className="h-10 w-[120px] px-3">NF</TableHead>
                                  <TableHead className="min-w-[220px]">Cliente</TableHead>
                                  <TableHead className="h-10 w-[140px] px-3">PÃ¡ginas</TableHead>
                                  <TableHead className="min-w-[320px]">Auditoria</TableHead>
                                </TableRow>
                              </TableHeader>
                              <TableBody>
                                {relatorioFiltrado.boletosPdfSeparados.map((b) => (
                                  <TableRow key={b.chave}>
                                    <TableCell className="px-3 py-2 font-mono text-xs">{b.nf || "-"}</TableCell>
                                    <TableCell className="px-3 py-2 break-words">{b.cliente || "-"}</TableCell>
                                    <TableCell className="px-3 py-2 font-mono text-xs">{formatPaginas(b.paginas)}</TableCell>
                                    <TableCell className="px-3 py-2">
                                      {renderBoletoAuditoria(b, "Separado sem detalhes extras")}
                                    </TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                              </Table>
                            </ScrollArea>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  </TabsContent>

                  <TabsContent value="boletos_pdf_problemas" className="mt-4 flex min-h-0 flex-1 flex-col">
                    <Card className="shadow-card flex min-h-0 flex-1 flex-col">
                      <CardHeader className="pb-2">
                        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                          <CardTitle className="text-base">Problemas no PDF de boletos</CardTitle>
                          <div className="w-full sm:w-80">
                            <Input
                              value={qBoletosPdfProblemas}
                              onChange={(e) => setQBoletosPdfProblemas(e.target.value)}
                              placeholder="Buscar por doc, NF, pagador ou motivoâ€¦"
                              className="h-9"
                              disabled={!hasPdfBoletos}
                            />
                          </div>
                        </div>

                        {hasPdfBoletos ? (
                          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                            <span>
                              Exibindo {relatorioFiltrado.boletosPdfProblemas.length} de {relatorio.boletosPdfProblemas.length}
                            </span>
                            {relatorio.boletos?.pdf_paginas_nao_identificadas ? (
                              <Badge variant="outline">PÃ¡ginas sem NF: {relatorio.boletos.pdf_paginas_nao_identificadas}</Badge>
                            ) : null}
                            {typeof relatorio.boletos?.pdf_sem_correspondencia === "number" ? (
                              <Badge variant="outline">Sem correspondÃªncia: {relatorio.boletos.pdf_sem_correspondencia}</Badge>
                            ) : null}
                            {typeof relatorio.boletos?.pdf_ambiguos === "number" ? (
                              <Badge variant="outline">AmbÃ­guos: {relatorio.boletos.pdf_ambiguos}</Badge>
                            ) : null}
                            {typeof relatorio.boletos?.pdf_sem_nf === "number" ? (
                              <Badge variant="outline">Sem NF: {relatorio.boletos.pdf_sem_nf}</Badge>
                            ) : null}
                            {typeof relatorio.boletos?.pdf_falha_salvar === "number" && relatorio.boletos.pdf_falha_salvar > 0 ? (
                              <Badge variant="outline">Falha ao salvar: {relatorio.boletos.pdf_falha_salvar}</Badge>
                            ) : null}
                          </div>
                        ) : null}
                      </CardHeader>
                      <CardContent className="flex min-h-0 flex-1 flex-col p-4">
                        {!hasPdfBoletos ? (
                          <Alert>
                            <AlertTitle>Sem boletos</AlertTitle>
                            <AlertDescription>VocÃª nÃ£o informou um PDF de boletos neste processamento.</AlertDescription>
                          </Alert>
                        ) : relatorioFiltrado.boletosPdfProblemas.length === 0 && !(relatorio.boletos?.pdf_paginas_nao_identificadas ?? 0) ? (
                          <Alert>
                            <AlertTitle>Sem problemas</AlertTitle>
                            <AlertDescription>Nenhum problema foi detectado no PDF de boletos.</AlertDescription>
                          </Alert>
                        ) : relatorioFiltrado.boletosPdfProblemas.length === 0 ? (
                          qBoletosPdfProblemas.trim() ? (
                            <Alert>
                              <AlertTitle>Nenhum resultado</AlertTitle>
                              <AlertDescription>A busca nÃ£o encontrou itens para este filtro.</AlertDescription>
                            </Alert>
                          ) : (
                            <Alert>
                              <AlertTitle>Sem correspondÃªncia detalhada</AlertTitle>
                              <AlertDescription>
                                HÃ¡ pÃ¡ginas sem NF identificada neste PDF, mas nenhum documento com mismatch detalhado foi registrado.
                              </AlertDescription>
                            </Alert>
                          )
                        ) : (
                          <div className="rounded-lg border overflow-hidden flex flex-col flex-1 min-h-[200px]">
                            <ScrollArea className="h-full">
                              <Table>
                              <TableHeader>
                                <TableRow>
                                  <TableHead className="h-10 w-[160px] px-3">Doc/NF</TableHead>
                                  <TableHead className="min-w-[220px]">Motivo</TableHead>
                                  <TableHead className="h-10 w-[100px] px-3">PÃ¡ginas</TableHead>
                                  <TableHead className="min-w-[340px]">Auditoria</TableHead>
                                </TableRow>
                              </TableHeader>
                              <TableBody>
                                {relatorioFiltrado.boletosPdfProblemas.map((p, idx) => (
                                  <TableRow key={`${p.doc}-${idx}`}>
                                    <TableCell className="px-3 py-2 font-mono text-xs">{p.doc || "-"}</TableCell>
                                    <TableCell className="px-3 py-2 break-words">{p.motivo || "-"}</TableCell>
                                    <TableCell className="px-3 py-2 text-xs">{p.paginas ?? "-"}</TableCell>
                                    <TableCell className="px-3 py-2">
                                      {renderBoletoAuditoria(p, "Sem detalhes extras para auditoria")}
                                    </TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                              </Table>
                            </ScrollArea>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  </TabsContent>

                  <TabsContent value="boletos_faltando" className="mt-4 flex min-h-0 flex-1 flex-col">
                    <Card className="shadow-card flex min-h-0 flex-1 flex-col">
                      <CardHeader className="pb-2">
                        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                          <CardTitle className="text-base">Boletos do PDF nÃ£o anexados (NF)</CardTitle>
                          <div className="w-full sm:w-80">
                            <Input
                              value={qBoletosFaltando}
                              onChange={(e) => setQBoletosFaltando(e.target.value)}
                              placeholder="Buscar por NF, cliente ou docâ€¦"
                              className="h-9"
                              disabled={!hasPdfBoletos}
                            />
                          </div>
                        </div>
                        {hasPdfBoletos ? (
                          <div className="text-xs text-muted-foreground">
                            Exibindo {relatorioFiltrado.boletosFaltando.length} de {relatorio.boletosFaltando.length}
                          </div>
                        ) : null}
                      </CardHeader>
                      <CardContent className="flex min-h-0 flex-1 flex-col p-4">
                        {!hasPdfBoletos ? (
                          <Alert>
                            <AlertTitle>Sem boletos</AlertTitle>
                            <AlertDescription>VocÃª nÃ£o informou um PDF de boletos neste processamento.</AlertDescription>
                          </Alert>
                        ) : relatorioFiltrado.boletosFaltando.length === 0 ? (
                          <Alert>
                            <AlertTitle>{relatorio.boletosFaltando.length === 0 ? "Tudo certo" : "Nenhum resultado"}</AlertTitle>
                            <AlertDescription>
                              {relatorio.boletosFaltando.length === 0
                                ? "Todos os boletos identificados no PDF foram anexados (PDF e/ou histÃ³rico)."
                                : "A busca nÃ£o encontrou itens para este filtro."}
                            </AlertDescription>
                          </Alert>
                        ) : (
                          <div className="rounded-lg border overflow-hidden flex flex-col flex-1 min-h-[200px]">
                            <ScrollArea className="h-full">
                              <Table>
                              <TableHeader>
                                <TableRow>
                                  <TableHead className="h-10 w-[120px] px-3">NF</TableHead>
                                  <TableHead className="min-w-[220px]">Cliente</TableHead>
                                  <TableHead className="h-10 w-[140px] px-3">PÃ¡ginas</TableHead>
                                  <TableHead className="min-w-[320px]">Contexto</TableHead>
                                </TableRow>
                              </TableHeader>
                              <TableBody>
                                {relatorioFiltrado.boletosFaltando.map((b) => (
                                  <TableRow key={b.chave}>
                                    <TableCell className="px-3 py-2 font-mono text-xs">{b.nf || "-"}</TableCell>
                                    <TableCell className="px-3 py-2 break-words">{b.cliente || "-"}</TableCell>
                                    <TableCell className="px-3 py-2 font-mono text-xs">{formatPaginas(b.paginas)}</TableCell>
                                    <TableCell className="px-3 py-2">
                                      {renderBoletoAuditoria(b, "NF esperada, mas sem sinais adicionais")}
                                    </TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                              </Table>
                            </ScrollArea>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  </TabsContent>

                  <TabsContent value="boletos_historico" className="mt-4 flex min-h-0 flex-1 flex-col">
                    <Card className="shadow-card flex min-h-0 flex-1 flex-col">
                      <CardHeader className="pb-2">
                        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                          <CardTitle className="text-base">Boletos recuperados do histÃ³rico</CardTitle>
                          <div className="w-full sm:w-80">
                            <Input
                              value={qBoletosHistorico}
                              onChange={(e) => setQBoletosHistorico(e.target.value)}
                              placeholder="Buscar por NF, cliente ou docâ€¦"
                              className="h-9"
                              disabled={!hasPdfBoletos}
                            />
                          </div>
                        </div>
                        {hasPdfBoletos ? (
                          <div className="text-xs text-muted-foreground">
                            Exibindo {relatorioFiltrado.boletosHistorico.length} de {relatorio.boletosHistorico.length}
                          </div>
                        ) : null}
                      </CardHeader>
                      <CardContent className="flex min-h-0 flex-1 flex-col p-4">
                        {!hasPdfBoletos ? (
                          <Alert>
                            <AlertTitle>Sem boletos</AlertTitle>
                            <AlertDescription>VocÃª nÃ£o informou um PDF de boletos neste processamento.</AlertDescription>
                          </Alert>
                        ) : relatorioFiltrado.boletosHistorico.length === 0 ? (
                          <Alert>
                            <AlertTitle>
                              {relatorio.boletosHistorico.length === 0 ? "Nenhum item" : "Nenhum resultado"}
                            </AlertTitle>
                            <AlertDescription>
                              {relatorio.boletosHistorico.length === 0
                                ? "Nenhum boleto precisou ser recuperado do histÃ³rico."
                                : "A busca nÃ£o encontrou itens para este filtro."}
                            </AlertDescription>
                          </Alert>
                        ) : (
                          <>
                            <div className="mb-3 text-sm text-muted-foreground">
                              Estes boletos foram encontrados no cache/histÃ³rico local e anexados automaticamente.
                            </div>
                            <div className="rounded-lg border overflow-hidden flex flex-col flex-1 min-h-[200px]">
                              <ScrollArea className="h-full">
                                <Table>
                                <TableHeader>
                                  <TableRow>
                                    <TableHead className="h-10 w-[120px] px-3">NF</TableHead>
                                    <TableHead className="min-w-[220px]">Cliente</TableHead>
                                    <TableHead className="h-10 w-[140px] px-3">PÃ¡ginas</TableHead>
                                    <TableHead className="min-w-[280px]">ReferÃªncia</TableHead>
                                  </TableRow>
                                </TableHeader>
                                <TableBody>
                                  {relatorioFiltrado.boletosHistorico.map((b) => (
                                    <TableRow key={b.chave}>
                                      <TableCell className="px-3 py-2 font-mono text-xs">{b.nf || "-"}</TableCell>
                                      <TableCell className="px-3 py-2 break-words">{b.cliente || "-"}</TableCell>
                                      <TableCell className="px-3 py-2 font-mono text-xs">{formatPaginas(b.paginas)}</TableCell>
                                      <TableCell className="px-3 py-2">
                                        {renderBoletoAuditoria(b, "Recuperado do histÃ³rico local")}
                                      </TableCell>
                                    </TableRow>
                                  ))}
                                </TableBody>
                                </Table>
                              </ScrollArea>
                            </div>
                          </>
                        )}
                      </CardContent>
                    </Card>
                  </TabsContent>
                </Tabs>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={coverageRoutesOpen} onOpenChange={setCoverageRoutesOpen}>
        <DialogContent className="flex max-w-4xl flex-col gap-0 overflow-hidden p-0 sm:rounded-xl max-h-[85vh]">
          <div className="border-b border-border px-6 py-4 pr-12">
            <DialogHeader className="space-y-2">
              <DialogTitle className="text-xl">Cobertura por rota</DialogTitle>
              <DialogDescription>
                Veja todas as rotas auditadas na cobertura atual, com notas esperadas, XML pronto, PDF pronto e faltantes.
              </DialogDescription>
            </DialogHeader>
          </div>

          <div className="flex min-h-0 flex-1 flex-col p-6">
            {!coverageReview?.routes.length ? (
              <div className="text-sm text-muted-foreground">Sem dados de rota nesta cobertura.</div>
            ) : (
              <ScrollArea className="min-h-0 flex-1 rounded-xl border border-border/60 bg-background/50">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Rota</TableHead>
                      <TableHead className="text-right">Esperadas</TableHead>
                      <TableHead className="text-right">Com XML</TableHead>
                      <TableHead className="text-right">Com PDF</TableHead>
                      <TableHead className="text-right">Faltantes</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {coverageReview.routes.map((route) => (
                      <TableRow key={route.rota}>
                        <TableCell className="max-w-[420px] break-words">{route.rota}</TableCell>
                        <TableCell className="text-right">{route.esperadas}</TableCell>
                        <TableCell className="text-right">{route.com_xml}</TableCell>
                        <TableCell className="text-right">{route.com_pdf}</TableCell>
                        <TableCell className="text-right">{route.faltantes}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {filtrosCarregando && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
          <div className="w-[min(520px,92vw)] rounded-2xl border border-border bg-card/90 p-6 shadow-2xl">
            <div className="flex items-center gap-4">
              <div className="h-10 w-10 rounded-full border-4 border-primary/30 border-t-primary animate-spin" />
              <div className="min-w-0">
                <div className="text-base font-semibold text-foreground">Lendo planilha...</div>
                <div className="text-sm text-muted-foreground">Carregando filtros do lote.</div>
              </div>
            </div>
          </div>
        </div>
      )}
      <div className="min-h-screen bg-[linear-gradient(180deg,hsl(var(--background)),hsl(var(--muted)/0.94))]">
        <div className="mx-auto w-full max-w-[1500px] px-4 py-5 sm:px-6 lg:px-8">
          <section className="overflow-hidden rounded-[28px] border border-border/80 bg-card/94 shadow-[0_28px_80px_-48px_rgba(0,0,0,0.9)]">
            <div className="border-b border-border/70 px-5 py-5 sm:px-6">
              <div className="flex flex-col gap-3">
                <div className="min-w-0">
                  <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Processamento de lote</div>
                  <h1 className="mt-2 text-2xl font-semibold tracking-tight text-foreground">
                    Planilha, cobertura e disparo no mesmo painel.
                  </h1>
                  <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
                    Carregue a planilha, ajuste o recorte e dispare. O essencial fica concentrado aqui, sem cards de status e sem precisar percorrer a pagina para seguir o fluxo.
                  </p>
                </div>
              </div>
            </div>

            <div className="grid gap-0 lg:grid-cols-[minmax(0,1fr)_360px]">
              <div className="min-w-0 px-5 py-5 sm:px-6">
                <div className="space-y-6">
                  <section className="space-y-4">
                    <div>
                      <h2 className="text-sm font-semibold text-foreground">1. Entradas</h2>
                      <p className="mt-1 text-sm text-muted-foreground">
                        Planilha, boletos manuais e a base de XMLs que alimenta a cobertura.
                      </p>
                    </div>

                    <div className="grid gap-4 xl:grid-cols-2">
                      <div className="space-y-2 xl:col-span-2">
                        <Label htmlFor="file-upload">Planilha base (.xlsx)</Label>
                        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                          <Input id="file-upload" type="file" accept=".xlsx,.xls" onChange={handlePlanilhaChange} className="min-w-0 flex-1" />
                          {planilhaFile ? <Badge variant="secondary" className="max-w-full truncate">{planilhaFile.name}</Badge> : null}
                        </div>
                        <p className="text-xs text-muted-foreground">
                          Estrutura esperada: rota, placa, nota, chave e cliente.
                        </p>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="boletos-upload">PDF de boletos (opcional)</Label>
                        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                          <Input id="boletos-upload" type="file" accept=".pdf" onChange={handleBoletosChange} className="min-w-0 flex-1" />
                          {boletosPdfFile ? <Badge variant="outline" className="max-w-full truncate">{boletosPdfFile.name}</Badge> : null}
                        </div>
                        <p className="text-xs text-muted-foreground">Se houver PDF, o anexo entra no grupo final do lote.</p>
                      </div>

                      <div className="space-y-2">
                        <Label>Pasta de XMLs</Label>
                        <div className="flex flex-col gap-2">
                          <Input
                            value={pastaXmlsEdit}
                            onChange={(e) => setPastaXmlsEdit(e.target.value)}
                            placeholder="C:/Users/feito/Documents/work/XML"
                          />
                          <div className="flex gap-2">
                            <Button type="button" variant="outline" onClick={selecionarPastaXmls} className="flex-1">
                              Procurar
                            </Button>
                            <Button type="button" variant="outline" onClick={salvarPastaXmls} className="flex-1">
                              Salvar
                            </Button>
                          </div>
                        </div>
                        <p className="text-xs text-muted-foreground">{origemXmlResumo}</p>
                      </div>
                    </div>
                  </section>

                  <div className="h-px bg-border/70" />

                  <section className="space-y-4">
                    <div>
                      <h2 className="text-sm font-semibold text-foreground">2. Recorte e saida</h2>
                      <p className="mt-1 text-sm text-muted-foreground">
                        Ajuste o agrupamento, a estrategia de PDF e o subset do lote sem sair do painel.
                      </p>
                    </div>

                    <div className="grid gap-4 xl:grid-cols-2">
                      <div className="space-y-2">
                        <Label>Separar por</Label>
                        <RadioGroup
                          value={tipoSeparacao}
                          onValueChange={(value) => setTipoSeparacao(value as typeof tipoSeparacao)}
                          className="flex flex-wrap gap-4"
                        >
                          <div className="flex items-center gap-2">
                            <RadioGroupItem id="tipo-separacao-placa" value="placa" />
                            <Label htmlFor="tipo-separacao-placa">Placa</Label>
                          </div>
                          <div className="flex items-center gap-2">
                            <RadioGroupItem id="tipo-separacao-rota" value="rota" />
                            <Label htmlFor="tipo-separacao-rota">Rota</Label>
                          </div>
                        </RadioGroup>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="metodo-pdf">Metodo de PDF</Label>
                        <Select value={metodoPdf} onValueChange={(value) => setMetodoPdf(value as typeof metodoPdf)} disabled={!baixarPdf}>
                          <SelectTrigger id="metodo-pdf">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="api">API</SelectItem>
                            <SelectItem value="local">Local</SelectItem>
                            <SelectItem value="api_fallback_local">API + local</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-2 xl:col-span-2">
                        <Label>Entrega final</Label>
                        <div className="flex flex-wrap gap-x-5 gap-y-3 text-sm">
                          <label className="flex items-center gap-2">
                            <Checkbox checked={baixarPdf} onCheckedChange={(checked) => setBaixarPdf(checked === true)} />
                            <span>Download de PDFs</span>
                          </label>
                          <label className="flex items-center gap-2">
                            <Checkbox checked={baixarXml} onCheckedChange={(checked) => setBaixarXml(checked === true)} />
                            <span>Download de XMLs</span>
                          </label>
                          <label className="flex items-center gap-2">
                            <Checkbox
                              checked={juntarPdfs}
                              onCheckedChange={(checked) => setJuntarPdfs(checked === true)}
                              disabled={!baixarPdf}
                            />
                            <span>Juntar PDFs por grupo</span>
                          </label>
                          <label className="flex items-center gap-2">
                            <Checkbox
                              checked={separarEmPastas}
                              onCheckedChange={(checked) => setSepararEmPastas(checked === true)}
                            />
                            <span>Organizar em subpastas</span>
                          </label>
                        </div>
                      </div>
                    </div>

                    <div className="grid gap-4 xl:grid-cols-2">
                      <div className="space-y-2">
                        <Label>Placas</Label>
                        <MultiSelect
                          placeholder={selRotas.length > 0 ? "Desabilitado por rotas" : "Buscar placas..."}
                          options={opPlacas.map((placa) => ({ value: placa } as MultiSelectOption))}
                          value={selPlacas}
                          onChange={(next) => {
                            setSelPlacas(next);
                            if (next.length > 0) setSelRotas([]);
                          }}
                          disabled={filtrosCarregando || selRotas.length > 0 || opPlacas.length === 0}
                          minSearchChars={3}
                        />
                      </div>

                      <div className="space-y-2">
                        <Label>Rotas</Label>
                        <MultiSelect
                          placeholder={selPlacas.length > 0 ? "Desabilitado por placas" : "Buscar rotas..."}
                          options={opRotas.map((rota) => ({ value: rota } as MultiSelectOption))}
                          value={selRotas}
                          onChange={(next) => {
                            setSelRotas(next);
                            if (next.length > 0) setSelPlacas([]);
                          }}
                          disabled={filtrosCarregando || selPlacas.length > 0 || opRotas.length === 0}
                          minSearchChars={3}
                        />
                      </div>

                      <div className="space-y-2 xl:col-span-2">
                        <Label>Clientes</Label>
                        <MultiSelect
                          placeholder="Buscar clientes..."
                          options={clienteOptionsFiltrados.map((cliente) => ({ value: cliente } as MultiSelectOption))}
                          value={selClientes}
                          onChange={(next) => {
                            const allowed = new Set(clienteOptionsFiltrados);
                            setSelClientes(next.filter((item) => allowed.has(item)));
                          }}
                          disabled={filtrosCarregando || clienteOptionsFiltrados.length === 0}
                          minSearchChars={3}
                        />
                        <div className="flex flex-col gap-2 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
                          <span>Filtros usam logica OR. Qualquer criterio valido entra no lote.</span>
                          <Button
                            type="button"
                            variant="ghost"
                            className="h-auto justify-start px-0 text-xs text-muted-foreground hover:text-foreground"
                            onClick={() => {
                              setSelRotas([]);
                              setSelPlacas([]);
                              setSelClientes([]);
                            }}
                          >
                            Limpar recorte
                          </Button>
                        </div>
                      </div>
                    </div>
                  </section>

                  <div className="h-px bg-border/70" />

                  <details className="group rounded-2xl border border-border/70 bg-background/35 px-4 py-4">
                    <summary className="flex cursor-pointer list-none items-start justify-between gap-3 [&::-webkit-details-marker]:hidden">
                      <div>
                        <h2 className="text-sm font-semibold text-foreground">3. Coleta Protheus</h2>
                        <p className="mt-1 text-sm text-muted-foreground">
                          Abra apenas se for usar o modo assistido ou se a cobertura precisar recuperar notas faltantes.
                        </p>
                      </div>
                      <Badge variant={coletaToken ? "secondary" : "outline"}>
                        {coletaToken ? "Coleta pronta" : "Opcional"}
                      </Badge>
                    </summary>

                    <div className="mt-4 space-y-4">
                      <div className="grid gap-4 md:grid-cols-2">
                        <div className="space-y-2">
                          <Label htmlFor="protheus-base-url">Base URL</Label>
                          <Input
                            id="protheus-base-url"
                            value={protheusBaseUrl}
                            onChange={(e) => setProtheusBaseUrl(e.target.value)}
                            placeholder="https://protheus.exemplo.local"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="protheus-user">Usuario</Label>
                          <Input
                            id="protheus-user"
                            value={protheusUser}
                            onChange={(e) => setProtheusUser(e.target.value)}
                            placeholder="usuario"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="protheus-uf">UF da execucao</Label>
                          <Select value={protheusUf} onValueChange={setProtheusUf}>
                            <SelectTrigger id="protheus-uf">
                              <SelectValue placeholder="Selecione a UF" />
                            </SelectTrigger>
                            <SelectContent>
                              {protheusUfOptions.map((ufOption) => (
                                <SelectItem key={ufOption} value={ufOption}>
                                  {ufOption}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="protheus-password">Senha</Label>
                          <Input
                            id="protheus-password"
                            type="password"
                            value={protheusPassword}
                            onChange={(e) => setProtheusPassword(e.target.value)}
                            placeholder={protheusConfig?.has_password ? "Senha ja salva no Windows" : "Informe a senha"}
                          />
                        </div>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="protheus-map">Mapa UF=filial</Label>
                        <Textarea
                          id="protheus-map"
                          value={protheusUfMapText}
                          onChange={(e) => setProtheusUfMapText(e.target.value)}
                          className="min-h-[96px] font-mono text-xs"
                          placeholder={"MG=0202\nRJ=0101\nSP=0201"}
                        />
                      </div>

                      <div className="flex flex-col gap-2 sm:flex-row">
                        <Button type="button" variant="outline" onClick={salvarConfigProtheus} disabled={workflowBusy || protheusSalvandoConfig}>
                          {protheusSalvandoConfig ? "Salvando config..." : "Salvar configuracao"}
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          onClick={salvarCredenciaisProtheus}
                          disabled={workflowBusy || protheusSalvandoCredenciais}
                        >
                          {protheusSalvandoCredenciais ? "Salvando senha..." : "Salvar senha"}
                        </Button>
                        <Button type="button" onClick={extrairDoProtheus} disabled={workflowBusy || filtrosCarregando || !planilhaFile}>
                          {protheusExtraindo ? "Extraindo..." : "Extrair do Protheus"}
                        </Button>
                      </div>

                      {protheusConfig?.pending_fields?.length ? (
                        <Alert className="border-amber-500/40 bg-amber-500/5">
                          <AlertTitle>Configuracao pendente</AlertTitle>
                          <AlertDescription className="space-y-2">
                            <p>Faltam seletores ou rotinas no arquivo operacional do Protheus.</p>
                            <p className="text-xs">Pendencias: {protheusConfig.pending_fields.join(", ")}</p>
                            {protheusConfig.config_path ? <p className="text-xs break-all">{protheusConfig.config_path}</p> : null}
                          </AlertDescription>
                        </Alert>
                      ) : null}

                      {protheusReview ? (
                        <div className="space-y-2 text-sm text-muted-foreground">
                          <div className="flex items-center justify-between gap-3">
                            <span>Filial</span>
                            <span className="font-medium text-foreground">
                              {protheusReview.uf} / {protheusReview.branch_code}
                            </span>
                          </div>
                          <div className="flex items-center justify-between gap-3">
                            <span>Subset</span>
                            <span className="font-medium text-foreground">{protheusReview.subset_total} notas</span>
                          </div>
                          <div className="flex items-center justify-between gap-3">
                            <span>XMLs</span>
                            <span className="font-medium text-foreground">
                              {protheusReview.xml.encontrados}/{protheusReview.xml.esperados}
                            </span>
                          </div>
                          <div className="flex items-center justify-between gap-3">
                            <span>Boletos</span>
                            <span className="font-medium text-foreground">
                              {protheusReview.boletos.pdf_disponivel ? "PDF pronto" : "Sem PDF"}
                            </span>
                          </div>
                        </div>
                      ) : null}
                    </div>
                  </details>
                </div>
              </div>

              <aside className="border-t border-border/70 bg-muted/16 px-5 py-5 sm:px-6 lg:border-l lg:border-t-0">
                <div className="flex h-full flex-col gap-5">
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h2 className="text-sm font-semibold text-foreground">Cobertura e disparo</h2>
                        <p className="mt-1 text-sm leading-6 text-muted-foreground">
                          A cobertura revalida sozinha quando o lote muda. O disparo so libera quando o estado exibido for o atual.
                        </p>
                      </div>
                      <Badge variant={coverageReadyForCurrentInputs ? "secondary" : "outline"}>
                        {coverageReadyForCurrentInputs
                          ? "Pronta"
                          : coverageValidando
                            ? "Atualizando"
                            : coverageReview
                              ? "Pendente"
                              : "Aguardando"}
                      </Badge>
                    </div>

                    {coverageToken ? (
                      <div className="text-[11px] font-mono text-muted-foreground">{coverageToken}</div>
                    ) : null}

                    {coverageReview ? (
                      <div className="space-y-2 text-sm">
                        <div className="flex items-center justify-between gap-3 border-b border-border/60 pb-2">
                          <span className="text-muted-foreground">Notas esperadas</span>
                          <span className="font-medium text-foreground">{coverageReview.totals.esperadas}</span>
                        </div>
                        <div className="flex items-center justify-between gap-3 border-b border-border/60 pb-2">
                          <span className="text-muted-foreground">Base local</span>
                          <span className="font-medium text-foreground">{coverageReview.totals.encontradas_local}</span>
                        </div>
                        <div className="flex items-center justify-between gap-3 border-b border-border/60 pb-2">
                          <span className="text-muted-foreground">Recuperadas</span>
                          <span className="font-medium text-foreground">{coverageReview.totals.recuperadas_protheus}</span>
                        </div>
                        <div className="flex items-center justify-between gap-3 border-b border-border/60 pb-2">
                          <span className="text-muted-foreground">Pendencias</span>
                          <span className="font-medium text-foreground">{coveragePendencias}</span>
                        </div>
                        <div className="flex items-center justify-between gap-3 border-b border-border/60 pb-2">
                          <span className="text-muted-foreground">PDF pronto</span>
                          <span className="font-medium text-foreground">{coverageReview.totals.com_pdf}</span>
                        </div>
                        <div className="flex items-center justify-between gap-3">
                          <span className="text-muted-foreground">Metodo</span>
                          <span className="font-medium text-foreground">{coverageReview.metodo_pdf.resolved}</span>
                        </div>
                      </div>
                    ) : (
                      <p className="text-sm leading-6 text-muted-foreground">
                        A validacao usa primeiro a base local. Se ainda faltar nota e houver UF configurada, o Protheus entra apenas para recuperar o que ficou pendente.
                      </p>
                    )}

                    {coverageStale ? (
                      <Alert>
                        <AlertTitle>Revalidacao em andamento</AlertTitle>
                        <AlertDescription>
                          O lote mudou e a tela manteve a ultima auditoria visivel enquanto a nova cobertura fecha.
                        </AlertDescription>
                      </Alert>
                    ) : null}

                    {coverageReview?.failures.length ? (
                      <Alert variant="destructive">
                        <AlertDescription>{coverageReview.failures[0]}</AlertDescription>
                      </Alert>
                    ) : null}

                    <div className="flex flex-col gap-2 sm:flex-row">
                      <Button type="button" variant="outline" onClick={validarCobertura} disabled={workflowBusy || filtrosCarregando || !planilhaFile}>
                        {coverageValidando ? "Validando..." : "Revalidar"}
                      </Button>
                      {coverageReview?.paths?.staging_root ? (
                        <Button
                          type="button"
                          variant="outline"
                          onClick={() =>
                            abrirPastaLocal(coverageReview.paths.staging_root, "Staging da cobertura aberto").catch((error) => {
                              toast({
                                title: "Erro",
                                description: error instanceof Error ? error.message : "Falha ao abrir staging da cobertura",
                                variant: "destructive",
                              });
                            })
                          }
                        >
                          Abrir staging
                        </Button>
                      ) : null}
                    </div>

                    {coverageReview ? (
                      <div className="space-y-3">
                        <details className="rounded-2xl border border-border/70 bg-background/45 px-3 py-3">
                          <summary className="cursor-pointer list-none text-sm font-medium text-foreground [&::-webkit-details-marker]:hidden">
                            Ver pendencias e itens auditados
                          </summary>
                          <div className="mt-3 space-y-3">
                            {coverageProblemItems.length ? (
                              <ScrollArea className="max-h-[220px] rounded-xl border border-border/60 bg-background/50">
                                <Table>
                                  <TableHeader>
                                    <TableRow>
                                      <TableHead>NF</TableHead>
                                      <TableHead>Cliente</TableHead>
                                      <TableHead>Motivo</TableHead>
                                    </TableRow>
                                  </TableHeader>
                                  <TableBody>
                                    {coverageProblemItems.map((item) => (
                                      <TableRow key={`${item.chave}-${item.rota || ""}-${item.nf || ""}`}>
                                        <TableCell className="font-mono text-xs">{item.nf || "-"}</TableCell>
                                        <TableCell className="max-w-[180px] break-words">{item.cliente || "-"}</TableCell>
                                        <TableCell className="max-w-[220px] break-words text-muted-foreground">
                                          {item.reason || item.source || "-"}
                                        </TableCell>
                                      </TableRow>
                                    ))}
                                  </TableBody>
                                </Table>
                              </ScrollArea>
                            ) : (
                              <div className="text-sm text-muted-foreground">Sem pendencias abertas nesta cobertura.</div>
                            )}
                          </div>
                        </details>

                        <Button
                          type="button"
                          variant="outline"
                          className="w-full justify-between rounded-2xl border-border/70 bg-background/45 px-3 py-3 text-sm font-medium text-foreground hover:bg-background/60"
                          onClick={() => setCoverageRoutesOpen(true)}
                        >
                          <span>Ver rota a rota</span>
                          <Badge variant="outline" className="ml-3">
                            {coverageReview.routes.length}
                          </Badge>
                        </Button>
                      </div>
                    ) : null}
                  </div>

                  <div className="mt-auto space-y-4">
                    {workflowBusy ? (
                      <div className="space-y-2">
                        <div className="flex items-center justify-between gap-3 text-sm">
                          <span className="font-medium text-foreground">
                            {protheusExtraindo ? "Extraindo do Protheus..." : coverageValidando ? "Validando cobertura..." : "Processando lote..."}
                          </span>
                          <span className="text-muted-foreground">{progress}%</span>
                        </div>
                        <Progress value={progress} className="h-2" />
                        <div className="text-xs leading-5 text-muted-foreground">
                          {progressoInfo?.mensagem ||
                            (protheusExtraindo
                              ? "Abrindo o browser embutido e baixando o recorte filtrado."
                              : coverageValidando
                                ? "Conferindo XMLs, PDF e recuperacao de faltantes."
                                : metodoPdf === "local"
                                  ? "Gerando DANFE local a partir da base validada."
                                  : "Enviando para API e buscando os PDFs do lote.")}
                        </div>
                        {progressoInfo?.detalhes ? <div className="text-[11px] text-muted-foreground">{progressoInfo.detalhes}</div> : null}
                      </div>
                    ) : null}

                    {resumo ? (
                      <div className="space-y-2 text-sm">
                        <div className="flex items-center justify-between gap-3">
                          <span className="text-muted-foreground">Total</span>
                          <span className="font-medium text-foreground">{resumo.total_alocacoes}</span>
                        </div>
                        <div className="flex items-center justify-between gap-3">
                          <span className="text-muted-foreground">Sucesso</span>
                          <span className="font-medium text-foreground">{resumo.sucesso}</span>
                        </div>
                        <div className="flex items-center justify-between gap-3">
                          <span className="text-muted-foreground">Erros</span>
                          <span className="font-medium text-foreground">{resumo.erros}</span>
                        </div>
                        <div className="flex items-center justify-between gap-3">
                          <span className="text-muted-foreground">Taxa</span>
                          <span className="font-medium text-foreground">{resumo.taxa_sucesso}</span>
                        </div>
                      </div>
                    ) : null}

                    <Button
                      onClick={handleProcess}
                      disabled={workflowBusy || filtrosCarregando || !coverageReadyForCurrentInputs}
                      className="w-full"
                      size="lg"
                    >
                      <Play className="mr-2 h-4 w-4" />
                      {processing
                        ? "Processando..."
                        : coverageReadyForCurrentInputs
                          ? "Processar lote"
                          : coverageReview
                            ? "Aguardando revalidacao"
                            : "Aguardando cobertura"}
                    </Button>

                    {progress === 100 && resumo && relatorio.saida ? (
                      <Button variant="outline" size="lg" className="w-full" onClick={abrirPastaSaida}>
                        <FolderOpen className="mr-2 h-4 w-4" />
                        Abrir pasta de saida
                      </Button>
                    ) : null}
                  </div>
                </div>
              </aside>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}


