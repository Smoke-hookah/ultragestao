"""Orquestrador principal do processamento."""

from typing import List, Dict, Tuple, Optional
from datetime import datetime
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import time
import os
import re
import unicodedata

from utils.logger import logger
from utils.validators import normalizar_chave_acesso, validar_linha_planilha
from models.alocacao import Alocacao, ResultadoProcessamento
from services.excel_reader import LeitorPlanilha
from services.api_client import ClienteAPI
from services.api_client_pool import ApiClientPool
from services.alocacao_filters import filtrar_alocacoes
from services.xml_builder import ConstrutorXML
from services.gestor_saida import GestorSaida
from services.leitor_xml import LeitorXML
from services.danfe_local import (
    DanfeLocalError,
    escolher_executor_local_pdf,
    gerar_pdf_danfe_bytes,
    gerar_pdf_danfe_task,
)
from services.historico_put import criar_historico_padrao
from services.historico_boletos import criar_historico_boletos_padrao
from config import (
    API_KEYS,
    POST_PUT_WAIT_SECONDS,
    GET_RETRY_ROUNDS,
    GET_RETRY_BASE_DELAY_SECONDS,
    GET_RETRY_MAX_DELAY_SECONDS,
    MIGRATE_HISTORY_API_KEY,
)
from services.historico_service import HistoricoService

from utils.progress import progresso_atual


