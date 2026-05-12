from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from services.danfe_local import (
    DanfeLocalError,
    escolher_executor_local_pdf,
    gerar_pdf_danfe_task,
)


class LocalPdfRuntimeTests(unittest.TestCase):
    def test_selector_prefers_thread_for_small_batches(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("LOCAL_PDF_EXECUTOR", None)
            os.environ.pop("LOCAL_PDF_WORKERS", None)
            with patch("services.danfe_local.os.cpu_count", return_value=8):
                mode, workers = escolher_executor_local_pdf(8)

        self.assertEqual(mode, "thread")
        self.assertEqual(workers, 32)

    def test_selector_prefers_process_for_large_batches(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("LOCAL_PDF_EXECUTOR", None)
            os.environ.pop("LOCAL_PDF_WORKERS", None)
            with patch("services.danfe_local.os.cpu_count", return_value=8):
                mode, workers = escolher_executor_local_pdf(64)

        self.assertEqual(mode, "process")
        self.assertEqual(workers, 8)

    def test_selector_honors_env_override(self) -> None:
        with patch.dict(
            os.environ,
            {"LOCAL_PDF_EXECUTOR": "process", "LOCAL_PDF_WORKERS": "3"},
            clear=False,
        ):
            with patch("services.danfe_local.os.cpu_count", return_value=16):
                mode, workers = escolher_executor_local_pdf(4)

        self.assertEqual(mode, "process")
        self.assertEqual(workers, 3)

    def test_task_returns_structured_error_when_xml_is_missing(self) -> None:
        chave, ok, pdf_bytes, msg = gerar_pdf_danfe_task("abc", "")

        self.assertEqual(chave, "abc")
        self.assertFalse(ok)
        self.assertIsNone(pdf_bytes)
        self.assertIn("XML ausente", msg)

    def test_task_rejects_non_nfe_xml(self) -> None:
        chave, ok, pdf_bytes, msg = gerar_pdf_danfe_task(
            "evt",
            '<retInutNFe xmlns="http://www.portalfiscal.inf.br/nfe"></retInutNFe>',
        )

        self.assertEqual(chave, "evt")
        self.assertFalse(ok)
        self.assertIsNone(pdf_bytes)
        self.assertIn("NF-e renderizavel", msg)

    def test_task_wraps_generator_success_and_failure(self) -> None:
        with patch("services.danfe_local.gerar_pdf_danfe_bytes", return_value=b"pdf"):
            chave_ok, ok, pdf_bytes, msg_ok = gerar_pdf_danfe_task("123", "<xml/>")

        self.assertEqual(chave_ok, "123")
        self.assertTrue(ok)
        self.assertEqual(pdf_bytes, b"pdf")
        self.assertIn("sucesso", msg_ok.lower())

        with patch(
            "services.danfe_local.gerar_pdf_danfe_bytes",
            side_effect=DanfeLocalError("falha controlada"),
        ):
            chave_err, ok_err, pdf_err, msg_err = gerar_pdf_danfe_task("456", "<xml/>")

        self.assertEqual(chave_err, "456")
        self.assertFalse(ok_err)
        self.assertIsNone(pdf_err)
        self.assertEqual(msg_err, "falha controlada")


if __name__ == "__main__":
    unittest.main()
