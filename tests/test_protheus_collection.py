from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from models.alocacao import Alocacao
from services.protheus_automation import ProtheusAutomationResult
from services.protheus_coleta import ProtheusCollectionService
from services.protheus_staging import ProtheusStagingStore


def _sample_xml(chave: str) -> str:
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">'
        f'<protNFe><infProt><chNFe>{chave}</chNFe></infProt></protNFe>'
        f'<NFe><infNFe Id="NFe{chave}"></infNFe></NFe>'
        "</nfeProc>"
    )


class _FakeCredentialStore:
    def read(self):
        return {"username": "operador", "password": "segredo"}


class _FakeCollector:
    def __init__(self, expected_key: str, extra_key: str) -> None:
        self.expected_key = expected_key
        self.extra_key = extra_key

    def collect_branch(self, request, _config, _credentials, progress_callback=None):
        request.xml_dir.mkdir(parents=True, exist_ok=True)
        request.boleto_pdf_path.parent.mkdir(parents=True, exist_ok=True)
        request.diagnostics_dir.mkdir(parents=True, exist_ok=True)
        (request.xml_dir / f"NFe{self.expected_key}.xml").write_text(_sample_xml(self.expected_key), encoding="utf-8")
        (request.xml_dir / f"NFe{self.extra_key}.xml").write_text(_sample_xml(self.extra_key), encoding="utf-8")
        request.boleto_pdf_path.write_bytes(b"%PDF-1.4\n%fake")
        if progress_callback:
            progress_callback("protheus_xml", 50, "extraindo", request.branch_code)
        return ProtheusAutomationResult(
            xml_dir=request.xml_dir,
            boleto_pdf_path=request.boleto_pdf_path,
            download_manifest={"xml_export": {"files": []}, "boleto_export": {"download": str(request.boleto_pdf_path)}},
        )


class ProtheusCollectionServiceTests(unittest.TestCase):
    def test_collect_builds_review_and_filters_extra_xmls(self) -> None:
        chave_esperada = "35123456789012345678901234567890123456789012"
        chave_extra = "35999999999999999999999999999999999999999999"
        alocacoes = [
            Alocacao(
                chave=chave_esperada,
                placa="ABC1234",
                rota="R1",
                pedido="1",
                nf="1001",
                cliente="Cliente A",
                cidade="SP",
                tipo_cliente="Normal",
            )
        ]

        with tempfile.TemporaryDirectory(prefix="protheus_collect_") as tmp:
            tmp_path = Path(tmp)
            planilha_path = tmp_path / "planilha.xlsx"
            planilha_path.write_bytes(b"fake-xlsx")
            store = ProtheusStagingStore(tmp_path / "staging", ttl_seconds=60)
            service = ProtheusCollectionService(
                staging_store=store,
                credential_store=_FakeCredentialStore(),
                collector=_FakeCollector(chave_esperada, chave_extra),
            )

            with patch("services.protheus_coleta.load_protheus_config", return_value={"uf_branch_map": {"MG": "0202"}}), patch(
                "services.protheus_coleta.list_protheus_config_issues",
                return_value=[],
            ), patch(
                "services.protheus_coleta.resolve_branch_for_uf",
                return_value="0202",
            ), patch(
                "services.protheus_coleta.get_public_protheus_config",
                return_value={"config_path": "C:/cfg/protheus_config.json", "pending_fields": []},
            ):
                review = service.collect(
                    planilha_token="token-1",
                    planilha_path=str(planilha_path),
                    alocacoes=alocacoes,
                    uf="MG",
                )

            self.assertEqual(review["xml"]["esperados"], 1)
            self.assertEqual(review["xml"]["encontrados"], 1)
            self.assertEqual(review["xml"]["extras_ignorados"], 1)
            self.assertTrue(review["boletos"]["pdf_disponivel"])
            self.assertTrue(Path(review["xml"]["processing_dir"]).exists())
            processing_files = list(Path(review["xml"]["processing_dir"]).glob("*.xml"))
            self.assertEqual(len(processing_files), 1)
            self.assertIn(chave_esperada, processing_files[0].name)


if __name__ == "__main__":
    unittest.main()
