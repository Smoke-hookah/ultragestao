from __future__ import annotations

import unittest
from unittest.mock import patch

from services.gestor_saida import GestorSaida


class _FakePage:
    def __init__(self, text: str) -> None:
        self._text = text

    def extract_text(self) -> str:
        return self._text


class _FakeReader:
    def __init__(self, texts: list[str]) -> None:
        self.pages = [_FakePage(text) for text in texts]


class BoletoExtractionTests(unittest.TestCase):
    def test_extract_document_candidates_supports_common_labels(self) -> None:
        gestor = GestorSaida()
        texto = """
        Nº documento: 3000017402
        Nosso número: 99887766
        Seu numero: 99887766
        Número do documento: 3000017402
        """

        candidatos = gestor._extrair_candidatos_documento(texto)

        self.assertEqual(candidatos, ["3000017402", "99887766"])
        self.assertEqual(gestor._extrair_numero_documento(texto), "3000017402")

    def test_extract_documentos_merges_consecutive_pages_with_same_document(self) -> None:
        gestor = GestorSaida()
        textos = [
            "Nº documento: 3000017402\nPagador: MERCADO TESTE",
            "Número do documento: 3000017402\ncontinuação do boleto",
            "Nº documento: 3000017403\nPagador: MERCADO TESTE 2",
        ]

        with patch("services.gestor_saida.PdfReader", return_value=_FakeReader(textos)):
            with patch.object(GestorSaida, "_extrair_texto_pagina_docling", return_value=""):
                documentos, nao_identificadas = gestor.extrair_documentos_boletos("fake.pdf")

        self.assertEqual(nao_identificadas, [])
        self.assertEqual(len(documentos), 2)
        self.assertEqual(documentos[0]["doc_digits"], "3000017402")
        self.assertEqual(documentos[0]["pages"], [0, 1])
        self.assertEqual(documentos[0]["doc_candidates"], ["3000017402"])
        self.assertEqual(documentos[1]["doc_digits"], "3000017403")
        self.assertEqual(documentos[1]["pages"], [2])


if __name__ == "__main__":
    unittest.main()
