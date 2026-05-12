from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from services.historico_boletos import HistoricoBoletos


class HistoricoBoletosTests(unittest.TestCase):
    def test_registra_e_reusa_extracao_por_hash(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ultradanfe_hist_boletos_") as tmpdir:
            base = Path(tmpdir)
            historico = HistoricoBoletos(
                db_path=base / "boletos.sqlite3",
                sources_dir=base / "sources",
            )
            source_hash = "abc123"
            documentos = [
                {
                    "doc_digits": "3000017402",
                    "doc_candidates": ["3000017402"],
                    "pages": [0, 1],
                    "texto": "boleto mercado teste",
                    "pagador": "MERCADO TESTE",
                    "pagador_cnpj": "12345678000199",
                    "valor_documento": 152.64,
                    "numeric_blocks": ["3000017402"],
                    "anonimo": False,
                }
            ]
            nao_identificadas = [3]

            ok = historico.registrar_extracao_pdf(
                source_hash,
                documentos,
                nao_identificadas,
            )
            cached = historico.obter_extracao_pdf(source_hash)

        self.assertTrue(ok)
        self.assertIsNotNone(cached)
        self.assertEqual(cached["source_hash"], source_hash)
        self.assertEqual(cached["page_count"], 2)
        self.assertEqual(cached["nao_identificadas"], [3])
        self.assertEqual(cached["documentos"], documentos)


if __name__ == "__main__":
    unittest.main()
