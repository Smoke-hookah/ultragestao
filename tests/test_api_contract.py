from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("ALLOW_NO_API_KEYS", "1")

import api


EXAMPLE_SPREADSHEET = Path(__file__).resolve().parents[1] / "exemplo_de_planilha.xlsx"


class ApiContractSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not EXAMPLE_SPREADSHEET.exists():
            raise unittest.SkipTest(f"Planilha de exemplo ausente: {EXAMPLE_SPREADSHEET}")

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="ultradanfe_test_")
        self.temp_path = Path(self.tempdir.name)
        self.xml_dir = self.temp_path / "xmls"
        self.xml_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir = self.temp_path / "output"
        self.saved_paths: list[str] = []
        self.saved_credentials: list[tuple[str, str]] = []

        self.patches = [
            patch.object(api, "_output_base_dir", return_value=self.output_dir),
            patch.object(api, "obter_pasta_xmls_salva", return_value=str(self.xml_dir)),
            patch.object(api, "salvar_pasta_xmls", side_effect=self.saved_paths.append),
            patch.object(api._PROTHEUS_CREDENTIAL_STORE, "has", return_value=False),
            patch.object(
                api._PROTHEUS_CREDENTIAL_STORE,
                "save",
                side_effect=lambda username, password: self.saved_credentials.append((username, password)),
            ),
            patch.object(api._PROTHEUS_STAGING, "cleanup", return_value=None),
            patch.object(api._COVERAGE_STAGING, "cleanup", return_value=None),
        ]
        for item in self.patches:
            item.start()

        api._PLANILHA_CACHE.clear()
        api.processamento_ativo = False
        self.client = api.app.test_client()

    def tearDown(self) -> None:
        for item in reversed(self.patches):
            item.stop()
        api._PLANILHA_CACHE.clear()
        api.processamento_ativo = False
        self.tempdir.cleanup()

    def _post_planilha_filtros(self) -> dict:
        with EXAMPLE_SPREADSHEET.open("rb") as handle:
            response = self.client.post(
                "/api/planilha-filtros",
                data={"planilha": (handle, EXAMPLE_SPREADSHEET.name)},
                content_type="multipart/form-data",
            )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIsInstance(payload, dict)
        self.assertTrue(payload.get("sucesso"))
        return payload

    def test_get_progresso_returns_expected_shape(self) -> None:
        response = self.client.get("/api/progresso")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(
            set(payload.keys()),
            {"processamento_ativo", "etapa", "percentual", "mensagem", "detalhes"},
        )
        self.assertFalse(payload["processamento_ativo"])

    def test_set_pasta_xmls_accepts_existing_directory(self) -> None:
        response = self.client.post(
            "/api/ui/pasta-xmls/set",
            json={"pasta_xmls": str(self.xml_dir)},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["sucesso"])
        self.assertEqual(payload["pasta_xmls"], str(self.xml_dir))
        self.assertEqual(self.saved_paths, [str(self.xml_dir)])

    def test_planilha_filtros_returns_token_and_aggregates(self) -> None:
        payload = self._post_planilha_filtros()

        self.assertGreater(payload.get("total_alocacoes", 0), 0)
        self.assertTrue(payload.get("planilha_token"))
        self.assertIsInstance(payload.get("rotas"), list)
        self.assertIsInstance(payload.get("placas"), list)
        self.assertIsInstance(payload.get("clientes"), list)

        cached = api._PLANILHA_CACHE[payload["planilha_token"]]
        run_dir = Path(cached["run_dir"])
        self.assertTrue(run_dir.exists())

    def test_protheus_config_endpoints_return_public_contract(self) -> None:
        fake_config = {
            "base_url": "https://protheus.local",
            "selector_version": 1,
            "protheus_user": "operador",
            "uf_branch_map": {"MG": "0202"},
            "has_password": False,
            "config_path": "C:/cfg/protheus_config.json",
            "advanced_config_ready": True,
            "pending_fields": [],
        }
        with patch.object(api, "get_public_protheus_config", return_value=fake_config):
            response = self.client.get("/api/ui/protheus-config")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["sucesso"])
        self.assertEqual(payload["config"]["uf_branch_map"]["MG"], "0202")

        fake_saved = dict(fake_config)
        with patch.object(api, "save_protheus_public_config", return_value={"uf_branch_map": {"MG": "0202"}}), patch.object(
            api,
            "get_public_protheus_config",
            return_value=fake_saved,
        ):
            response = self.client.post(
                "/api/ui/protheus-config",
                json={
                    "base_url": "https://protheus.local",
                    "protheus_user": "operador",
                    "uf_branch_map": {"MG": "0202"},
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["sucesso"])
        self.assertEqual(payload["config"]["base_url"], "https://protheus.local")

    def test_protheus_credenciais_endpoint_saves_password_without_echoing_it(self) -> None:
        fake_config = {
            "base_url": "https://protheus.local",
            "selector_version": 1,
            "protheus_user": "operador",
            "uf_branch_map": {"MG": "0202"},
            "has_password": True,
            "config_path": "C:/cfg/protheus_config.json",
            "advanced_config_ready": True,
            "pending_fields": [],
        }
        with patch.object(api, "save_protheus_public_config", return_value={"protheus_user": "operador"}), patch.object(
            api,
            "get_public_protheus_config",
            return_value=fake_config,
        ):
            response = self.client.post(
                "/api/ui/protheus-credenciais",
                json={"username": "operador", "password": "segredo"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["sucesso"])
        self.assertEqual(self.saved_credentials, [("operador", "segredo")])
        self.assertNotIn("segredo", json.dumps(payload))

    def test_protheus_extrair_returns_review_from_service(self) -> None:
        filtros = self._post_planilha_filtros()
        review = {
            "coleta_token": "coleta-123",
            "uf": "MG",
            "branch_code": "0202",
            "subset_total": 5,
            "nf_range": {"inicio": "1", "fim": "5"},
            "xml": {
                "esperados": 5,
                "encontrados": 5,
                "extras_ignorados": 1,
                "ausentes": 0,
                "staging_dir": "c:/tmp/xml",
                "processing_dir": "c:/tmp/xml_filtrados",
            },
            "boletos": {"pdf_disponivel": True, "pdf_path": "c:/tmp/boletos.pdf"},
            "paths": {"staging_root": "c:/tmp", "diagnostics_dir": "c:/tmp/diag"},
            "pending_fields": [],
            "failures": [],
            "ready_for_processing": True,
        }

        with patch.object(api._PROTHEUS_SERVICE, "collect", return_value=review) as collect_mock:
            response = self.client.post(
                "/api/protheus/extrair",
                json={
                    "planilha_token": filtros["planilha_token"],
                    "uf": "MG",
                    "filtro_rotas": [],
                    "filtro_placas": [],
                    "filtro_clientes": [],
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["sucesso"])
        self.assertEqual(payload["review"]["coleta_token"], "coleta-123")
        collect_mock.assert_called_once()

    def test_cobertura_lote_returns_review_from_service(self) -> None:
        filtros = self._post_planilha_filtros()
        review = {
            "coverage_token": "coverage-123",
            "ready_for_processing": True,
            "totals": {
                "esperadas": 5,
                "validas": 5,
                "com_xml": 5,
                "com_pdf": 5,
                "encontradas_local": 5,
                "recuperadas_protheus": 0,
                "faltantes": 0,
                "invalidas": 0,
                "duplicadas": 0,
                "nao_renderizaveis": 0,
            },
            "routes": [{"rota": "R1", "esperadas": 5, "com_xml": 5, "com_pdf": 5, "faltantes": 0}],
            "items": [],
            "failures": [],
            "paths": {"processing_xml_dir": "c:/tmp/xml", "staging_root": "c:/tmp"},
            "metodo_pdf": {"requested": "api", "resolved": "api_fallback_local"},
            "recovery_reviews": [],
        }

        with patch.object(api._COVERAGE_SERVICE, "validate", return_value=review) as validate_mock:
            response = self.client.post(
                "/api/cobertura-lote",
                json={
                    "planilha_token": filtros["planilha_token"],
                    "filtro_rotas": [],
                    "filtro_placas": [],
                    "filtro_clientes": [],
                    "garantir_pdf": True,
                    "baixar_pdf": True,
                    "metodo_pdf": "api",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["sucesso"])
        self.assertEqual(payload["review"]["coverage_token"], "coverage-123")
        validate_mock.assert_called_once()

    def test_processar_local_accepts_coleta_token_without_manual_xml_or_pdf(self) -> None:
        manifest = {
            "processing_xml_dir": str(self.xml_dir),
            "planilha_path": str(EXAMPLE_SPREADSHEET),
            "boleto_pdf_path": None,
            "filtro_rotas": [],
            "filtro_placas": [],
            "filtro_clientes": [],
        }
        fake_orquestrador = Mock()
        fake_orquestrador.processar_planilha.return_value = (True, [])
        fake_orquestrador.obter_resumo.return_value = {
            "total_alocacoes": 1,
            "sucesso": 1,
            "erros": 0,
            "taxa_sucesso": "100.0%",
            "execucao_timestamp": "2026-04-30_10-00-00",
            "caminho_saida_base": str(self.output_dir / "resultado"),
            "boletos": None,
            "resultados": [],
        }

        with patch.object(api._PROTHEUS_STAGING, "load_manifest", return_value=manifest), patch.object(
            api,
            "Orquestrador",
            return_value=fake_orquestrador,
        ):
            response = self.client.post(
                "/api/processar-local",
                data={
                    "coleta_token": "coleta-123",
                    "tipo_separacao": "rota",
                    "baixar_pdf": "false",
                    "baixar_xml": "false",
                    "juntar_pdfs": "false",
                    "metodo_pdf": "local",
                    "filtro_rotas": "[]",
                    "filtro_placas": "[]",
                    "filtro_clientes": "[]",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["sucesso"])
        fake_orquestrador.processar_planilha.assert_called_once()
        kwargs = fake_orquestrador.processar_planilha.call_args.kwargs
        self.assertEqual(kwargs["pasta_xmls"], str(self.xml_dir))
        self.assertIsNone(kwargs["caminho_boletos_pdf"])

    def test_processar_local_accepts_coverage_token_and_uses_processing_dir(self) -> None:
        manifest = {
            "ready_for_processing": True,
            "processing_xml_dir": str(self.xml_dir),
            "planilha_path": str(EXAMPLE_SPREADSHEET),
            "planilha_token": "planilha-123",
            "boleto_pdf_path": None,
            "filtro_rotas": ["R1"],
            "filtro_placas": [],
            "filtro_clientes": [],
            "metodo_pdf_resolved": "api_fallback_local",
        }
        fake_orquestrador = Mock()
        fake_orquestrador.processar_planilha.return_value = (True, [])
        fake_orquestrador.obter_resumo.return_value = {
            "total_alocacoes": 1,
            "sucesso": 1,
            "erros": 0,
            "taxa_sucesso": "100.0%",
            "execucao_timestamp": "2026-04-30_10-00-00",
            "caminho_saida_base": str(self.output_dir / "resultado"),
            "boletos": None,
            "resultados": [],
        }

        with patch.object(api._COVERAGE_STAGING, "load_manifest", return_value=manifest), patch.object(
            api,
            "Orquestrador",
            return_value=fake_orquestrador,
        ):
            response = self.client.post(
                "/api/processar-local",
                data={
                    "coverage_token": "coverage-123",
                    "tipo_separacao": "rota",
                    "baixar_pdf": "true",
                    "baixar_xml": "false",
                    "juntar_pdfs": "false",
                    "metodo_pdf": "api",
                    "filtro_rotas": "[]",
                    "filtro_placas": "[]",
                    "filtro_clientes": "[]",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["sucesso"])
        kwargs = fake_orquestrador.processar_planilha.call_args.kwargs
        self.assertEqual(kwargs["pasta_xmls"], str(self.xml_dir))
        self.assertEqual(kwargs["metodo_pdf"], "api_fallback_local")
        self.assertEqual(kwargs["filtro_rotas"], ["R1"])

    def test_processar_local_rejeita_coverage_token_bloqueado(self) -> None:
        with patch.object(
            api._COVERAGE_STAGING,
            "load_manifest",
            return_value={"ready_for_processing": False},
        ):
            response = self.client.post(
                "/api/processar-local",
                data={"coverage_token": "coverage-123", "tipo_separacao": "rota"},
            )

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertFalse(payload["sucesso"])
        self.assertIn("coverage_token bloqueado", payload["mensagem"])

    def test_processar_local_with_empty_xml_dir_returns_structured_errors_and_preserves_cache_for_reuse(self) -> None:
        filtros = self._post_planilha_filtros()
        token = filtros["planilha_token"]
        primeira_rota = (filtros.get("rotas") or [None])[0]
        dados = {
            "planilha_token": token,
            "tipo_separacao": "rota",
            "baixar_pdf": "false",
            "baixar_xml": "false",
            "juntar_pdfs": "false",
            "metodo_pdf": "local",
            "filtro_rotas": json.dumps([primeira_rota]) if primeira_rota else "[]",
            "filtro_placas": "[]",
            "filtro_clientes": "[]",
        }

        cached_before = dict(api._PLANILHA_CACHE[token])
        last_access_before = float(cached_before.get("last_accessed", 0))

        for _ in range(2):
            response = self.client.post("/api/processar-local", data=dados)

            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertIsInstance(payload, dict)
            self.assertIn("sucesso", payload)
            self.assertIn("resumo", payload)

            resumo = payload["resumo"]
            self.assertGreater(resumo.get("total_alocacoes", 0), 0)
            self.assertEqual(resumo.get("sucesso"), 0)
            self.assertEqual(resumo.get("total_alocacoes"), resumo.get("erros"))

            resultados = resumo.get("resultados") or []
            self.assertTrue(resultados)
            self.assertTrue(
                any(item.get("mensagem") == "XML não encontrado na pasta para esta chave" for item in resultados)
            )

        self.assertIn(token, api._PLANILHA_CACHE)
        cached_after = api._PLANILHA_CACHE[token]
        self.assertGreaterEqual(float(cached_after.get("last_accessed", 0)), last_access_before)
        self.assertTrue(Path(cached_after["run_dir"]).exists())

    def test_cleanup_stale_temp_dirs_removes_old_temp_directories(self) -> None:
        stale_dir = self.output_dir / "ultradanfe_filtros_stale"
        stale_dir.mkdir(parents=True, exist_ok=True)
        marker = stale_dir / "marker.txt"
        marker.write_text("old", encoding="utf-8")

        stale_time = api.time.time() - api._PLANILHA_CACHE_TTL_SECONDS - 5
        os.utime(stale_dir, (stale_time, stale_time))
        os.utime(marker, (stale_time, stale_time))

        api._cleanup_stale_temp_dirs()

        self.assertFalse(stale_dir.exists())


if __name__ == "__main__":
    unittest.main()
