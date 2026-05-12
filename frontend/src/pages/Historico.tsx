import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { 
  History, 
  Search, 
  FileText, 
  Download, 
  ChevronRight, 
  Calendar,
  CheckCircle2,
  XCircle,
  Loader2,
  ArrowLeft,
  Package
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from "@/components/ui/table";
import { toast } from "sonner";

interface Processamento {
  uuid: string;
  timestamp: string;
  planilha_nome: string;
  status: string;
  resumo: {
    total_alocacoes?: number;
    sucesso?: number;
    erros?: number;
  } | null;
}

interface DetalheProcessamento extends Processamento {
  tipo_separacao: string;
  mensagem?: string;
  filtros: any;
  arquivos: {
    chave_nfe: string;
    tipo: string;
    cliente: string;
    valor: number;
    rota: string;
    placa: string;
  }[];
}

import { API_URL } from "@/config";

const Historico = () => {
  const [selectedUuid, setSelectedUuid] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");

  const { data: list, isLoading: loadingList } = useQuery({
    queryKey: ["historico"],
    queryFn: async () => {
      const resp = await fetch(`${API_URL}/api/historico/listar`);
      if (!resp.ok) throw new Error("Falha ao carregar histórico");
      return (await resp.json()) as Processamento[];
    },
  });

  const { data: details, isLoading: loadingDetails } = useQuery({
    queryKey: ["historico-detalhes", selectedUuid],
    queryFn: async () => {
      if (!selectedUuid) return null;
      const resp = await fetch(`${API_URL}/api/historico/detalhes/${selectedUuid}`);
      if (!resp.ok) throw new Error("Falha ao carregar detalhes");
      return (await resp.json()) as DetalheProcessamento;
    },
    enabled: !!selectedUuid,
  });

  const handleDownload = (pUuid: string, tipo: string, chave: string) => {
    window.open(`${API_URL}/api/historico/download/${pUuid}/${tipo}/${chave}`, "_blank");
  };

  const filteredList = list?.filter(p => 
    p.planilha_nome.toLowerCase().includes(searchTerm.toLowerCase()) ||
    p.uuid.includes(searchTerm)
  );

  return (
    <div className="flex flex-col h-screen bg-[#121212] text-[#e0e0e0] overflow-hidden">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-[#1a1a1a] border-b border-[#2a2a2a] shrink-0">
        <div className="flex items-center gap-3">
          <History className="w-6 h-6 text-blue-500" />
          <h1 className="text-xl font-semibold tracking-tight">Histórico de Processamento</h1>
        </div>
        <div className="flex items-center gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input 
              placeholder="Buscar por planilha ou ID..." 
              className="pl-9 w-64 bg-[#222] border-[#333] focus:border-blue-500 transition-colors"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar List */}
        <div className="w-1/3 border-r border-[#2a2a2a] bg-[#161616] flex flex-col">
          <div className="p-4 border-b border-[#2a2a2a] bg-[#1a1a1a]">
            <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <Package className="w-4 h-4" />
              Lotes Recentes
            </h2>
          </div>
          <ScrollArea className="flex-1">
            {loadingList ? (
              <div className="flex items-center justify-center p-8">
                <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
              </div>
            ) : filteredList?.length === 0 ? (
              <div className="p-8 text-center text-muted-foreground italic">
                Nenhum processamento encontrado.
              </div>
            ) : (
              <div className="divide-y divide-[#2a2a2a]">
                {filteredList?.map((p) => (
                  <button
                    key={p.uuid}
                    onClick={() => setSelectedUuid(p.uuid)}
                    className={`w-full text-left p-4 transition-all hover:bg-[#222] flex items-start gap-3 group ${
                      selectedUuid === p.uuid ? "bg-[#1e1e1e] border-l-2 border-blue-500" : "border-l-2 border-transparent"
                    }`}
                  >
                    <div className={`mt-1 p-1.5 rounded-full ${
                      p.status === 'concluido' ? 'bg-green-500/10 text-green-500' : 
                      p.status === 'erro' ? 'bg-red-500/10 text-red-500' : 'bg-blue-500/10 text-blue-500'
                    }`}>
                      {p.status === 'concluido' ? <CheckCircle2 size={16} /> : 
                       p.status === 'erro' ? <XCircle size={16} /> : <Loader2 size={16} className="animate-spin" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex justify-between items-start gap-2">
                        <span className="font-medium text-sm truncate block">{p.planilha_nome}</span>
                        <ChevronRight className={`w-4 h-4 text-muted-foreground transition-transform ${selectedUuid === p.uuid ? "translate-x-1" : ""}`} />
                      </div>
                      <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                        <Calendar size={12} />
                        {new Date(p.timestamp).toLocaleString('pt-BR')}
                      </div>
                      {p.resumo && (
                        <div className="flex gap-3 mt-2">
                          <span className="text-[10px] text-green-500 bg-green-500/10 px-1.5 py-0.5 rounded">
                            {p.resumo.sucesso} OK
                          </span>
                          <span className="text-[10px] text-red-400 bg-red-400/10 px-1.5 py-0.5 rounded">
                            {p.resumo.erros} Erros
                          </span>
                        </div>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </ScrollArea>
        </div>

        {/* Details View */}
        <div className="flex-1 bg-[#121212] overflow-hidden flex flex-col">
          {selectedUuid ? (
            loadingDetails ? (
              <div className="flex-1 flex flex-center items-center justify-center">
                <Loader2 className="w-10 h-10 animate-spin text-blue-500" />
              </div>
            ) : details ? (
              <ScrollArea className="flex-1 p-8">
                <div className="max-w-4xl mx-auto space-y-8">
                  {/* Summary Header */}
                  <div className="flex justify-between items-start">
                    <div>
                      <h2 className="text-3xl font-bold">{details.planilha_nome}</h2>
                      <p className="text-muted-foreground mt-1 flex items-center gap-2">
                        ID: <code className="text-blue-400 bg-blue-400/10 px-1.5 rounded">{details.uuid}</code>
                      </p>
                    </div>
                    <Badge variant={details.status === 'concluido' ? 'default' : 'destructive'} className="text-sm px-3 py-1">
                      {details.status.toUpperCase()}
                    </Badge>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <Card className="bg-[#1a1a1a] border-[#2a2a2a]">
                      <CardHeader className="pb-2">
                        <CardDescription>Status Geral</CardDescription>
                        <CardTitle className="text-2xl">{details.resumo?.sucesso} / {details.resumo?.total_alocacoes}</CardTitle>
                      </CardHeader>
                    </Card>
                    <Card className="bg-[#1a1a1a] border-[#2a2a2a]">
                      <CardHeader className="pb-2">
                        <CardDescription>Tipo Separação</CardDescription>
                        <CardTitle className="text-2xl capitalize">{details.tipo_separacao}</CardTitle>
                      </CardHeader>
                    </Card>
                    <Card className="bg-[#1a1a1a] border-[#2a2a2a]">
                      <CardHeader className="pb-2">
                        <CardDescription>Data Processamento</CardDescription>
                        <CardTitle className="text-lg">{new Date(details.timestamp).toLocaleString('pt-BR')}</CardTitle>
                      </CardHeader>
                    </Card>
                  </div>

                  {/* Files Table */}
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <h3 className="text-lg font-semibold flex items-center gap-2">
                        <FileText className="w-5 h-5 text-blue-500" />
                        Arquivos Gerados
                      </h3>
                    </div>
                    <div className="rounded-md border border-[#2a2a2a] bg-[#161616] overflow-hidden">
                      <Table>
                        <TableHeader className="bg-[#1a1a1a]">
                          <TableRow className="border-[#2a2a2a] hover:bg-transparent">
                            <TableHead className="text-[#888]">Chave NF-e</TableHead>
                            <TableHead className="text-[#888]">Cliente</TableHead>
                            <TableHead className="text-[#888]">Rota/Placa</TableHead>
                            <TableHead className="text-[#888]">Tipo</TableHead>
                            <TableHead className="text-right text-[#888]">Ações</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {details.arquivos.map((arq, idx) => (
                            <TableRow key={`${arq.chave_nfe}-${arq.tipo}-${idx}`} className="border-[#2a2a2a] hover:bg-[#1e1e1e]">
                              <TableCell className="font-mono text-xs text-blue-400">{arq.chave_nfe}</TableCell>
                              <TableCell className="max-w-[150px] truncate">{arq.cliente}</TableCell>
                              <TableCell className="text-xs text-muted-foreground">{arq.rota || arq.placa}</TableCell>
                              <TableCell>
                                <Badge variant="outline" className="bg-[#222] border-[#333] text-[10px]">
                                  {arq.tipo.toUpperCase()}
                                </Badge>
                              </TableCell>
                              <TableCell className="text-right">
                                <Button 
                                  variant="ghost" 
                                  size="sm" 
                                  className="h-8 w-8 p-0 hover:bg-blue-500/20 hover:text-blue-500"
                                  onClick={() => handleDownload(details.uuid, arq.tipo, arq.chave_nfe)}
                                >
                                  <Download className="w-4 h-4" />
                                </Button>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </div>
                </div>
              </ScrollArea>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center p-12 text-center text-muted-foreground">
                <FileText className="w-16 h-16 opacity-10 mb-4" />
                <p>Erro ao carregar detalhes do processamento.</p>
              </div>
            )
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-12 text-center text-muted-foreground">
              <History className="w-20 h-20 opacity-5 mb-6" />
              <h2 className="text-xl font-medium text-[#e0e0e0]">Selecione um lote</h2>
              <p className="max-w-xs mt-2">Escolha um processamento na lista ao lado para visualizar os detalhes e baixar os arquivos.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Historico;