class Orquestrador:
    """Orquestra o processamento de planilhas de alocação."""
    
    def __init__(self):
        """Inicializa o orquestrador."""
        # Cliente padrão (mantém compatibilidade com métodos legados)
        self.cliente_api = ClienteAPI(api_key=API_KEYS[0] if API_KEYS else None)
        # Pool para paralelismo com múltiplas Api-Key (opcional: pode estar vazio em modo local)
        self.api_pool = ApiClientPool(API_KEYS) if API_KEYS else None
        self.construtor_xml = ConstrutorXML()
        self.gestor_saida = GestorSaida()
        self.resultados: List[ResultadoProcessamento] = []
        self._boletos_relatorio: dict = {}
        self.processamento_uuid: Optional[str] = None
    
    def processar_planilha(
        self,
        caminho_planilha: str,
        tipo_separacao: str = "placa",  # 'placa' ou 'rota'
        baixar_pdf: bool = True,
        baixar_xml: bool = False,
        metodo_pdf: str = "api",
        pasta_xmls: Optional[str] = None,
        juntar_pdfs: bool = False,
        caminho_boletos_pdf: Optional[str] = None,
        filtro_rotas: Optional[List[str]] = None,
        filtro_placas: Optional[List[str]] = None,
        filtro_clientes: Optional[List[str]] = None,
        alocacoes_precarregadas: Optional[List[Alocacao]] = None,
        separar_em_pastas: bool = True,
    ) -> Tuple[bool, List[ResultadoProcessamento]]:
        """
        Processa uma planilha de alocação completa.
        
        Args:
            caminho_planilha: Caminho do arquivo .xlsx
            tipo_separacao: Como separar os arquivos ('placa' ou 'rota')
            baixar_pdf: Se deve baixar o PDF
            baixar_xml: Se deve baixar o XML
            metodo_pdf: 'api' (padrão), 'local' (teste), 'api_fallback_local' (tenta API e gera local se falhar)
        
        Returns:
            Tupla (sucesso_geral, lista_resultados)
        """
        self.resultados = []
        self._boletos_relatorio = {}
        
        try:
            # Fixar pasta da execução (data/hora) uma vez
            self.gestor_saida.iniciar_execucao()

            historico = criar_historico_padrao()
            dados_historico = historico.carregar()

            # Ler planilha (ou reutilizar parse já feito para filtros)
            logger.info(f"Iniciando processamento de: {caminho_planilha}")
            leitor: Optional[LeitorPlanilha] = None
            if alocacoes_precarregadas is not None:
                alocacoes = list(alocacoes_precarregadas)
                logger.info(f"Reutilizando alocações já lidas: {len(alocacoes)}")
            else:
                leitor = LeitorPlanilha(caminho_planilha)
                alocacoes = leitor.ler_alocacoes()

            # Nome da planilha (para metadados de saída/logs)
            nome_planilha = (
                getattr(leitor, 'nome_arquivo', None)
                or Path(caminho_planilha).name
            )

            # Aplicar filtros avançados (lógica OR entre categorias)
            if filtro_rotas or filtro_placas or filtro_clientes:
                antes = len(alocacoes)
                alocacoes = filtrar_alocacoes(
                    alocacoes,
                    filtro_rotas=filtro_rotas,
                    filtro_placas=filtro_placas,
                    filtro_clientes=filtro_clientes,
                )
                logger.info(f"Filtros aplicados: {len(alocacoes)}/{antes} alocações selecionadas")
            
            logger.info(f"Total de alocações a processar: {len(alocacoes)}")
            
            # Registrar início no histórico
            self.processamento_uuid = HistoricoService.criar_processamento(
                planilha_nome=nome_planilha,
                tipo_separacao=tipo_separacao,
                filtros={
                    "rotas": filtro_rotas,
                    "placas": filtro_placas,
                    "clientes": filtro_clientes
                }
            ).uuid

            if not alocacoes:
                logger.warning("Nenhuma alocação encontrada na planilha")
                HistoricoService.atualizar_processamento(
                    self.processamento_uuid,
                    status="concluido",
                    mensagem="Nenhuma alocação encontrada",
                    resumo={"sucesso": 0, "falha": 0, "total": 0}
                )
                return False, []

            # Fallback de pasta_xmls: quando o método precisa de XML local e a pasta não foi informada,
            # tenta reutilizar a pasta salva pela UI (usada pelo endpoint /api/processar-local).
            # A pasta de XMLs alimenta todo o fluxo atual:
            # - PUT para a API, quando metodo_pdf='api'
            # - geração local de DANFE, quando metodo_pdf='local'
            # - fallback local, quando metodo_pdf='api_fallback_local'
            usar_xml_local = bool(pasta_xmls)
            xml_local_obrigatorio = bool(pasta_xmls)

            if not pasta_xmls:
                try:
                    from utils.ui import obter_pasta_xmls_salva

                    pasta_salva = (obter_pasta_xmls_salva() or "").strip()
                    if pasta_salva:
                        pasta_xmls = pasta_salva
                        logger.info(f"Usando pasta_xmls salva na UI: {pasta_xmls}")
                except Exception as e:
                    logger.debug(f"Não foi possível obter pasta_xmls salva na UI: {e}")

            # Recalcular após possível preenchimento via UI
            usar_xml_local = bool(pasta_xmls)
            xml_local_obrigatorio = bool(pasta_xmls)

            # Carregar XMLs (uma vez) e indexar por chave
            mapa_xml_por_chave = {}
            mapa_caminho_xml_por_chave = {}
            leitor_xml = None
            if pasta_xmls and usar_xml_local:
                logger.info(f"Indexando XMLs por chave em: {pasta_xmls}")
                leitor_xml = LeitorXML(pasta_xmls)

                chaves_desejadas = set(
                    normalizar_chave_acesso(getattr(a, "chave", "")) for a in alocacoes if getattr(a, 'chave', None)
                )
                mapa_caminho_xml_por_chave, stats_xml = leitor_xml.carregar_mapa_chave_para_caminho(chaves_desejadas)
                logger.info(
                    "XMLs (índice rápido): "
                    f"total={stats_xml['total']} mapeadas={stats_xml['mapeadas']} duplicadas={stats_xml['duplicadas']} "
                    f"erros={stats_xml['erros']} lidos_conteudo={stats_xml['lidos_conteudo']} "
                    f"ignorados_tipo={stats_xml.get('ignorados_tipo', 0)} "
                    f"filtradas={stats_xml['filtradas']} faltantes={stats_xml['faltantes']}"
                )
                progresso_atual["etapa"] = "indexacao"
                progresso_atual["percentual"] = 5
                progresso_atual["mensagem"] = f"XMLs indexados: {stats_xml['mapeadas']} de {stats_xml['total']}"
                progresso_atual["detalhes"] = ""

            # Pré-criar resultados para atualizar em fases
            resultados_por_chave = {}
            for alocacao in alocacoes:
                resultados_por_chave[str(alocacao.chave).strip()] = ResultadoProcessamento(
                    alocacao=alocacao,
                    sucesso=False,
                    etapa="inicio",
                    mensagem=""
                )

            # Normalizar método de PDF
            metodo_pdf = (metodo_pdf or "api").strip().lower()
            metodos_validos = {"api", "local", "api_fallback_local"}
            if metodo_pdf not in metodos_validos:
                raise ValueError(
                    f"metodo_pdf inválido: {metodo_pdf}. Use um de: {sorted(metodos_validos)}"
                )
            if metodo_pdf == "api_fallback_local" and self.api_pool is None and baixar_pdf:
                logger.warning(
                    "API_KEYS ausentes para api_fallback_local; usando geracao local de DANFE para garantir o lote."
                )
                metodo_pdf = "local"

            def _valor_separacao_com_id(aloc: Alocacao) -> str:
                base = aloc.placa if tipo_separacao == "placa" else aloc.rota
                base = str(base or "").strip()
                if aloc.id_quebra:
                    return f"{base} ({aloc.id_quebra})".strip()
                return base
            
            # Vincular XML + validar (antes das fases PUT/GET)
            alocacoes_validas: List[Alocacao] = []
            chaves_dados_invalidos: List[str] = []
            chaves_xml_nao_encontrado: List[str] = []
            for idx, alocacao in enumerate(alocacoes, 1):
                chave_str = normalizar_chave_acesso(alocacao.chave) or str(alocacao.chave).strip()
                logger.info(f"Preparando {idx}/{len(alocacoes)}: {chave_str}")

                # Vincular XML da pasta pela chave
                if usar_xml_local and not alocacao.xml:
                    caminho_xml = mapa_caminho_xml_por_chave.get(chave_str)
                    if caminho_xml and leitor_xml is not None:
                        ok_ler, conteudo_ou_erro = leitor_xml.ler_xml(Path(caminho_xml))
                        if ok_ler:
                            alocacao.xml = conteudo_ou_erro

                # Validar dados da linha
                if not validar_linha_planilha(alocacao.to_dict(), tipo_separacao):
                    r = resultados_por_chave[chave_str]
                    r.etapa = "validacao"
                    r.mensagem = "Dados inválidos"
                    self.resultados.append(r)
                    chaves_dados_invalidos.append(chave_str)
                    continue

                # Se precisa usar XML da pasta, ele é obrigatório
                if xml_local_obrigatorio and not alocacao.xml:
                    r = resultados_por_chave[chave_str]
                    r.etapa = "validacao"
                    r.mensagem = "XML não encontrado na pasta para esta chave"
                    self.resultados.append(r)
                    chaves_xml_nao_encontrado.append(chave_str)
                    continue

                alocacoes_validas.append(alocacao)

            # Resumo completo do pré-processamento (por que X != Y)
            logger.info("\n" + "=" * 60)
            logger.info("RESUMO - PRÉ-PROCESSAMENTO")
            logger.info("=" * 60)
            logger.info(f"Chaves na planilha (lidas): {len(alocacoes)}")
            logger.info(f"Prontas para PUT/GET: {len(alocacoes_validas)}")
            logger.info(f"Ignoradas (dados inválidos): {len(chaves_dados_invalidos)}")
            logger.info(f"Ignoradas (XML não encontrado): {len(chaves_xml_nao_encontrado)}")

            if chaves_xml_nao_encontrado:
                logger.info("\nCHAVES SEM XML NA PASTA (por chave):")
                for chave in chaves_xml_nao_encontrado:
                    logger.info(f"- {chave}")

            if chaves_dados_invalidos:
                logger.info("\nCHAVES COM DADOS INVÁLIDOS (por chave):")
                for chave in chaves_dados_invalidos:
                    logger.info(f"- {chave}")
            logger.info("=" * 60 + "\n")
            
            progresso_atual["etapa"] = "validacao"
            progresso_atual["percentual"] = 10
            progresso_atual["mensagem"] = f"Validação concluída: {len(alocacoes_validas)} alocações válidas"
            progresso_atual["detalhes"] = ""

            if not alocacoes_validas:
                logger.warning("Nenhuma alocação válida para processar")
                return False, self.resultados

            # MODO LOCAL: gerar PDF sem chamar API (util para testes e lotes grandes)
            if metodo_pdf == "local" and baixar_pdf:
                total_local = len(alocacoes_validas)
                executor_mode, max_workers = escolher_executor_local_pdf(total_local)
                logger.info(
                    "Modo PDF=local: gerando DANFE em PDF a partir do XML "
                    f"(executor={executor_mode}, workers={max_workers}, lote={total_local})"
                )

                progresso_atual["etapa"] = "danfe_local"
                progresso_atual["percentual"] = 15
                progresso_atual["mensagem"] = f"Gerando {total_local} PDFs locais..."
                progresso_atual["detalhes"] = (
                    f"Executor: {executor_mode} com {max_workers} worker(s)"
                )

                pdf_dir_por_chave: dict[str, Path] = {}
                xml_dir_por_chave: dict[str, Path] = {}
                alocacao_por_chave: dict[str, Alocacao] = {}
                for aloc in alocacoes_validas:
                    chave_str = str(aloc.chave).strip()
                    valor_dir = _valor_separacao_com_id(aloc)
                    estrutura = self.gestor_saida.criar_estrutura_diretorios(tipo_separacao, valor_dir, separar_em_pastas=separar_em_pastas)
                    pdf_dir_por_chave[chave_str] = estrutura / "pdf"
                    xml_dir_por_chave[chave_str] = estrutura / "xml"
                    alocacao_por_chave[chave_str] = aloc

                def _persistir_local(chave_str: str, pdf_bytes: bytes) -> tuple[str, str]:
                    alocacao = alocacao_por_chave.get(chave_str)
                    pdf_dir = pdf_dir_por_chave.get(chave_str)
                    xml_dir = xml_dir_por_chave.get(chave_str)
                    if alocacao is None or pdf_dir is None:
                        raise RuntimeError("Pasta de saida nao encontrada para salvar PDF")

                    caminho_pdf = pdf_dir / f"NFE-{chave_str}.pdf"
                    caminho_pdf.write_bytes(pdf_bytes)
                    
                    # Registrar PDF no histórico
                    if self.processamento_uuid:
                        HistoricoService.registrar_arquivo(
                            self.processamento_uuid,
                            chave_nfe=chave_str,
                            tipo="pdf",
                            caminho_local=str(caminho_pdf),
                            cliente=alocacao.cliente,
                            valor=alocacao.valor_total,
                            rota=alocacao.rota,
                            placa=alocacao.placa
                        )

                    caminho_xml_s = ""
                    if baixar_xml and xml_dir is not None:
                        caminho_xml = xml_dir / f"NFE-{chave_str}.xml"
                        caminho_xml.write_text(alocacao.xml or "", encoding="utf-8")
                        caminho_xml_s = str(caminho_xml)
                        
                        # Registrar XML no histórico
                        if self.processamento_uuid:
                            HistoricoService.registrar_arquivo(
                                self.processamento_uuid,
                                chave_nfe=chave_str,
                                tipo="xml",
                                caminho_local=caminho_xml_s,
                                cliente=alocacao.cliente,
                                valor=alocacao.valor_total,
                                rota=alocacao.rota,
                                placa=alocacao.placa
                            )

                    return str(caminho_pdf), caminho_xml_s

                def _executar_lote_local(executor_cls, modo_nome: str) -> None:
                    processados = 0
                    with executor_cls(max_workers=max_workers) as ex:
                        futs = [
                            ex.submit(gerar_pdf_danfe_task, a.chave, a.xml or "")
                            for a in alocacoes_validas
                        ]
                        for fut in as_completed(futs):
                            chave_str, ok, pdf_bytes, msg = fut.result()
                            r = resultados_por_chave.get(chave_str)
                            if not r:
                                continue

                            pdf_path = ""
                            xml_path = ""
                            if ok and pdf_bytes:
                                try:
                                    pdf_path, xml_path = _persistir_local(chave_str, pdf_bytes)
                                except Exception as exc:
                                    ok = False
                                    msg = f"Erro ao salvar DANFE local: {exc}"

                            r.sucesso = bool(ok)
                            r.etapa = "concluido" if ok else "danfe_local"
                            r.mensagem = msg
                            if pdf_path:
                                r.arquivo_pdf = pdf_path
                            if xml_path:
                                r.arquivo_xml = xml_path
                            if r not in self.resultados:
                                self.resultados.append(r)

                            processados += 1
                            percentual_local = 15 + int((processados / total_local) * 50)
                            progresso_atual["etapa"] = "danfe_local"
                            progresso_atual["percentual"] = min(percentual_local, 65)
                            progresso_atual["mensagem"] = (
                                f"Gerando PDFs locais: {processados}/{total_local}"
                            )
                            progresso_atual["detalhes"] = (
                                f"Executor: {modo_nome} com {max_workers} worker(s)"
                            )

                if executor_mode == "process":
                    try:
                        _executar_lote_local(ProcessPoolExecutor, "process")
                    except Exception as exc:
                        logger.warning(
                            "ProcessPool no modo local falhou; "
                            f"reprocessando com threads. Erro: {exc}"
                        )
                        progresso_atual["detalhes"] = (
                            "Process pool indisponivel; reiniciando com threads"
                        )
                        _executar_lote_local(ThreadPoolExecutor, "thread")
                else:
                    _executar_lote_local(ThreadPoolExecutor, "thread")

                # Sem fase PUT/GET em modo local. Segue para pos-processamento abaixo.
                pendentes: List[Alocacao] = []
                chaves_put_puladas: set[str] = set()

            else:
                # Modos que dependem de API precisam de pool
                if self.api_pool is None:
                    raise ValueError(
                        "API_KEYS não configurada(s), mas metodo_pdf requer API. "
                        "Defina API_KEY/API_KEYS no .env, ou use metodo_pdf='local'."
                    )

                # FASE 1: PUT (upload) em lote
                logger.info(f"FASE 1/2: Enviando XMLs (PUT) para {len(alocacoes_validas)} alocações...")
                progresso_atual["etapa"] = "put"
                progresso_atual["percentual"] = 15
                progresso_atual["mensagem"] = f"Iniciando envio de {len(alocacoes_validas)} XMLs..."
                progresso_atual["detalhes"] = ""
                falhas_put = 0
                put_ok = 0
                put_pulado_historico = 0
                chaves_put_puladas: set[str] = set()
                api_key_preferida_por_chave: dict[str, str] = {}
                erros_put: List[tuple[str, str]] = []

                # Pré-validações (baratas) + montar lista de PUTs
                put_tasks: List[tuple[str, str]] = []  # (chave, xml)
                historico_alterado = False
                last_good_api_key: Optional[str] = None

                def _descobrir_api_key_por_get(chave: str) -> Optional[str]:
                    """Tenta descobrir qual Api-Key enxerga a NF na Área do Cliente.

                    Regra: no máximo 1 tentativa por Api-Key (até 5). Retorna a Api-Key encontrada.
                    """

                    nonlocal last_good_api_key

                    if not MIGRATE_HISTORY_API_KEY:
                        return None
                    if not getattr(self.api_pool, "api_keys", None):
                        return None
                    if len(self.api_pool.api_keys) <= 1:
                        return None
                    # Sem nenhum GET para fazer, não há como "provar" onde está.
                    if not baixar_pdf and not baixar_xml:
                        return None

                    # Tenta primeiro a última Api-Key que deu certo (normalmente acelera muito).
                    keys_to_try = []
                    if last_good_api_key and last_good_api_key in self.api_pool.api_keys:
                        keys_to_try.append(last_good_api_key)
                    keys_to_try.extend([k for k in self.api_pool.api_keys if k not in keys_to_try])

                    for k in keys_to_try:
                        try:
                            def call(client: ClienteAPI):
                                if baixar_pdf:
                                    return client.baixar_pdf(chave)
                                return client.baixar_xml(chave)

                            ok, payload, resp = self.api_pool.with_client_for_api_key(k, call)
                            if ok:
                                last_good_api_key = k
                                return k

                            # 404: não está nesta conta; tenta próxima Api-Key
                            if getattr(resp, "codigo", None) == 404:
                                continue

                            # Outros erros: não conclui, mas tenta próxima Api-Key
                            continue
                        except Exception:
                            continue
                    return None

                for alocacao in alocacoes_validas:
                    chave_str = str(alocacao.chave).strip()
                    r = resultados_por_chave[chave_str]

                    # Se já teve PUT recente (<= 60 dias), pula PUT
                    if historico.dentro_da_validade(chave_str, dados_historico):
                        r.etapa = "upload_xml"
                        r.mensagem = "PUT ignorado (enviado nos últimos 60 dias)"
                        put_pulado_historico += 1
                        chaves_put_puladas.add(chave_str)

                        api_key_hist = historico.api_key_para_chave(chave_str, dados_historico)
                        if api_key_hist:
                            api_key_preferida_por_chave[chave_str] = api_key_hist
                        else:
                            # Migração (legado): tenta descobrir qual Api-Key enxerga a NF e grava no histórico
                            api_key_descoberta = _descobrir_api_key_por_get(chave_str)
                            if api_key_descoberta:
                                api_key_preferida_por_chave[chave_str] = api_key_descoberta
                                entry = dados_historico.get(chave_str)
                                if isinstance(entry, dict):
                                    entry["api_key"] = api_key_descoberta
                                    dados_historico[chave_str] = entry
                                    historico_alterado = True
                        continue

                    r.etapa = "upload_xml"
                    xml_enviado = alocacao.xml
                    if not xml_enviado:
                        r.mensagem = "XML não fornecido"
                        falhas_put += 1
                        erros_put.append((chave_str, r.mensagem))
                        continue

                    if not self.construtor_xml.validar_xml(xml_enviado):
                        r.mensagem = "XML inválido"
                        falhas_put += 1
                        erros_put.append((chave_str, r.mensagem))
                        continue

                    put_tasks.append((chave_str, xml_enviado))

                if historico_alterado:
                    # Salva a migração do histórico antes das fases (especialmente quando PUT for todo pulado).
                    historico.salvar(dados_historico)

                def _do_put(task: tuple[str, str]) -> tuple[str, bool, str]:
                    chave, xml = task

                    def call(client: ClienteAPI):
                        return client.enviar_xml(xml)

                    api_key_used, (ok, resp) = self.api_pool.with_client_info(call)
                    if ok:
                        # Persistir qual Api-Key foi usada para que o GET use a mesma conta/Área do Cliente
                        api_key_preferida_por_chave[chave] = api_key_used
                        return chave, True, "PUT OK"
                    return chave, False, f"Erro no PUT: {resp.mensagem}"

                if put_tasks:
                    total_put_tasks = len(put_tasks)
                    with ThreadPoolExecutor(max_workers=self.api_pool.stats.total_keys) as ex:
                        futs = [ex.submit(_do_put, t) for t in put_tasks]
                        for idx, fut in enumerate(as_completed(futs), 1):
                            chave, ok, msg = fut.result()
                            r = resultados_por_chave[chave]
                            r.etapa = "upload_xml"
                            r.mensagem = msg
                            if ok:
                                put_ok += 1
                                dados_historico = historico.registrar_sucesso(
                                    chave,
                                    api_key_preferida_por_chave.get(chave),
                                    dados_historico,
                                )
                            else:
                                falhas_put += 1
                                erros_put.append((chave, msg))
                            
                            # Atualizar progresso (PUT = 15-40%)
                            percentual_put = 15 + int((idx / total_put_tasks) * 25)
                            progresso_atual["etapa"] = "put"
                            progresso_atual["percentual"] = percentual_put
                            progresso_atual["mensagem"] = f"Enviando XMLs: {idx}/{total_put_tasks}"
                            progresso_atual["detalhes"] = f"Última chave: {chave[:8]}..."

                # Persistir histórico atualizado
                historico.salvar(dados_historico)

                # Resumo completo da fase PUT
                logger.info("\n" + "=" * 60)
                logger.info("RESUMO - FASE PUT (UPLOAD XML)")
                logger.info("=" * 60)
                logger.info(f"Total válidas: {len(alocacoes_validas)}")
                logger.info(f"PUT OK: {put_ok}")
                logger.info(f"PUT pulado (histórico 60d): {put_pulado_historico}")
                logger.info(f"PUT com erro: {falhas_put}")

                if erros_put:
                    logger.info("\nERROS COMPLETOS DO PUT (por chave):")
                    for chave, msg in erros_put:
                        logger.info(f"- {chave}: {msg}")
                logger.info("=" * 60 + "\n")

                if falhas_put > 0:
                    logger.warning(
                        f"FASE 1 falhou: {falhas_put} PUT(s) com erro. GET não será executado."
                    )
                    # Publicar resultados (inclui os válidos e os inválidos já adicionados)
                    for alocacao in alocacoes_validas:
                        chave_str = str(alocacao.chave).strip()
                        if resultados_por_chave[chave_str] not in self.resultados:
                            self.resultados.append(resultados_por_chave[chave_str])
                    return False, self.resultados

                # FASE 2: GET (downloads) somente após todos PUT OK
                logger.info("FASE 2/2: Baixando arquivos (GET)...")
                progresso_atual["etapa"] = "get"
                progresso_atual["percentual"] = 42
                progresso_atual["mensagem"] = "Iniciando download de arquivos..."
                progresso_atual["detalhes"] = ""

                if POST_PUT_WAIT_SECONDS and POST_PUT_WAIT_SECONDS > 0:
                    logger.info(
                        f"Aguardando {POST_PUT_WAIT_SECONDS:.0f}s para a API disponibilizar os documentos..."
                    )
                    time.sleep(POST_PUT_WAIT_SECONDS)

                # Rodadas de GET: mantém paralelismo alto e trata 404 como 'pendente' (não falha imediato).
                pendentes: List[Alocacao] = list(alocacoes_validas)

                def _do_get_once(
                    alocacao: Alocacao,
                ) -> tuple[str, Optional[str], Optional[str], bool, list[str]]:
                    """Uma tentativa de GET para (pdf/xml).

                    Retorna pending=True quando a API ainda não tem a NF (404).
                    """

                    chave_str = str(alocacao.chave).strip()
                    valor_separacao = _valor_separacao_com_id(alocacao)
                    msgs: list[str] = []
                    pending = False

                    r = resultados_por_chave[chave_str]
                    arquivo_pdf = r.arquivo_pdf
                    arquivo_xml = r.arquivo_xml

                    def call(client: ClienteAPI) -> tuple[Optional[str], Optional[str], bool, list[str]]:
                        local_msgs: list[str] = []
                        local_pending = False
                        local_pdf = arquivo_pdf
                        local_xml = arquivo_xml

                        if baixar_pdf and not local_pdf:
                            ok_pdf, pdf_bytes, resp_pdf = client.baixar_pdf(alocacao.chave)
                            if ok_pdf and pdf_bytes:
                                ok_save, path_pdf = self.gestor_saida.salvar_pdf(
                                    pdf_bytes,
                                    nome_planilha,
                                    tipo_separacao,
                                    valor_separacao,
                                    alocacao.chave,
                                    separar_em_pastas=separar_em_pastas
                                )
                                if ok_save:
                                    local_pdf = path_pdf
                                    # Registrar PDF no histórico (Modo API)
                                    if self.processamento_uuid:
                                        HistoricoService.registrar_arquivo(
                                            self.processamento_uuid,
                                            chave_nfe=str(alocacao.chave).strip(),
                                            tipo="pdf",
                                            caminho_local=path_pdf,
                                            cliente=alocacao.cliente,
                                            valor=alocacao.valor_total,
                                            rota=alocacao.rota,
                                            placa=alocacao.placa
                                        )
                            else:
                                # Fallback local quando solicitado
                                if metodo_pdf == "api_fallback_local" and (alocacao.xml or "").strip():
                                    try:
                                        pdf_local = gerar_pdf_danfe_bytes(alocacao.xml)
                                        ok_save, path_pdf = self.gestor_saida.salvar_pdf(
                                            pdf_local,
                                            nome_planilha,
                                            tipo_separacao,
                                            valor_separacao,
                                            alocacao.chave,
                                            separar_em_pastas=separar_em_pastas
                                        )
                                        if ok_save:
                                            local_pdf = path_pdf
                                            # Registrar PDF no histórico (Modo API Fallback)
                                            if self.processamento_uuid:
                                                HistoricoService.registrar_arquivo(
                                                    self.processamento_uuid,
                                                    chave_nfe=str(alocacao.chave).strip(),
                                                    tipo="pdf",
                                                    caminho_local=path_pdf,
                                                    cliente=alocacao.cliente,
                                                    valor=alocacao.valor_total,
                                                    rota=alocacao.rota,
                                                    placa=alocacao.placa
                                                )
                                    except Exception as e:
                                        if getattr(resp_pdf, "codigo", None) == 404:
                                            local_pending = True
                                        else:
                                            local_msgs.append(
                                                f"Erro no GET PDF: {resp_pdf.mensagem} | Fallback local: {e}"
                                            )

                                # Se não gerou local, mantém o comportamento padrão do GET
                                if not local_pdf:
                                    if getattr(resp_pdf, "codigo", None) == 404:
                                        local_pending = True
                                    else:
                                        local_msgs.append(f"Erro no GET PDF: {resp_pdf.mensagem}")

                        if baixar_xml and not local_xml:
                            ok_xml, xml_baixado, resp_xml = client.baixar_xml(alocacao.chave)
                            if ok_xml and xml_baixado:
                                ok_save, path_xml = self.gestor_saida.salvar_xml(
                                    xml_baixado,
                                    nome_planilha,
                                    tipo_separacao,
                                    valor_separacao,
                                    alocacao.chave,
                                    separar_em_pastas=separar_em_pastas
                                )
                                if ok_save:
                                    local_xml = path_xml
                                    # Registrar XML no histórico (Modo API)
                                    if self.processamento_uuid:
                                        HistoricoService.registrar_arquivo(
                                            self.processamento_uuid,
                                            chave_nfe=str(alocacao.chave).strip(),
                                            tipo="xml",
                                            caminho_local=path_xml,
                                            cliente=alocacao.cliente,
                                            valor=alocacao.valor_total,
                                            rota=alocacao.rota,
                                            placa=alocacao.placa
                                        )
                            else:
                                if getattr(resp_xml, "codigo", None) == 404:
                                    local_pending = True
                                else:
                                    local_msgs.append(f"Erro no GET XML: {resp_xml.mensagem}")

                        return local_pdf, local_xml, local_pending, local_msgs

                    api_key_pref = api_key_preferida_por_chave.get(chave_str)
                    if api_key_pref:
                        arquivo_pdf2, arquivo_xml2, pending2, msgs2 = self.api_pool.with_client_for_api_key(
                            api_key_pref, call
                        )
                    else:
                        arquivo_pdf2, arquivo_xml2, pending2, msgs2 = self.api_pool.with_client(call)

                    if arquivo_pdf2:
                        arquivo_pdf = arquivo_pdf2
                    if arquivo_xml2:
                        arquivo_xml = arquivo_xml2
                    if pending2:
                        pending = True
                    msgs.extend(msgs2)

                    return chave_str, arquivo_pdf, arquivo_xml, pending, msgs

                max_rodadas = max(1, int(GET_RETRY_ROUNDS))
                delay_base = float(GET_RETRY_BASE_DELAY_SECONDS)
                delay_max = float(GET_RETRY_MAX_DELAY_SECONDS)

                for rodada in range(1, max_rodadas + 1):
                    if not pendentes:
                        break

                    logger.info(f"GET - rodada {rodada}/{max_rodadas} (pendentes: {len(pendentes)})")
                    proximos_pendentes: List[Alocacao] = []

                    with ThreadPoolExecutor(max_workers=self.api_pool.stats.total_keys) as ex:
                        futs = [ex.submit(_do_get_once, a) for a in pendentes]
                        for fut in as_completed(futs):
                            chave_str, arquivo_pdf, arquivo_xml, pending, msgs = fut.result()
                            r = resultados_por_chave[chave_str]

                            if arquivo_pdf:
                                r.arquivo_pdf = arquivo_pdf
                            if arquivo_xml:
                                r.arquivo_xml = arquivo_xml

                            if msgs:
                                r.sucesso = False
                                r.etapa = "download"
                                r.mensagem = " | ".join(msgs)
                                if r not in self.resultados:
                                    self.resultados.append(r)
                                continue

                            # Se ainda está pendente (404), não falha agora — re-enfileira.
                            if pending:
                                r.sucesso = False
                                r.etapa = "download"
                                r.mensagem = (
                                    f"Aguardando disponibilização na API (tentativa {rodada}/{max_rodadas})"
                                )
                                proximos_pendentes.append(r.alocacao)
                                continue

                            # Concluiu o que precisava baixar
                            r.sucesso = True
                            r.etapa = "concluido"
                            if r.mensagem == "":
                                r.mensagem = "Processamento concluído com sucesso"
                            if r not in self.resultados:
                                self.resultados.append(r)

                    pendentes = proximos_pendentes
                    if pendentes and rodada < max_rodadas:
                        delay = min(delay_max, delay_base * (2 ** (rodada - 1)))
                        if delay > 0:
                            logger.info(f"Aguardando {delay:.1f}s antes da próxima rodada de GET...")
                            time.sleep(delay)

                # Fallback: se o PUT foi pulado pelo histórico local mas o GET nunca encontrou,
                # forçar PUT apenas para as chaves ainda pendentes e tentar GET novamente.
                if pendentes and chaves_put_puladas:
                    pendentes_chaves = {str(a.chave).strip() for a in pendentes}
                    candidatos = [
                        a for a in pendentes if str(a.chave).strip() in chaves_put_puladas
                    ]
                    if candidatos:
                        logger.warning(
                            "Algumas chaves continuam 404 após as rodadas de GET, "
                            "mas o PUT foi pulado pelo histórico local. "
                            f"Forçando PUT em {len(candidatos)}/{len(pendentes_chaves)} pendentes e tentando GET novamente..."
                        )

                        put_tasks2: List[tuple[str, str]] = []
                        for aloc in candidatos:
                            chave_str = str(aloc.chave).strip()
                            xml_enviado = aloc.xml
                            if not xml_enviado:
                                r = resultados_por_chave[chave_str]
                                r.sucesso = False
                                r.etapa = "upload_xml"
                                r.mensagem = "Fallback PUT não executado: XML não disponível"
                                if r not in self.resultados:
                                    self.resultados.append(r)
                                continue
                            if not self.construtor_xml.validar_xml(xml_enviado):
                                r = resultados_por_chave[chave_str]
                                r.sucesso = False
                                r.etapa = "upload_xml"
                                r.mensagem = "Fallback PUT não executado: XML inválido"
                                if r not in self.resultados:
                                    self.resultados.append(r)
                                continue
                            put_tasks2.append((chave_str, xml_enviado))

                        def _do_put_force(task: tuple[str, str]) -> tuple[str, bool, str]:
                            chave, xml = task

                            def call(client: ClienteAPI):
                                return client.enviar_xml(xml)

                            api_key_pref = api_key_preferida_por_chave.get(chave)
                            if api_key_pref:
                                ok, resp = self.api_pool.with_client_for_api_key(api_key_pref, call)
                                api_key_used = api_key_pref
                            else:
                                api_key_used, (ok, resp) = self.api_pool.with_client_info(call)

                            if ok:
                                api_key_preferida_por_chave[chave] = api_key_used
                                return chave, True, "PUT OK (fallback)"
                            return chave, False, f"Erro no PUT (fallback): {resp.mensagem}"

                        chaves_put_fallback_ok: set[str] = set()
                        erros_put_fallback: List[tuple[str, str]] = []

                        if put_tasks2:
                            with ThreadPoolExecutor(max_workers=self.api_pool.stats.total_keys) as ex:
                                futs = [ex.submit(_do_put_force, t) for t in put_tasks2]
                                for fut in as_completed(futs):
                                    chave, ok, msg = fut.result()
                                    r = resultados_por_chave[chave]
                                    r.etapa = "upload_xml"
                                    r.mensagem = msg
                                    if ok:
                                        chaves_put_fallback_ok.add(chave)
                                        dados_historico = historico.registrar_sucesso(
                                            chave,
                                            api_key_preferida_por_chave.get(chave),
                                            dados_historico,
                                        )
                                    else:
                                        erros_put_fallback.append((chave, msg))

                            # Persistir histórico atualizado (fallback)
                            historico.salvar(dados_historico)

                        if erros_put_fallback:
                            logger.info("\nERROS DO PUT (FALLBACK) (por chave):")
                            for chave, msg in erros_put_fallback:
                                logger.info(f"- {chave}: {msg}")

                        if chaves_put_fallback_ok:
                            if POST_PUT_WAIT_SECONDS and POST_PUT_WAIT_SECONDS > 0:
                                logger.info(
                                    f"Aguardando {POST_PUT_WAIT_SECONDS:.0f}s após PUT (fallback) para a API disponibilizar os documentos..."
                                )
                                time.sleep(POST_PUT_WAIT_SECONDS)

                            # Re-tentar GET apenas para as chaves que tiveram PUT OK no fallback
                            pendentes2: List[Alocacao] = [
                                a for a in pendentes if str(a.chave).strip() in chaves_put_fallback_ok
                            ]
                            max_rodadas2 = max(1, min(3, max_rodadas))
                            delay_base2 = 1.0
                            delay_max2 = min(5.0, delay_max)

                            for rodada2 in range(1, max_rodadas2 + 1):
                                if not pendentes2:
                                    break
                                logger.info(
                                    f"GET (fallback) - rodada {rodada2}/{max_rodadas2} (pendentes: {len(pendentes2)})"
                                )
                                proximos_pendentes2: List[Alocacao] = []

                                with ThreadPoolExecutor(max_workers=self.api_pool.stats.total_keys) as ex:
                                    futs = [ex.submit(_do_get_once, a) for a in pendentes2]
                                    for fut in as_completed(futs):
                                        chave_str, arquivo_pdf, arquivo_xml, pending, msgs = fut.result()
                                        r = resultados_por_chave[chave_str]

                                        if arquivo_pdf:
                                            r.arquivo_pdf = arquivo_pdf
                                        if arquivo_xml:
                                            r.arquivo_xml = arquivo_xml

                                        if msgs:
                                            r.sucesso = False
                                            r.etapa = "download"
                                            r.mensagem = " | ".join(msgs)
                                            if r not in self.resultados:
                                                self.resultados.append(r)
                                            continue

                                        if pending:
                                            r.sucesso = False
                                            r.etapa = "download"
                                            r.mensagem = (
                                                f"Aguardando disponibilização na API (fallback {rodada2}/{max_rodadas2})"
                                            )
                                            proximos_pendentes2.append(r.alocacao)
                                            continue

                                        r.sucesso = True
                                        r.etapa = "concluido"
                                        if r.mensagem == "":
                                            r.mensagem = "Processamento concluído com sucesso"
                                        if r not in self.resultados:
                                            self.resultados.append(r)

                                pendentes2 = proximos_pendentes2
                                if pendentes2 and rodada2 < max_rodadas2:
                                    delay2 = min(delay_max2, delay_base2 * (2 ** (rodada2 - 1)))
                                    if delay2 > 0:
                                        logger.info(
                                            f"Aguardando {delay2:.1f}s antes da próxima rodada de GET (fallback)..."
                                        )
                                        time.sleep(delay2)

                            # Atualizar lista de pendentes original removendo quem resolveu no fallback
                            pendentes = [
                                a for a in pendentes if str(a.chave).strip() not in chaves_put_fallback_ok
                            ] + pendentes2

                    # Se ainda sobrou pendente após todas rodadas, marca como erro final
                    if pendentes:
                        for aloc in pendentes:
                            chave_str = str(aloc.chave).strip()
                            r = resultados_por_chave[chave_str]
                            r.sucesso = False
                            r.etapa = "download"
                            r.mensagem = f"NF-e não encontrada na Área do Cliente após {max_rodadas} tentativas"
                            if r not in self.resultados:
                                self.resultados.append(r)

                        logger.info("\nFALHAS NO DOWNLOAD (por chave):")
                        for aloc in pendentes:
                            chave_str = str(aloc.chave).strip()
                            r = resultados_por_chave[chave_str]
                            logger.info(f"- {chave_str}: {r.mensagem}")

            # Pós-processamento: juntar PDFs por (rota, placa, id_quebra)
            # (e anexar boletos no PDF final quando fornecido)
            boletos_por_grupo: dict[tuple[str, str, str], list[str]] = {}

            # Relatório detalhado de boletos por chave (para UI)
            boletos_por_chave: dict[str, dict] = {}

            # Boletos: extrair/salvar em qualquer modo (juntar_pdfs ON ou OFF)
            if baixar_pdf:
                historico_boletos = criar_historico_boletos_padrao()

                def _digits_only(v: str) -> str:
                    return "".join(ch for ch in str(v or "") if ch.isdigit())

                def _common_suffix_len(a: str, b: str) -> int:
                    if not a or not b:
                        return 0
                    i = 0
                    while i < len(a) and i < len(b) and a[-1 - i] == b[-1 - i]:
                        i += 1
                    return i

                def _normalizar_texto_busca(v: str) -> str:
                    texto = unicodedata.normalize("NFKD", str(v or ""))
                    texto = texto.encode("ascii", "ignore").decode("ascii")
                    texto = re.sub(r"[^A-Z0-9]+", " ", texto.upper())
                    return re.sub(r"\s+", " ", texto).strip()

                def _tokens_relevantes(v: str) -> set[str]:
                    ignorar = {
                        "LTDA",
                        "EIRELI",
                        "ME",
                        "EPP",
                        "SA",
                        "S",
                        "DE",
                        "DA",
                        "DO",
                        "DAS",
                        "DOS",
                        "E",
                        "COMERCIO",
                        "COMERCIAL",
                        "SUPERMERCADO",
                        "MERCADO",
                        "MINIMERCADO",
                    }
                    return {
                        token
                        for token in _normalizar_texto_busca(v).split()
                        if len(token) >= 3 and token not in ignorar
                    }

                def _extrair_destinatario_xml(xml: str) -> tuple[str, str]:
                    xml_s = str(xml or "")
                    if not xml_s.strip():
                        return "", ""

                    bloco_dest = xml_s
                    match_dest = re.search(r"<dest\b.*?</dest>", xml_s, flags=re.IGNORECASE | re.DOTALL)
                    if match_dest:
                        bloco_dest = match_dest.group(0)

                    cnpj = ""
                    for tag in ("CNPJ", "CPF"):
                        match_doc = re.search(
                            rf"<{tag}>\s*([^<]+)\s*</{tag}>",
                            bloco_dest,
                            flags=re.IGNORECASE,
                        )
                        if match_doc:
                            cnpj = _digits_only(match_doc.group(1))
                            break

                    nome = ""
                    match_nome = re.search(
                        r"<xNome>\s*([^<]+)\s*</xNome>",
                        bloco_dest,
                        flags=re.IGNORECASE,
                    )
                    if match_nome:
                        nome = str(match_nome.group(1) or "").strip()

                    return cnpj, nome

                # Index rápido: chave -> NF (raw) e NF (digits)
                chave_para_nf: dict[str, str] = {}
                aloc_por_chave: dict[str, Alocacao] = {}
                aloc_com_nf_digits: list[tuple[Alocacao, str]] = []
                chave_para_dest_cnpj: dict[str, str] = {}
                chave_para_dest_tokens: dict[str, set[str]] = {}
                chave_para_valor_documento: dict[str, float] = {}
                for aloc in alocacoes_validas:
                    chave_str = str(aloc.chave).strip()
                    aloc_por_chave[chave_str] = aloc
                    nf_raw = str(getattr(aloc, "nf", "") or "").strip()
                    chave_para_nf[chave_str] = nf_raw
                    dest_cnpj, dest_nome = _extrair_destinatario_xml(getattr(aloc, "xml", "") or "")
                    chave_para_dest_cnpj[chave_str] = dest_cnpj
                    chave_para_dest_tokens[chave_str] = _tokens_relevantes(dest_nome or getattr(aloc, "cliente", "") or "")
                    try:
                        chave_para_valor_documento[chave_str] = float(getattr(aloc, "valor_total", 0) or 0)
                    except Exception:
                        chave_para_valor_documento[chave_str] = 0.0
                    nf_digits = _digits_only(nf_raw)
                    if len(nf_digits) >= 5:
                        aloc_com_nf_digits.append((aloc, nf_digits))

                def _serializar_match(item: Optional[dict]) -> Optional[dict]:
                    if not item:
                        return None
                    aloc = item.get("aloc")
                    return {
                        "chave": str(getattr(aloc, "chave", "") or "").strip(),
                        "nf": str(getattr(aloc, "nf", "") or "").strip(),
                        "cliente": str(getattr(aloc, "cliente", "") or "").strip(),
                        "score": int(item.get("score") or 0),
                        "suffix": int(item.get("suffix") or 0),
                        "motivos": list(item.get("motivos") or []),
                    }

                def _resolver_alocacao_boleto(documento: dict) -> tuple[Optional[Alocacao], Optional[str], dict]:
                    doc_digits_s = _digits_only(documento.get("doc_digits") or "")
                    doc_candidates_s = [
                        _digits_only(v)
                        for v in (documento.get("doc_candidates") or [])
                        if _digits_only(v)
                    ]
                    if doc_digits_s and doc_digits_s not in doc_candidates_s:
                        doc_candidates_s.insert(0, doc_digits_s)
                    pagador_cnpj = _digits_only(documento.get("pagador_cnpj") or "")
                    pagador_tokens = _tokens_relevantes(documento.get("pagador") or "")
                    texto_tokens = _tokens_relevantes(documento.get("texto") or "")
                    numeric_blocks = {
                        _digits_only(v)
                        for v in (documento.get("numeric_blocks") or [])
                        if _digits_only(v)
                    }
                    if doc_digits_s:
                        numeric_blocks.add(doc_digits_s)
                    numeric_blocks.update(doc_candidates_s)

                    valor_documento = documento.get("valor_documento")
                    try:
                        valor_documento_f = float(valor_documento) if valor_documento is not None else None
                    except Exception:
                        valor_documento_f = None

                    candidatos: list[dict] = []

                    for aloc, nf_digits in aloc_com_nf_digits:
                        chave_str = str(aloc.chave).strip()
                        score = 0
                        suffix = 0
                        motivos: list[str] = []

                        if doc_candidates_s:
                            suffix = max(
                                (_common_suffix_len(candidato, nf_digits) for candidato in doc_candidates_s),
                                default=0,
                            )
                            if suffix >= 5:
                                score += 1000 + suffix
                                motivos.append(f"doc_suffix={suffix}")
                            if any(candidato == nf_digits for candidato in doc_candidates_s):
                                score += 2500
                                motivos.append("doc_exato")

                        if nf_digits in numeric_blocks:
                            score += 3000
                            motivos.append("nf_em_texto")

                        dest_cnpj = chave_para_dest_cnpj.get(chave_str, "")
                        if pagador_cnpj and dest_cnpj and pagador_cnpj == dest_cnpj:
                            score += 4000
                            motivos.append("cnpj_pagador")

                        dest_tokens = chave_para_dest_tokens.get(chave_str, set())
                        overlap_pagador = len(dest_tokens.intersection(pagador_tokens))
                        overlap_texto = len(dest_tokens.intersection(texto_tokens))
                        if overlap_pagador:
                            score += overlap_pagador * 300
                            motivos.append(f"pagador_tokens={overlap_pagador}")
                        if overlap_texto:
                            score += overlap_texto * 80
                            motivos.append(f"texto_tokens={overlap_texto}")

                        valor_nf = chave_para_valor_documento.get(chave_str, 0.0)
                        if (
                            valor_documento_f is not None
                            and valor_nf > 0
                            and abs(valor_nf - valor_documento_f) <= 0.05
                        ):
                            score += 900
                            motivos.append("valor_documento")

                        if score > 0:
                            candidatos.append(
                                {
                                    "aloc": aloc,
                                    "score": score,
                                    "suffix": suffix,
                                    "motivos": motivos,
                                }
                            )

                    if not candidatos:
                        return None, "Sem correspondencia na planilha", {
                            "doc_digits": doc_digits_s or None,
                            "doc_candidates": doc_candidates_s,
                        }

                    candidatos.sort(
                        key=lambda item: (item["score"], item["suffix"], len(item["motivos"])),
                        reverse=True,
                    )

                    melhor = candidatos[0]
                    segundo = candidatos[1] if len(candidatos) > 1 else None

                    if melhor["score"] < 1000:
                        return None, "Sem correspondencia com confianca suficiente", {
                            "doc_digits": doc_digits_s or None,
                            "doc_candidates": doc_candidates_s,
                            "melhor": _serializar_match(melhor),
                            "segundo": _serializar_match(segundo),
                        }

                    if segundo and melhor["score"] == segundo["score"]:
                        return None, "Ambiguo (pontuacao empatada)", {
                            "doc_digits": doc_digits_s or None,
                            "doc_candidates": doc_candidates_s,
                            "melhor": _serializar_match(melhor),
                            "segundo": _serializar_match(segundo),
                        }

                    if segundo and melhor["score"] < 4000 and (melhor["score"] - segundo["score"] < 250):
                        return None, "Ambiguo (diferenca insuficiente)", {
                            "doc_digits": doc_digits_s or None,
                            "doc_candidates": doc_candidates_s,
                            "melhor": _serializar_match(melhor),
                            "segundo": _serializar_match(segundo),
                        }

                    return melhor["aloc"], None, {
                        "doc_digits": doc_digits_s or None,
                        "doc_candidates": doc_candidates_s,
                        "melhor": _serializar_match(melhor),
                        "segundo": _serializar_match(segundo),
                    }

                # Controle de quais chaves já receberam boleto nesta execução
                chaves_com_boleto: set[str] = set()

                # Controle de quais chaves "deveriam" receber boleto (derivado do PDF de boletos)
                chaves_esperadas_por_pdf: set[str] = set()

                # Métricas/diagnóstico do PDF de boletos
                pdf_total_documentos = 0
                pdf_paginas_nao_identificadas = 0
                pdf_separados = 0
                pdf_sem_correspondencia = 0
                pdf_ambiguos = 0
                pdf_sem_nf = 0
                pdf_falha_salvar = 0
                pdf_problemas: list[dict] = []
                pdf_extracao_cache_hit = False
                pdf_source_hash: Optional[str] = None

                # A) Se veio PDF de boletos, extrair e salvar em cada pasta (e registrar histórico)
                if caminho_boletos_pdf and Path(str(caminho_boletos_pdf)).exists():
                    logger.info(f"Processando PDF de boletos: {caminho_boletos_pdf}")
                    progresso_atual["etapa"] = "boletos"
                    progresso_atual["percentual"] = 70
                    progresso_atual["mensagem"] = "Processando PDF de boletos..."
                    progresso_atual["detalhes"] = ""
                    logger.info(f"📄 Lendo arquivo PDF de boletos...")

                    source_hash = historico_boletos.registrar_pdf_origem(str(caminho_boletos_pdf))
                    pdf_source_hash = source_hash
                    cache_extracao = (
                        historico_boletos.obter_extracao_pdf(source_hash) if source_hash else None
                    )
                    if cache_extracao:
                        pdf_extracao_cache_hit = True
                        documentos_boleto = list(cache_extracao.get("documentos") or [])
                        nao_identificadas = [
                            int(p) for p in (cache_extracao.get("nao_identificadas") or [])
                        ]
                        logger.info(
                            "📊 Extração de boletos reaproveitada do histórico "
                            f"(docs={len(documentos_boleto)}, hash={source_hash[:12] if source_hash else ''})"
                        )
                    else:
                        logger.info(f"📊 Extraindo páginas e identificando NFs no PDF...")
                        documentos_boleto, nao_identificadas = self.gestor_saida.extrair_documentos_boletos(
                            str(caminho_boletos_pdf)
                        )
                        if source_hash:
                            historico_boletos.registrar_extracao_pdf(
                                source_hash,
                                documentos_boleto,
                                nao_identificadas,
                            )
                    logger.info(
                        f"✅ Extração concluída: {len(documentos_boleto)} documentos analisados, "
                        f"{len(nao_identificadas)} páginas não identificadas"
                    )
                    if nao_identificadas:
                        logger.info(f"Boletos: {len(nao_identificadas)} páginas sem NF identificada")

                    pdf_total_documentos = len(documentos_boleto)
                    pdf_paginas_nao_identificadas = len(nao_identificadas)

                    total_docs = len(documentos_boleto)
                    logger.info(f"🔄 Processando {total_docs} documentos extraídos...")

                    for idx, documento in enumerate(documentos_boleto, 1):
                        paginas = [
                            int(p)
                            for p in (documento.get("pages") or [])
                            if isinstance(p, int)
                        ]
                        doc_digits = str(documento.get("doc_digits") or "").strip()
                        doc_digits_s = _digits_only(doc_digits)
                        doc_candidates_s = [
                            _digits_only(v)
                            for v in (documento.get("doc_candidates") or [])
                            if _digits_only(v)
                        ]
                        pagador = str(documento.get("pagador") or "").strip()
                        pagador_cnpj = _digits_only(documento.get("pagador_cnpj") or "")
                        valor_documento = documento.get("valor_documento")
                        doc_label = doc_digits_s or pagador_cnpj or pagador or f"anon-{idx}"

                        # Atualizar progresso a cada documento processado
                        percentual_boleto = 70 + int((idx / total_docs) * 20)
                        progresso_atual["etapa"] = "boletos"
                        progresso_atual["percentual"] = percentual_boleto
                        progresso_atual["mensagem"] = f"Processando boletos: {idx}/{total_docs} documentos"
                        progresso_atual["detalhes"] = f"Documento: {doc_label}"

                        if idx % 10 == 0 or idx == total_docs:
                            logger.info(f"   Processando documento {idx}/{total_docs}...")

                        aloc_ref, motivo_match, _debug_match = _resolver_alocacao_boleto(documento)
                        if aloc_ref is None:
                            if len(doc_digits_s) < 5:
                                pdf_sem_nf += 1

                            if motivo_match and "Ambiguo" in motivo_match:
                                pdf_ambiguos += 1
                            else:
                                pdf_sem_correspondencia += 1

                            pdf_problemas.append({
                                "doc": str(doc_label),
                                "motivo": motivo_match or "Sem correspondência na planilha",
                                "paginas": len(paginas) if paginas else 0,
                                "doc_digits": doc_digits_s or None,
                                "doc_candidates": doc_candidates_s,
                                "pagador": pagador or None,
                                "pagador_cnpj": pagador_cnpj or None,
                                "valor_documento": valor_documento,
                                "match_debug": _debug_match or None,
                            })
                            continue

                        chave_associada = str(aloc_ref.chave).strip()
                        chaves_esperadas_por_pdf.add(chave_associada)
                        rota = str(aloc_ref.rota or "").strip()
                        placa = str(aloc_ref.placa or "").strip()
                        idq = str(aloc_ref.id_quebra or "").strip()
                        grupo_key = (rota, placa, idq)

                        # Inicializa relatório por chave apenas para chaves esperadas (derivadas do PDF)
                        if chave_associada not in boletos_por_chave:
                            boletos_por_chave[chave_associada] = {
                                "chave": chave_associada,
                                "nf": str(getattr(aloc_ref, "nf", "") or "").strip(),
                                "cliente": str(getattr(aloc_ref, "cliente", "") or "").strip(),
                                "status": "pendente",  # anexado|faltando|pendente
                                "origem": None,         # pdf|historico
                                "arquivo": None,
                                "paginas": [],
                                "doc_digits": None,
                                "doc_candidates": [],
                                "pagador": None,
                                "pagador_cnpj": None,
                                "valor_documento": None,
                                "match_debug": None,
                            }

                        valor_dir = _valor_separacao_com_id(aloc_ref)
                        estrutura = self.gestor_saida.criar_estrutura_diretorios(tipo_separacao, valor_dir, separar_em_pastas=separar_em_pastas)
                        pasta_pdf = estrutura / "pdf"

                        nf_digits_ref = _digits_only(str(getattr(aloc_ref, "nf", "") or ""))
                        nf5 = (
                            doc_digits_s[-5:]
                            if len(doc_digits_s) >= 5
                            else (nf_digits_ref[-5:] if len(nf_digits_ref) >= 5 else chave_associada[-6:])
                        )
                        nome_boleto = self.gestor_saida._safe_file_stem(f"BOLETO-{nf5}")
                        caminho_boleto_path = pasta_pdf / f"{nome_boleto}.pdf"
                        if caminho_boleto_path.exists():
                            caminho_boleto_path = pasta_pdf / f"{nome_boleto}-{chave_associada[-6:]}.pdf"

                        ok_bol, _ = self.gestor_saida.salvar_pdf_com_paginas(
                            str(caminho_boletos_pdf),
                            paginas,
                            str(caminho_boleto_path),
                        )
                        if ok_bol:
                            pdf_separados += 1
                            chaves_com_boleto.add(chave_associada)
                            boletos_por_grupo.setdefault(grupo_key, []).append(str(caminho_boleto_path))

                            if chave_associada in boletos_por_chave:
                                boletos_por_chave[chave_associada]["status"] = "anexado"
                                boletos_por_chave[chave_associada]["origem"] = "pdf"
                                boletos_por_chave[chave_associada]["arquivo"] = str(caminho_boleto_path)
                                boletos_por_chave[chave_associada]["paginas"] = paginas
                                boletos_por_chave[chave_associada]["doc_digits"] = doc_digits_s or None
                                boletos_por_chave[chave_associada]["doc_candidates"] = doc_candidates_s
                                boletos_por_chave[chave_associada]["pagador"] = pagador or None
                                boletos_por_chave[chave_associada]["pagador_cnpj"] = pagador_cnpj or None
                                boletos_por_chave[chave_associada]["valor_documento"] = valor_documento
                                boletos_por_chave[chave_associada]["match_debug"] = _debug_match or None

                            if source_hash:
                                historico_boletos.registrar_boleto(
                                    chave=chave_associada,
                                    nota=chave_para_nf.get(chave_associada, ""),
                                    source_hash=source_hash,
                                    paginas=paginas,
                                    doc_digits=doc_digits_s or nf_digits_ref,
                                )
                        else:
                            pdf_falha_salvar += 1
                            pdf_problemas.append({
                                "doc": str(doc_label),
                                "motivo": "Falha ao salvar boleto separado",
                                "paginas": len(paginas) if paginas else 0,
                            })

                    logger.info(
                        "Boletos extraídos: "
                        f"salvos={pdf_separados} sem_correspondencia={pdf_sem_correspondencia} "
                        f"ambiguos={pdf_ambiguos} sem_nf={pdf_sem_nf} falha_salvar={pdf_falha_salvar}"
                    )

                # B) Completar boletos faltantes via histórico por chave
                # Regra: só tenta histórico para chaves que o PDF indicou que têm boleto.
                boletos_cache_hits = 0
                boletos_cache_miss = 0
                boletos_cache_fallback_hits = 0
                boletos_cache_fallback_miss = 0
                boletos_cache_fallback_ambiguo = 0

                for chave_str in sorted(chaves_esperadas_por_pdf):
                    if not chave_str or chave_str in chaves_com_boleto:
                        continue

                    aloc = aloc_por_chave.get(chave_str)
                    if not aloc:
                        continue

                    # Garantir registro no relatório por chave
                    if chave_str not in boletos_por_chave:
                        boletos_por_chave[chave_str] = {
                            "chave": chave_str,
                            "nf": str(getattr(aloc, "nf", "") or "").strip(),
                            "cliente": str(getattr(aloc, "cliente", "") or "").strip(),
                            "status": "pendente",
                            "origem": None,
                            "arquivo": None,
                            "paginas": [],
                            "doc_digits": None,
                            "doc_candidates": [],
                            "pagador": None,
                            "pagador_cnpj": None,
                            "valor_documento": None,
                            "match_debug": None,
                        }

                    entry = historico_boletos.obter_por_chave(chave_str)
                    if not entry:
                        boletos_cache_miss += 1

                        # Fallback: tentar pelo NF (últimos 5 dígitos) usando score por doc_digits
                        nf_raw = str(getattr(aloc, "nf", "") or "").strip()
                        nf_digits = _digits_only(nf_raw)
                        if len(nf_digits) < 5:
                            boletos_cache_fallback_miss += 1
                            continue
                        nf5 = nf_digits[-5:]
                        candidatos = historico_boletos.obter_por_nf5(nf5, limite=5)
                        if not candidatos:
                            boletos_cache_fallback_miss += 1
                            continue

                        melhor_score = 0
                        melhores_entries: list[dict] = []
                        for c in candidatos:
                            doc_c = _digits_only(c.get("doc_digits") or "")
                            score = _common_suffix_len(doc_c, nf_digits)
                            if score < 5:
                                continue
                            if score > melhor_score:
                                melhor_score = score
                                melhores_entries = [c]
                            elif score == melhor_score:
                                melhores_entries.append(c)

                        if not melhores_entries:
                            boletos_cache_fallback_miss += 1
                            continue
                        if len(melhores_entries) > 1:
                            boletos_cache_fallback_ambiguo += 1
                            continue

                        entry = melhores_entries[0]
                        boletos_cache_fallback_hits += 1

                    valor_dir = _valor_separacao_com_id(aloc)
                    estrutura = self.gestor_saida.criar_estrutura_diretorios(tipo_separacao, valor_dir, separar_em_pastas=separar_em_pastas)
                    pasta_pdf = estrutura / "pdf"

                    nf_raw = str(getattr(aloc, "nf", "") or "").strip()
                    nf_digits = _digits_only(nf_raw)
                    nf5 = nf_digits[-5:] if len(nf_digits) >= 5 else ""
                    base = nf5 or chave_str[-6:]
                    nome_boleto = self.gestor_saida._safe_file_stem(f"BOLETO-{base}-{chave_str[-6:]}")
                    caminho_boleto_path = pasta_pdf / f"{nome_boleto}.pdf"

                    ok_bol, _ = self.gestor_saida.salvar_pdf_com_paginas(
                        entry["source_path"],
                        entry["pages"],
                        str(caminho_boleto_path),
                    )
                    if ok_bol:
                        boletos_cache_hits += 1
                        chaves_com_boleto.add(chave_str)
                        rota = str(aloc.rota or "").strip()
                        placa = str(aloc.placa or "").strip()
                        idq = str(aloc.id_quebra or "").strip()
                        grupo_key = (rota, placa, idq)
                        boletos_por_grupo.setdefault(grupo_key, []).append(str(caminho_boleto_path))

                        if chave_str in boletos_por_chave:
                            boletos_por_chave[chave_str]["status"] = "anexado"
                            boletos_por_chave[chave_str]["origem"] = "historico"
                            boletos_por_chave[chave_str]["arquivo"] = str(caminho_boleto_path)
                            boletos_por_chave[chave_str]["paginas"] = list(entry.get("pages") or [])
                            boletos_por_chave[chave_str]["doc_digits"] = str(entry.get("doc_digits") or "") or None

                if any(
                    x
                    for x in (
                        boletos_cache_hits,
                        boletos_cache_miss,
                        boletos_cache_fallback_hits,
                        boletos_cache_fallback_miss,
                        boletos_cache_fallback_ambiguo,
                    )
                ):
                    logger.info(
                        "Boletos do histórico: "
                        f"anexados={boletos_cache_hits} sem_cache={boletos_cache_miss} "
                        f"fallback_hits={boletos_cache_fallback_hits} fallback_miss={boletos_cache_fallback_miss} "
                        f"fallback_ambiguo={boletos_cache_fallback_ambiguo}"
                    )

                # Finalizar relatório de boletos (somente chaves esperadas pelo PDF)
                for chave_i, info in boletos_por_chave.items():
                    if info.get("status") != "anexado":
                        info["status"] = "faltando"

                anexados_pdf = [v for v in boletos_por_chave.values() if v.get("origem") == "pdf" and v.get("status") == "anexado"]
                anexados_hist = [v for v in boletos_por_chave.values() if v.get("origem") == "historico" and v.get("status") == "anexado"]
                faltando = [v for v in boletos_por_chave.values() if v.get("status") == "faltando"]

                pdf_ok = (
                    (pdf_total_documentos > 0)
                    and (pdf_separados == pdf_total_documentos)
                    and (pdf_sem_correspondencia == 0)
                    and (pdf_ambiguos == 0)
                    and (pdf_sem_nf == 0)
                    and (pdf_falha_salvar == 0)
                    and (pdf_paginas_nao_identificadas == 0)
                )

                self._boletos_relatorio = {
                    # PDF de boletos (denominador é o PDF)
                    "pdf_total_documentos": int(pdf_total_documentos),
                    "pdf_paginas_nao_identificadas": int(pdf_paginas_nao_identificadas),
                    "pdf_separados": int(pdf_separados),
                    "pdf_sem_correspondencia": int(pdf_sem_correspondencia),
                    "pdf_ambiguos": int(pdf_ambiguos),
                    "pdf_sem_nf": int(pdf_sem_nf),
                    "pdf_falha_salvar": int(pdf_falha_salvar),
                    "pdf_ok": bool(pdf_ok),
                    "pdf_extracao_cache_hit": bool(pdf_extracao_cache_hit),
                    "pdf_source_hash": pdf_source_hash,
                    "pdf_problemas": pdf_problemas,

                    # Chaves esperadas (PDF -> planilha)
                    "esperados_total": int(len(chaves_esperadas_por_pdf)),

                    # Resultados por chave (apenas para chaves esperadas)
                    "anexados_total": int(len(anexados_pdf) + len(anexados_hist)),
                    "anexados_pdf": int(len(anexados_pdf)),
                    "anexados_historico": int(len(anexados_hist)),
                    "faltando_total": int(len(faltando)),
                    "todos_ok": bool(len(faltando) == 0 and pdf_ok),
                    "faltando": sorted(faltando, key=lambda x: (str(x.get("cliente") or ""), str(x.get("nf") or ""))),
                    "do_historico": sorted(anexados_hist, key=lambda x: (str(x.get("cliente") or ""), str(x.get("nf") or ""))),
                    "do_pdf": sorted(anexados_pdf, key=lambda x: (str(x.get("cliente") or ""), str(x.get("nf") or ""))),
                }

            # Se não foi fornecido PDF de boletos, não gera relatório/uso de histórico
            if baixar_pdf and not (caminho_boletos_pdf and Path(str(caminho_boletos_pdf)).exists()):
                self._boletos_relatorio = {}

            if juntar_pdfs and baixar_pdf:
                progresso_atual["etapa"] = "merge"
                progresso_atual["percentual"] = 92
                progresso_atual["mensagem"] = "Juntando PDFs por grupo..."
                progresso_atual["detalhes"] = ""
                logger.info("Iniciando união de PDFs por (rota, placa, id_quebra)...")

                grupos: dict[tuple[str, str, str], dict[str, list[str]]] = {}
                for aloc in alocacoes_validas:
                    chave_str = str(aloc.chave).strip()
                    r = resultados_por_chave.get(chave_str)
                    if not r or not r.arquivo_pdf:
                        continue

                    rota = str(aloc.rota or "").strip()
                    placa = str(aloc.placa or "").strip()
                    idq = str(aloc.id_quebra or "").strip()
                    g = grupos.setdefault((rota, placa, idq), {"danfes": [], "boletos": [], "chaves": []})
                    g["danfes"].append(r.arquivo_pdf)
                    g["chaves"].append(chave_str)

                # Injetar boletos coletados (PDFs já salvos em disco)
                for grupo_key, boletos in boletos_por_grupo.items():
                    if not boletos:
                        continue
                    g = grupos.setdefault(grupo_key, {"danfes": [], "boletos": [], "chaves": []})
                    g["boletos"].extend(boletos)

                unidos_ok = 0
                unidos_erro = 0
                for (rota, placa, idq), dados_grupo in grupos.items():
                    danfes = dados_grupo.get("danfes", [])
                    boletos = dados_grupo.get("boletos", [])
                    chaves = dados_grupo.get("chaves", [])
                    # Pasta do grupo segue a separação atual (placa/rota) e inclui (id)
                    # Para evitar colisões quando rota/placa se repetem, a pasta já vem com (id).
                    if tipo_separacao == "placa":
                        valor_dir = f"{placa} ({idq})" if idq else placa
                    else:
                        valor_dir = f"{rota} ({idq})" if idq else rota

                    estrutura = self.gestor_saida.criar_estrutura_diretorios(tipo_separacao, valor_dir, separar_em_pastas=separar_em_pastas)
                    pasta_pdf = estrutura / "pdf"

                    # Nome do PDF unido (padrão pedido): ROTA_PLACA_ID
                    parts = [p for p in (rota, placa, idq) if p]
                    nome_base = "_".join(parts) if parts else "PDF_UNIDO"
                    nome_base = self.gestor_saida._safe_file_stem(nome_base)
                    caminho_unido = str(pasta_pdf / f"{nome_base}.pdf")

                    # Ordem: DANFEs primeiro, boletos depois
                    danfes_sorted = sorted(set(danfes))
                    boletos_sorted = sorted(set(boletos))
                    pdfs_ordenados = danfes_sorted + boletos_sorted

                    ok_merge, _ = self.gestor_saida.juntar_pdfs(pdfs_ordenados, caminho_unido, ordenar_por_nome=False)
                    if ok_merge:
                        unidos_ok += 1

                        # Se juntou, apaga PDFs individuais (regra solicitada)
                        apagados = 0
                        for p in sorted(set(pdfs_ordenados)):
                            if not p or os.path.normcase(p) == os.path.normcase(caminho_unido):
                                continue
                            try:
                                if os.path.exists(p):
                                    os.remove(p)
                                    apagados += 1
                            except OSError:
                                # Não falha o processamento por erro de remoção
                                pass

                        # Atualiza o caminho do PDF no resultado para apontar para o arquivo unido
                        for chave_str in chaves:
                            rr = resultados_por_chave.get(chave_str)
                            if rr and rr.arquivo_pdf:
                                rr.arquivo_pdf = caminho_unido

                        logger.info(
                            f"PDF unido gerado: {caminho_unido} (apagados {apagados} PDFs individuais)"
                        )
                    else:
                        unidos_erro += 1

                logger.info(f"PDFs unidos: ok={unidos_ok} erro={unidos_erro}")
            
            # Resumo
            sucesso_total = sum(1 for r in self.resultados if r.sucesso)
            logger.info(f"\n{'='*60}")
            logger.info(f"RESUMO: {sucesso_total}/{len(self.resultados)} processadas com sucesso")
            logger.info(f"{'='*60}")
            
            progresso_atual["etapa"] = "concluido"
            progresso_atual["percentual"] = 100
            progresso_atual["mensagem"] = f"Processamento concluído: {sucesso_total}/{len(self.resultados)} sucesso"
            progresso_atual["detalhes"] = ""
            
            resumo = self.obter_resumo()
            # Registrar final no histórico
            if self.processamento_uuid:
                HistoricoService.atualizar_processamento(
                    self.processamento_uuid,
                    status="concluido" if sucesso_total > 0 else "erro",
                    resumo=resumo
                )
            
            return sucesso_total > 0, self.resultados
        
        except Exception as e:
            logger.error(f"Erro ao processar planilha: {e}")
            return False, []
    
    def _processar_alocacao(
        self,
        alocacao: Alocacao,
        nome_planilha: str,
        tipo_separacao: str,
        baixar_pdf: bool,
        baixar_xml: bool,
        separar_em_pastas: bool = True
    ) -> ResultadoProcessamento:
        """
        Processa uma única alocação.
        
        Args:
            alocacao: Dados da alocação
            nome_planilha: Nome da planilha sendo processada
            tipo_separacao: 'placa' ou 'rota'
            baixar_pdf: Se deve baixar PDF
            baixar_xml: Se deve baixar XML
        
        Returns:
            ResultadoProcessamento
        """
        resultado = ResultadoProcessamento(
            alocacao=alocacao,
            sucesso=False,
            etapa="inicio"
        )
        
        try:
            # Determinar valor de separação
            if tipo_separacao == "placa":
                valor_separacao = alocacao.placa
            else:
                valor_separacao = alocacao.rota
            
            # ETAPA 1: ENVIAR XML (OBRIGATÓRIO)
            resultado.etapa = "upload_xml"
            
            # Aqui você já tem o XML da planilha ou pode gerar um
            # Por enquanto, vamos assumir que o XML já vem nos dados
            xml_enviado = alocacao.xml
            
            if not xml_enviado:
                logger.warning(f"XML não fornecido para {alocacao.chave}")
                resultado.mensagem = "XML não fornecido"
                return resultado
            
            # Validar XML
            if not self.construtor_xml.validar_xml(xml_enviado):
                resultado.mensagem = "XML inválido"
                return resultado
            
            # Enviar para API
            sucesso, resposta = self.cliente_api.enviar_xml(xml_enviado)
            
            if not sucesso:
                resultado.mensagem = f"Erro ao enviar XML: {resposta.mensagem}"
                return resultado
            
            logger.info(f"✓ XML enviado para chave: {alocacao.chave}")
            
            # ETAPA 2: BAIXAR PDF (se solicitado)
            if baixar_pdf:
                resultado.etapa = "download_pdf"
                sucesso_pdf, pdf_bytes, resposta_pdf = self.cliente_api.baixar_pdf(
                    alocacao.chave
                )
                
                if sucesso_pdf and pdf_bytes:
                    sucesso_save, arquivo_pdf = self.gestor_saida.salvar_pdf(
                        pdf_bytes,
                        nome_planilha,
                        tipo_separacao,
                        valor_separacao,
                        alocacao.chave,
                        separar_em_pastas=separar_em_pastas
                    )
                    if sucesso_save:
                        resultado.arquivo_pdf = arquivo_pdf
                        logger.info(f"✓ PDF salvo: {arquivo_pdf}")
                else:
                    logger.warning(f"Erro ao baixar PDF: {resposta_pdf.mensagem}")
            
            # ETAPA 3: BAIXAR XML (se solicitado)
            if baixar_xml:
                resultado.etapa = "download_xml"
                sucesso_xml, xml_baixado, resposta_xml = self.cliente_api.baixar_xml(
                    alocacao.chave
                )
                
                if sucesso_xml and xml_baixado:
                    sucesso_save, arquivo_xml = self.gestor_saida.salvar_xml(
                        xml_baixado,
                        nome_planilha,
                        tipo_separacao,
                        valor_separacao,
                        alocacao.chave,
                        separar_em_pastas=separar_em_pastas
                    )
                    if sucesso_save:
                        resultado.arquivo_xml = arquivo_xml
                        logger.info(f"✓ XML salvo: {arquivo_xml}")
                else:
                    logger.warning(f"Erro ao baixar XML: {resposta_xml.mensagem}")
            
            resultado.sucesso = True
            resultado.etapa = "concluido"
            resultado.mensagem = "Processamento concluído com sucesso"
            
        except Exception as e:
            logger.error(f"Erro ao processar alocação {alocacao.chave}: {e}")
            resultado.mensagem = f"Erro: {str(e)}"
        
        return resultado
    
    def obter_resumo(self) -> Dict:
        """
        Retorna um resumo do processamento.
        
        Returns:
            Dicionário com resumo
        """
        total = len(self.resultados)
        sucesso = sum(1 for r in self.resultados if r.sucesso)
        erros = total - sucesso
        
        ts = getattr(self.gestor_saida, 'execucao_timestamp', None)
        caminho_saida_base = (
            str(self.gestor_saida.output_base / ts)
            if ts else str(self.gestor_saida.output_base)
        )

        return {
            "total_alocacoes": total,
            "sucesso": sucesso,
            "erros": erros,
            "taxa_sucesso": f"{(sucesso/total*100):.1f}%" if total > 0 else "0%",
            "execucao_timestamp": ts,
            "caminho_saida_base": caminho_saida_base,
            "boletos": self._boletos_relatorio or None,
            "resultados": [
                {
                    "chave": r.alocacao.chave,
                    "nf": getattr(r.alocacao, 'nf', ''),
                    "cliente": getattr(r.alocacao, 'cliente', ''),
                    "sucesso": r.sucesso,
                    "etapa": r.etapa,
                    "mensagem": r.mensagem,
                    "arquivo_pdf": r.arquivo_pdf,
                    "arquivo_xml": r.arquivo_xml
                }
                for r in self.resultados
            ]
        }
