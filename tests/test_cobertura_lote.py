from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from models.alocacao import Alocacao
from services.cobertura_lote import CoverageService
from services.coverage_staging import CoverageStagingStore


def _sample_xml(chave: str) -> str:
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">'
        f'<protNFe><infProt><chNFe>{chave}</chNFe></infProt></protNFe>'
        f'<NFe><infNFe Id="NFe{chave}" versao="4.00"></infNFe></NFe>'
        "</nfeProc>"
    )


def _alocacao(chave: str, nf: str = "1001", rota: str = "R1") -> Alocacao:
    return Alocacao(
        chave=chave,
        placa="ABC1234",
        rota=rota,
        pedido="1",
        nf=nf,
        cliente="Cliente A",
        cidade="SP",
        tipo_cliente="Normal",
    )


class CoverageServiceTests(unittest.TestCase):
    def test_validate_uses_local_xml_base_and_marks_lote_ready(self) -> None:
        chave = "35123456789012345678901234567890123456789012"
        with tempfile.TemporaryDirectory(prefix="coverage_service_") as tmp:
            tmp_path = Path(tmp)
            xml_dir = tmp_path / "xml"
            xml_dir.mkdir(parents=True, exist_ok=True)
            (xml_dir / f"NFe{chave}.xml").write_text(_sample_xml(chave), encoding="utf-8")
            planilha = tmp_path / "planilha.xlsx"
            planilha.write_bytes(b"fake")
            store = CoverageStagingStore(tmp_path / "staging", ttl_seconds=60)
            service = CoverageService(coverage_store=store, protheus_service=Mock())

            with patch("services.cobertura_lote.gerar_pdf_danfe_bytes", return_value=b"%PDF-1.4\nfake"):
                review = service.validate(
                    planilha_token="planilha-1",
                    planilha_path=str(planilha),
                    alocacoes=[_alocacao(chave)],
                    pasta_xmls=str(xml_dir),
                    baixar_pdf=True,
                    metodo_pdf="api",
                    garantir_pdf=True,
                )

        self.assertTrue(review["ready_for_processing"])
        self.assertEqual(review["totals"]["encontradas_local"], 1)
        self.assertEqual(review["totals"]["faltantes"], 0)
        self.assertEqual(review["routes"][0]["com_xml"], 1)
        self.assertEqual(review["items"][0]["xml_status"], "found_local")
        self.assertEqual(review["items"][0]["pdf_status"], "ready")
        self.assertTrue(Path(review["paths"]["processing_xml_dir"]).name)

    def test_validate_marks_invalid_key_as_invalid_key_not_missing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="coverage_service_") as tmp:
            tmp_path = Path(tmp)
            planilha = tmp_path / "planilha.xlsx"
            planilha.write_bytes(b"fake")
            store = CoverageStagingStore(tmp_path / "staging", ttl_seconds=60)
            service = CoverageService(coverage_store=store, protheus_service=Mock())

            review = service.validate(
                planilha_token="planilha-1",
                planilha_path=str(planilha),
                alocacoes=[_alocacao("12345")],
                pasta_xmls=str(tmp_path / "xml_inexistente"),
                baixar_pdf=True,
                metodo_pdf="local",
                garantir_pdf=True,
            )

        self.assertFalse(review["ready_for_processing"])
        self.assertEqual(review["totals"]["invalidas"], 1)
        self.assertEqual(review["totals"]["faltantes"], 0)
        self.assertEqual(review["items"][0]["xml_status"], "invalid_key")
        self.assertIn("invalida", review["items"][0]["reason"].lower())

    def test_validate_recovers_missing_keys_via_protheus(self) -> None:
        chave = "35123456789012345678901234567890123456789012"
        with tempfile.TemporaryDirectory(prefix="coverage_service_") as tmp:
            tmp_path = Path(tmp)
            local_xml_dir = tmp_path / "local_xml"
            local_xml_dir.mkdir(parents=True, exist_ok=True)
            recovery_dir = tmp_path / "recovery_xml"
            recovery_dir.mkdir(parents=True, exist_ok=True)
            (recovery_dir / f"NFe{chave}.xml").write_text(_sample_xml(chave), encoding="utf-8")
            planilha = tmp_path / "planilha.xlsx"
            planilha.write_bytes(b"fake")
            store = CoverageStagingStore(tmp_path / "staging", ttl_seconds=60)
            protheus_service = Mock()
            protheus_service.collect.return_value = {
                "coleta_token": "coleta-1",
                "xml": {
                    "processing_dir": str(recovery_dir),
                    "staging_dir": str(recovery_dir),
                    "esperados": 1,
                    "encontrados": 1,
                    "extras_ignorados": 0,
                    "ausentes": 0,
                },
                "boletos": {"pdf_path": None, "pdf_disponivel": False},
            }
            service = CoverageService(coverage_store=store, protheus_service=protheus_service)

            with patch("services.cobertura_lote.gerar_pdf_danfe_bytes", return_value=b"%PDF-1.4\nfake"):
                review = service.validate(
                    planilha_token="planilha-1",
                    planilha_path=str(planilha),
                    alocacoes=[_alocacao(chave)],
                    pasta_xmls=str(local_xml_dir),
                    uf="MG",
                    baixar_pdf=True,
                    metodo_pdf="api",
                    garantir_pdf=True,
                )

        self.assertTrue(review["ready_for_processing"])
        self.assertEqual(review["totals"]["recuperadas_protheus"], 1)
        self.assertEqual(review["items"][0]["xml_status"], "recovered_protheus")
        self.assertEqual(len(review["recovery_reviews"]), 1)
        protheus_service.collect.assert_called_once()


if __name__ == "__main__":
    unittest.main()
