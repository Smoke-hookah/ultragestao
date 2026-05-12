"""Orquestracao da coleta Protheus para XMLs e boletos."""

from __future__ import annotations

from dataclasses import dataclass
import re
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from models.alocacao import Alocacao
from services.alocacao_filters import filtrar_alocacoes, normalizar_filtros
from services.leitor_xml import LeitorXML
from services.protheus_automation import (
    ProtheusBranchRequest,
    ProtheusPlaywrightCollector,
    criar_coletor_protheus_padrao,
)
from services.protheus_config import (
    get_public_protheus_config,
    list_protheus_config_issues,
    load_protheus_config,
    resolve_branch_for_uf,
)
from services.protheus_credentials import (
    WindowsCredentialStore,
    criar_credencial_protheus_padrao,
)
from services.protheus_staging import (
    ProtheusStagingStore,
    criar_store_coleta_protheus_padrao,
)
from utils.logger import logger
from utils.progress import set_progresso


def _parse_nf_numero(value: str | int | float | None) -> int | None:
    digits = re.sub(r"\D+", "", str(value or ""))
    if not digits:
        return None
    try:
        return int(digits)
    except Exception:
        return None


def _stringify_nf(numero: int) -> str:
    return str(int(numero))


@dataclass
class ProtheusCollectionService:
    staging_store: ProtheusStagingStore
    credential_store: WindowsCredentialStore
    collector: ProtheusPlaywrightCollector

    def _set_progress(self, etapa: str, percentual: int, mensagem: str, detalhes: str = "") -> None:
        set_progresso(
            etapa=etapa,
            percentual=percentual,
            mensagem=mensagem,
            detalhes=detalhes,
        )

    def _load_credentials(self) -> Dict[str, str]:
        credentials = self.credential_store.read()
        if not credentials:
            raise ValueError("Credenciais do Protheus nao configuradas")
        username = str(credentials.get("username") or "").strip()
        password = str(credentials.get("password") or "")
        if not username or not password:
            raise ValueError("Credenciais do Protheus incompletas")
        return {"username": username, "password": password}

    def _derive_nf_range(self, alocacoes: Sequence[Alocacao]) -> tuple[str, str, List[str]]:
        numeros: List[int] = []
        sem_nf: List[str] = []
        for alocacao in alocacoes:
            numero_nf = _parse_nf_numero(getattr(alocacao, "nf", None))
            if numero_nf is None:
                sem_nf.append(str(getattr(alocacao, "chave", "") or ""))
                continue
            numeros.append(numero_nf)

        if not numeros:
            raise ValueError("Nenhuma NF numerica valida foi encontrada no subset selecionado")

        return _stringify_nf(min(numeros)), _stringify_nf(max(numeros)), sem_nf

    def _copy_expected_xmls(
        self,
        source_map: Dict[str, str],
        expected_keys: Iterable[str],
        target_dir: Path,
    ) -> Dict[str, str]:
        target_dir.mkdir(parents=True, exist_ok=True)
        copied: Dict[str, str] = {}
        for chave in expected_keys:
            source = source_map.get(chave)
            if not source:
                continue
            source_path = Path(source)
            dest_path = target_dir / source_path.name
            if dest_path.resolve() != source_path.resolve():
                shutil.copy2(source_path, dest_path)
            copied[chave] = str(dest_path)
        return copied

    def collect(
        self,
        *,
        planilha_token: str,
        planilha_path: str,
        alocacoes: Sequence[Alocacao],
        uf: str,
        filtro_rotas: Sequence[str] | None = None,
        filtro_placas: Sequence[str] | None = None,
        filtro_clientes: Sequence[str] | None = None,
    ) -> Dict[str, Any]:
        self.staging_store.cleanup()

        subset = filtrar_alocacoes(
            alocacoes,
            filtro_rotas=filtro_rotas,
            filtro_placas=filtro_placas,
            filtro_clientes=filtro_clientes,
        )
        if not subset:
            raise ValueError("Nenhuma alocacao encontrada com os filtros atuais")

        expected_keys = sorted(
            {
                str(getattr(alocacao, "chave", "") or "").strip()
                for alocacao in subset
                if str(getattr(alocacao, "chave", "") or "").strip()
            }
        )
        if not expected_keys:
            raise ValueError("O subset selecionado nao possui chaves validas para extracao")

        nf_inicio, nf_fim, chaves_sem_nf = self._derive_nf_range(subset)

        config = load_protheus_config()
        pending_fields = list_protheus_config_issues(config)
        if pending_fields:
            raise ValueError(
                "Configuracao do Protheus incompleta. Campos pendentes: "
                + ", ".join(pending_fields)
            )

        credentials = self._load_credentials()
        branch_code = resolve_branch_for_uf(config, uf)

        token, root_dir = self.staging_store.create()
        source_planilha = Path(str(planilha_path or "")).resolve()
        if not source_planilha.exists():
            raise ValueError("Planilha original da coleta nao foi encontrada no disco")
        copied_planilha = root_dir / source_planilha.name
        if copied_planilha.resolve() != source_planilha:
            shutil.copy2(source_planilha, copied_planilha)

        branch_slug = f"{str(uf or '').strip().upper()}_{branch_code}"
        branch_dir = root_dir / branch_slug
        xml_dir = branch_dir / "xml"
        boletos_dir = branch_dir / "boletos"
        boleto_pdf_path = boletos_dir / "boletos.pdf"
        diagnostics_dir = branch_dir / "diagnostico"
        processing_xml_dir = branch_dir / "xml_filtrados"
        work_dir = branch_dir / "downloads"

        request = ProtheusBranchRequest(
            uf=str(uf or "").strip().upper(),
            branch_code=branch_code,
            nf_start=nf_inicio,
            nf_end=nf_fim,
            xml_dir=xml_dir,
            boleto_pdf_path=boleto_pdf_path,
            work_dir=work_dir,
            diagnostics_dir=diagnostics_dir,
        )

        logger.info(
            "Iniciando coleta Protheus: "
            f"uf={request.uf} filial={branch_code} subset={len(subset)} nf={nf_inicio}-{nf_fim}"
        )

        self._set_progress(
            "protheus_login",
            5,
            "Preparando coleta Protheus...",
            f"Subset filtrado: {len(subset)} notas",
        )

        automation_result = self.collector.collect_branch(
            request,
            config,
            credentials,
            progress_callback=self._set_progress,
        )

        self._set_progress(
            "protheus_validacao",
            85,
            "Validando XMLs extraidos...",
            f"Faixa NF {nf_inicio}-{nf_fim}",
        )

        leitor_xml = LeitorXML(str(automation_result.xml_dir))
        expected_map, expected_stats = leitor_xml.carregar_mapa_chave_para_caminho(set(expected_keys))
        all_map, all_stats = leitor_xml.carregar_mapa_chave_para_caminho()
        filtered_map = self._copy_expected_xmls(expected_map, expected_keys, processing_xml_dir)

        found_keys = sorted(filtered_map.keys())
        missing_keys = sorted(set(expected_keys) - set(found_keys))
        extra_keys = sorted(set(all_map.keys()) - set(expected_keys))

        failures: List[str] = []
        if chaves_sem_nf:
            failures.append(
                f"{len(chaves_sem_nf)} item(ns) do subset nao tinham NF numerica valida para a faixa"
            )
        if missing_keys:
            failures.append(
                f"{len(missing_keys)} XML(s) esperados nao foram encontrados na extracao"
            )
        boleto_ok = bool(automation_result.boleto_pdf_path and Path(automation_result.boleto_pdf_path).exists())
        if not boleto_ok:
            failures.append("PDF consolidado de boletos nao foi encontrado no staging")

        manifest = {
            "kind": "coleta_protheus",
            "planilha_token": planilha_token,
            "planilha_path": str(copied_planilha),
            "uf": request.uf,
            "branch_code": branch_code,
            "subset_total": len(subset),
            "filtro_rotas": normalizar_filtros(filtro_rotas),
            "filtro_placas": normalizar_filtros(filtro_placas),
            "filtro_clientes": normalizar_filtros(filtro_clientes),
            "expected_keys_total": len(expected_keys),
            "expected_keys": expected_keys,
            "found_keys_total": len(found_keys),
            "found_keys": found_keys,
            "missing_keys_total": len(missing_keys),
            "missing_keys": missing_keys,
            "extra_keys_total": len(extra_keys),
            "extra_keys": extra_keys,
            "nf_start": nf_inicio,
            "nf_end": nf_fim,
            "xml_dir": str(automation_result.xml_dir),
            "processing_xml_dir": str(processing_xml_dir),
            "boleto_pdf_path": str(automation_result.boleto_pdf_path) if boleto_ok else None,
            "diagnostics_dir": str(diagnostics_dir),
            "download_manifest": automation_result.download_manifest,
            "xml_stats_expected": expected_stats,
            "xml_stats_all": all_stats,
            "review_ready": True,
            "failures": failures,
        }
        manifest = self.staging_store.save_manifest(token, manifest)

        public_config = get_public_protheus_config(has_password=True)
        review = {
            "coleta_token": token,
            "uf": request.uf,
            "branch_code": branch_code,
            "subset_total": len(subset),
            "nf_range": {"inicio": nf_inicio, "fim": nf_fim},
            "xml": {
                "esperados": len(expected_keys),
                "encontrados": len(found_keys),
                "extras_ignorados": len(extra_keys),
                "ausentes": len(missing_keys),
                "staging_dir": str(automation_result.xml_dir),
                "processing_dir": str(processing_xml_dir),
            },
            "boletos": {
                "pdf_disponivel": boleto_ok,
                "pdf_path": str(automation_result.boleto_pdf_path) if boleto_ok else None,
            },
            "paths": {
                "staging_root": str(root_dir),
                "diagnostics_dir": str(diagnostics_dir),
                "config_path": public_config.get("config_path"),
            },
            "pending_fields": public_config.get("pending_fields") or [],
            "failures": failures,
            "ready_for_processing": len(missing_keys) == 0,
        }

        self._set_progress(
            "protheus_revisao_pronta",
            100,
            "Coleta Protheus concluida",
            f"XMLs encontrados: {len(found_keys)}/{len(expected_keys)}",
        )
        return review


def criar_servico_coleta_protheus_padrao() -> ProtheusCollectionService:
    return ProtheusCollectionService(
        staging_store=criar_store_coleta_protheus_padrao(),
        credential_store=criar_credencial_protheus_padrao(),
        collector=criar_coletor_protheus_padrao(),
    )
