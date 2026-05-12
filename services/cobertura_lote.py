"""Validacao estrita da cobertura de XML/PDF antes do processamento."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
from typing import Any, Dict, Iterable, List, Optional, Sequence

from config import API_KEYS
from models.alocacao import Alocacao
from services.alocacao_filters import filtrar_alocacoes, normalizar_filtros
from services.coverage_staging import CoverageStagingStore, criar_store_cobertura_padrao
from services.danfe_local import gerar_pdf_danfe_bytes
from services.leitor_xml import LeitorXML
from services.protheus_coleta import ProtheusCollectionService, criar_servico_coleta_protheus_padrao
from utils.logger import logger
from utils.progress import set_progresso
from utils.validators import normalizar_chave_acesso


def _ler_xml_do_arquivo(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1", errors="replace")


def _copy_unique_files(source_map: Dict[str, str], expected_keys: Iterable[str], target_dir: Path) -> Dict[str, str]:
    target_dir.mkdir(parents=True, exist_ok=True)
    copied: Dict[str, str] = {}
    for chave in expected_keys:
        source = source_map.get(chave)
        if not source:
            continue
        source_path = Path(source)
        destination = target_dir / source_path.name
        if source_path.resolve() != destination.resolve():
            shutil.copy2(source_path, destination)
        copied[chave] = str(destination)
    return copied


def _sort_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: (
            str(item.get("rota") or ""),
            str(item.get("nf") or ""),
            str(item.get("cliente") or ""),
            str(item.get("chave") or ""),
        ),
    )


@dataclass
class CoverageService:
    coverage_store: CoverageStagingStore
    protheus_service: ProtheusCollectionService

    def _set_progress(self, etapa: str, percentual: int, mensagem: str, detalhes: str = "") -> None:
        set_progresso(etapa=etapa, percentual=percentual, mensagem=mensagem, detalhes=detalhes)

    def _resolve_pdf_method(self, metodo_pdf: str, baixar_pdf: bool, garantir_pdf: bool) -> str:
        metodo = str(metodo_pdf or "api").strip().lower()
        if metodo not in {"api", "local", "api_fallback_local"}:
            raise ValueError(
                f"metodo_pdf invalido: {metodo}. Use um de: {sorted({'api', 'local', 'api_fallback_local'})}"
            )
        if not baixar_pdf or not garantir_pdf:
            return metodo
        if metodo == "api":
            return "api_fallback_local" if API_KEYS else "local"
        if metodo == "api_fallback_local" and not API_KEYS:
            return "local"
        return metodo

    def _copy_planilha(self, planilha_path: str, root_dir: Path) -> Path:
        source = Path(str(planilha_path or "")).resolve()
        if not source.exists():
            raise ValueError("Planilha original da cobertura nao foi encontrada no disco")
        destination = root_dir / source.name
        if source != destination.resolve():
            shutil.copy2(source, destination)
        return destination

    def _inventariar_source(
        self,
        path: str | None,
        expected_keys: set[str],
    ) -> Dict[str, Any]:
        source_path = Path(str(path or "")).resolve() if path else None
        if not source_path or not source_path.exists() or not source_path.is_dir():
            return {
                "available": False,
                "path": str(source_path) if source_path else None,
                "mapa": {},
                "stats": {},
                "duplicates": {},
                "non_renderable": {},
                "read_errors": {},
                "unknown_read_errors": [],
            }
        inventory = LeitorXML(str(source_path)).inventariar_chaves(expected_keys)
        inventory["available"] = True
        inventory["path"] = str(source_path)
        return inventory

    def _preflight_pdf(self, xml_path: Path) -> Optional[str]:
        try:
            gerar_pdf_danfe_bytes(_ler_xml_do_arquivo(xml_path))
            return None
        except Exception as error:
            return str(error)

    def validate(
        self,
        *,
        planilha_token: str,
        planilha_path: str,
        alocacoes: Sequence[Alocacao],
        pasta_xmls: str | None = None,
        coleta_manifest: Optional[Dict[str, Any]] = None,
        uf: str | None = None,
        filtro_rotas: Sequence[str] | None = None,
        filtro_placas: Sequence[str] | None = None,
        filtro_clientes: Sequence[str] | None = None,
        baixar_pdf: bool = True,
        metodo_pdf: str = "api",
        garantir_pdf: bool = True,
    ) -> Dict[str, Any]:
        self.coverage_store.cleanup()

        subset = filtrar_alocacoes(
            alocacoes,
            filtro_rotas=filtro_rotas,
            filtro_placas=filtro_placas,
            filtro_clientes=filtro_clientes,
        )
        if not subset:
            raise ValueError("Nenhuma alocacao encontrada com os filtros atuais")

        coverage_token, root_dir = self.coverage_store.create()
        copied_planilha = self._copy_planilha(planilha_path, root_dir)
        processing_xml_dir = root_dir / "xmls_processamento"
        processing_xml_dir.mkdir(parents=True, exist_ok=True)

        requested_pdf_method = str(metodo_pdf or "api").strip().lower()
        resolved_pdf_method = self._resolve_pdf_method(requested_pdf_method, baixar_pdf, garantir_pdf)

        items: List[Dict[str, Any]] = []
        alocacoes_validas_por_chave: Dict[str, List[Alocacao]] = {}
        expected_keys: set[str] = set()
        invalid_keys = 0

        for alocacao in subset:
            chave = normalizar_chave_acesso(getattr(alocacao, "chave", ""))
            item = {
                "chave": chave or str(getattr(alocacao, "chave", "") or "").strip(),
                "nf": str(getattr(alocacao, "nf", "") or "").strip(),
                "rota": str(getattr(alocacao, "rota", "") or "").strip(),
                "placa": str(getattr(alocacao, "placa", "") or "").strip(),
                "cliente": str(getattr(alocacao, "cliente", "") or "").strip(),
                "xml_status": "missing",
                "pdf_status": "ready",
                "source": None,
                "reason": "",
            }
            if not chave:
                item["xml_status"] = "invalid_key"
                item["pdf_status"] = "missing" if baixar_pdf and garantir_pdf else "ready"
                item["reason"] = "Chave da planilha invalida ou incompleta"
                invalid_keys += 1
            else:
                alocacoes_validas_por_chave.setdefault(chave, []).append(alocacao)
                expected_keys.add(chave)
            items.append(item)

        self._set_progress(
            "cobertura_local",
            10,
            "Validando cobertura local do lote...",
            f"Subset filtrado: {len(subset)} notas",
        )

        local_inventory = self._inventariar_source(pasta_xmls, expected_keys)
        provided_coleta_inventory = self._inventariar_source(
            (coleta_manifest or {}).get("processing_xml_dir") or (coleta_manifest or {}).get("xml_dir"),
            expected_keys,
        )

        resolved_paths: Dict[str, str] = {}
        resolved_sources: Dict[str, str] = {}
        recovered_from_protheus = 0
        local_found = 0
        duplicates_total = 0
        non_renderable_total = 0

        for item in items:
            chave = normalizar_chave_acesso(item.get("chave"))
            if not chave:
                continue

            if chave in local_inventory["duplicates"]:
                item["xml_status"] = "duplicate"
                item["pdf_status"] = "missing" if baixar_pdf and garantir_pdf else "ready"
                item["reason"] = "Ha XMLs duplicados para a mesma chave na base local"
                duplicates_total += 1
                continue

            local_path = local_inventory["mapa"].get(chave)
            if local_path:
                item["xml_status"] = "found_local"
                item["source"] = "local"
                resolved_paths[chave] = local_path
                resolved_sources[chave] = "local"
                local_found += 1
                continue

            if chave in local_inventory["non_renderable"]:
                item["xml_status"] = "non_renderable"
                item["pdf_status"] = "missing" if baixar_pdf and garantir_pdf else "ready"
                item["reason"] = "XML encontrado na base local, mas nao e NF-e renderizavel"
                non_renderable_total += 1
                continue

            provided_path = provided_coleta_inventory["mapa"].get(chave)
            if provided_path:
                item["xml_status"] = "recovered_protheus"
                item["source"] = "coleta_protheus"
                resolved_paths[chave] = provided_path
                resolved_sources[chave] = "coleta_protheus"
                recovered_from_protheus += 1
                continue

            if chave in provided_coleta_inventory["duplicates"]:
                item["xml_status"] = "duplicate"
                item["pdf_status"] = "missing" if baixar_pdf and garantir_pdf else "ready"
                item["reason"] = "Ha XMLs duplicados para a mesma chave no staging do Protheus"
                duplicates_total += 1
                continue

            if chave in provided_coleta_inventory["non_renderable"]:
                item["xml_status"] = "non_renderable"
                item["pdf_status"] = "missing" if baixar_pdf and garantir_pdf else "ready"
                item["reason"] = "XML encontrado no staging do Protheus, mas nao e NF-e renderizavel"
                non_renderable_total += 1
                continue

            read_error_paths = local_inventory["read_errors"].get(chave) or []
            if read_error_paths:
                item["reason"] = "Falha ao ler o XML correspondente na base local"
            else:
                item["reason"] = "XML nao encontrado na base local"

        missing_keys = sorted(
            {
                normalizar_chave_acesso(item["chave"])
                for item in items
                if item["xml_status"] == "missing" and normalizar_chave_acesso(item["chave"])
            }
        )
        failures: List[str] = []
        recovery_reviews: List[Dict[str, Any]] = []

        if missing_keys:
            if not uf:
                failures.append(
                    f"{len(missing_keys)} nota(s) seguem sem XML e exigem UF para recuperacao automatica no Protheus"
                )
            else:
                self._set_progress(
                    "cobertura_protheus",
                    50,
                    "Tentando recuperar XMLs faltantes no Protheus...",
                    f"Faltantes: {len(missing_keys)}",
                )
                missing_subset: List[Alocacao] = []
                for chave in missing_keys:
                    missing_subset.extend(alocacoes_validas_por_chave.get(chave, []))
                try:
                    review = self.protheus_service.collect(
                        planilha_token=planilha_token,
                        planilha_path=str(copied_planilha),
                        alocacoes=missing_subset,
                        uf=str(uf or "").strip().upper(),
                        filtro_rotas=[],
                        filtro_placas=[],
                        filtro_clientes=[],
                    )
                    recovery_reviews.append(review)
                    recovered_inventory = self._inventariar_source(
                        review["xml"].get("processing_dir"),
                        set(missing_keys),
                    )
                    for item in items:
                        chave = normalizar_chave_acesso(item.get("chave"))
                        if item["xml_status"] != "missing" or not chave:
                            continue
                        recovered_path = recovered_inventory["mapa"].get(chave)
                        if recovered_path:
                            item["xml_status"] = "recovered_protheus"
                            item["source"] = "protheus_auto"
                            item["reason"] = ""
                            resolved_paths[chave] = recovered_path
                            resolved_sources[chave] = "protheus_auto"
                            recovered_from_protheus += 1
                            continue
                        if chave in recovered_inventory["duplicates"]:
                            item["xml_status"] = "duplicate"
                            item["reason"] = "Ha XMLs duplicados para a mesma chave apos a recuperacao Protheus"
                            duplicates_total += 1
                        elif chave in recovered_inventory["non_renderable"]:
                            item["xml_status"] = "non_renderable"
                            item["reason"] = "A recuperacao Protheus retornou XML nao renderizavel para a chave"
                            non_renderable_total += 1

                    missing_after_recovery = [
                        item for item in items if item["xml_status"] == "missing"
                    ]
                    if missing_after_recovery:
                        failures.append(
                            f"{len(missing_after_recovery)} nota(s) continuaram sem XML mesmo apos a recuperacao Protheus"
                        )
                except Exception as error:
                    failures.append(f"Falha na recuperacao automatica via Protheus: {error}")

        self._set_progress(
            "cobertura_reconciliacao",
            75,
            "Reconciliando cobertura final do lote...",
            f"XMLs resolvidos: {len(resolved_paths)}/{len(expected_keys)}",
        )

        processing_map = _copy_unique_files(resolved_paths, resolved_paths.keys(), processing_xml_dir)

        pdf_missing = 0
        if baixar_pdf and garantir_pdf:
            for item in items:
                chave = normalizar_chave_acesso(item.get("chave"))
                if not chave or item["xml_status"] not in {"found_local", "recovered_protheus"}:
                    item["pdf_status"] = "missing"
                    if item["xml_status"] != "invalid_key":
                        pdf_missing += 1
                    continue

                xml_path_str = processing_map.get(chave)
                if not xml_path_str:
                    item["pdf_status"] = "missing"
                    item["reason"] = item["reason"] or "XML resolvido nao foi copiado para o staging da cobertura"
                    pdf_missing += 1
                    continue

                pdf_error = self._preflight_pdf(Path(xml_path_str))
                if pdf_error:
                    item["pdf_status"] = "missing"
                    item["reason"] = f"Falha no preflight do PDF: {pdf_error}"
                    pdf_missing += 1
                else:
                    item["pdf_status"] = "ready"
        else:
            for item in items:
                item["pdf_status"] = "ready"

        unresolved_items = [
            item
            for item in items
            if item["xml_status"] not in {"found_local", "recovered_protheus"}
            or item["pdf_status"] == "missing"
        ]
        if pdf_missing:
            failures.append(f"{pdf_missing} nota(s) nao conseguiram garantir a geracao de PDF no preflight")

        route_totals: Dict[str, Dict[str, Any]] = {}
        for item in items:
            rota = str(item.get("rota") or "").strip() or "(Sem rota)"
            stats = route_totals.setdefault(
                rota,
                {"rota": rota, "esperadas": 0, "com_xml": 0, "com_pdf": 0, "faltantes": 0},
            )
            stats["esperadas"] += 1
            if item["xml_status"] in {"found_local", "recovered_protheus"}:
                stats["com_xml"] += 1
            if item["pdf_status"] != "missing":
                stats["com_pdf"] += 1
            if item["xml_status"] not in {"found_local", "recovered_protheus"} or item["pdf_status"] == "missing":
                stats["faltantes"] += 1

        boleto_pdf_path = None
        if coleta_manifest and str(coleta_manifest.get("boleto_pdf_path") or "").strip():
            boleto_pdf_path = str(coleta_manifest.get("boleto_pdf_path") or "").strip()
        elif recovery_reviews:
            for review in recovery_reviews:
                pdf_path = str((review.get("boletos") or {}).get("pdf_path") or "").strip()
                if pdf_path:
                    boleto_pdf_path = pdf_path
                    break

        ready_for_processing = not unresolved_items
        manifest = {
            "kind": "coverage_lote",
            "planilha_token": planilha_token,
            "planilha_path": str(copied_planilha),
            "pasta_xmls_origem": str(pasta_xmls or "").strip() or None,
            "processing_xml_dir": str(processing_xml_dir),
            "boleto_pdf_path": boleto_pdf_path,
            "coleta_token": (coleta_manifest or {}).get("token"),
            "uf": str(uf or "").strip().upper() or None,
            "filtro_rotas": normalizar_filtros(filtro_rotas),
            "filtro_placas": normalizar_filtros(filtro_placas),
            "filtro_clientes": normalizar_filtros(filtro_clientes),
            "garantir_pdf": bool(garantir_pdf),
            "baixar_pdf": bool(baixar_pdf),
            "metodo_pdf_requested": requested_pdf_method,
            "metodo_pdf_resolved": resolved_pdf_method,
            "expected_keys_total": len(expected_keys),
            "expected_keys": sorted(expected_keys),
            "resolved_keys_total": len(processing_map),
            "resolved_keys": sorted(processing_map.keys()),
            "failures": failures,
            "items": _sort_items(items),
            "routes": sorted(route_totals.values(), key=lambda item: str(item["rota"])),
            "ready_for_processing": ready_for_processing,
            "recovery_reviews": recovery_reviews,
        }
        manifest = self.coverage_store.save_manifest(coverage_token, manifest)

        totals = {
            "esperadas": len(items),
            "validas": len(expected_keys),
            "com_xml": len([item for item in items if item["xml_status"] in {"found_local", "recovered_protheus"}]),
            "com_pdf": len([item for item in items if item["pdf_status"] != "missing"]),
            "encontradas_local": local_found,
            "recuperadas_protheus": recovered_from_protheus,
            "faltantes": len([item for item in items if item["xml_status"] == "missing"]),
            "invalidas": invalid_keys,
            "duplicadas": duplicates_total,
            "nao_renderizaveis": non_renderable_total,
        }

        self._set_progress(
            "cobertura_pronta",
            100,
            "Cobertura validada",
            f"Pronto: {totals['com_xml']}/{totals['esperadas']} XMLs resolvidos",
        )
        return {
            "coverage_token": coverage_token,
            "ready_for_processing": ready_for_processing,
            "totals": totals,
            "routes": manifest["routes"],
            "items": manifest["items"],
            "failures": failures,
            "paths": {
                "staging_root": str(root_dir),
                "processing_xml_dir": str(processing_xml_dir),
                "planilha_path": str(copied_planilha),
                "boleto_pdf_path": boleto_pdf_path,
            },
            "metodo_pdf": {
                "requested": requested_pdf_method,
                "resolved": resolved_pdf_method,
            },
            "recovery_reviews": recovery_reviews,
        }


def criar_servico_cobertura_padrao(
    protheus_service: Optional[ProtheusCollectionService] = None,
) -> CoverageService:
    return CoverageService(
        coverage_store=criar_store_cobertura_padrao(),
        protheus_service=protheus_service or criar_servico_coleta_protheus_padrao(),
    )
