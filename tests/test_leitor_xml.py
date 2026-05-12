from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from services.leitor_xml import LeitorXML


class LeitorXmlTests(unittest.TestCase):
    def test_carregar_mapa_ignora_xml_que_nao_e_nfe(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ultradanfe_leitor_xml_") as tmpdir:
            pasta = Path(tmpdir)
            chave_valida = "35260112345678000123550010000000011000000001"
            chave_invalida = "35260112345678000123550010000000011000000002"

            (pasta / f"{chave_invalida}-inu.xml").write_text(
                (
                    '<retInutNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">'
                    "<infInut></infInut>"
                    "</retInutNFe>"
                ),
                encoding="utf-8",
            )
            (pasta / f"{chave_valida}-nfe.xml").write_text(
                (
                    '<NFe xmlns="http://www.portalfiscal.inf.br/nfe">'
                    f'<infNFe Id="NFe{chave_valida}" versao="4.00"></infNFe>'
                    "</NFe>"
                ),
                encoding="utf-8",
            )

            leitor = LeitorXML(str(pasta))
            mapa, stats = leitor.carregar_mapa_chave_para_caminho(
                {chave_valida, chave_invalida}
            )

        self.assertEqual(set(mapa.keys()), {chave_valida})
        self.assertEqual(stats["ignorados_tipo"], 1)
        self.assertEqual(stats["mapeadas"], 1)

    def test_inventariar_chaves_registra_duplicidade_e_nao_renderizavel_por_chave(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ultradanfe_leitor_xml_") as tmpdir:
            pasta = Path(tmpdir)
            chave_duplicada = "35260112345678000123550010000000011000000001"
            chave_evento = "35260112345678000123550010000000011000000002"

            for suffix in ("a", "b"):
                (pasta / f"NFe{chave_duplicada}-{suffix}.xml").write_text(
                    (
                        '<NFe xmlns="http://www.portalfiscal.inf.br/nfe">'
                        f'<infNFe Id="NFe{chave_duplicada}" versao="4.00"></infNFe>'
                        "</NFe>"
                    ),
                    encoding="utf-8",
                )
            (pasta / f"{chave_evento}-evento.xml").write_text(
                (
                    '<procEventoNFe xmlns="http://www.portalfiscal.inf.br/nfe">'
                    f"<evento><infEvento><chNFe>{chave_evento}</chNFe></infEvento></evento>"
                    "</procEventoNFe>"
                ),
                encoding="utf-8",
            )

            leitor = LeitorXML(str(pasta))
            inventory = leitor.inventariar_chaves({chave_duplicada, chave_evento})

        self.assertIn(chave_duplicada, inventory["duplicates"])
        self.assertIn(chave_evento, inventory["non_renderable"])
        self.assertEqual(inventory["stats"]["duplicadas"], 1)
        self.assertEqual(inventory["stats"]["ignorados_tipo"], 1)

    def test_processar_todos_xmls_marca_nao_renderizavel_como_erro(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ultradanfe_leitor_xml_") as tmpdir:
            pasta = Path(tmpdir)
            (pasta / "evento.xml").write_text(
                (
                    '<procEventoNFe xmlns="http://www.portalfiscal.inf.br/nfe">'
                    "<evento></evento>"
                    "</procEventoNFe>"
                ),
                encoding="utf-8",
            )

            leitor = LeitorXML(str(pasta))
            resultado = leitor.processar_todos_xmls()

        self.assertEqual(resultado["total"], 1)
        self.assertEqual(resultado["processados"], 0)
        self.assertEqual(resultado["erros"], 1)
        self.assertEqual(
            resultado["arquivos"][0]["erro"],
            "XML nao e NF-e renderizavel",
        )


if __name__ == "__main__":
    unittest.main()
