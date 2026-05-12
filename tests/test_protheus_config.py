from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from services.protheus_config import (
    get_public_protheus_config,
    list_protheus_config_issues,
    load_protheus_config,
    resolve_branch_for_uf,
    save_protheus_public_config,
)


class ProtheusConfigTests(unittest.TestCase):
    def test_save_and_resolve_branch_mapping(self) -> None:
        with tempfile.TemporaryDirectory(prefix="protheus_cfg_") as tmp:
            config_path = Path(tmp) / "protheus_config.json"
            save_protheus_public_config(
                {
                    "base_url": "https://protheus.local",
                    "protheus_user": "operador",
                    "uf_branch_map": {"mg": "0202", "RJ": "0101"},
                },
                config_path=config_path,
            )

            config = load_protheus_config(config_path)
            self.assertEqual(config["uf_branch_map"]["MG"], "0202")
            self.assertEqual(resolve_branch_for_uf(config, "mg"), "0202")
            self.assertEqual(resolve_branch_for_uf(config, "RJ"), "0101")

    def test_public_config_reports_pending_fields_for_placeholders(self) -> None:
        with tempfile.TemporaryDirectory(prefix="protheus_cfg_") as tmp:
            config_path = Path(tmp) / "protheus_config.json"
            public = get_public_protheus_config(config_path=config_path, has_password=False)

            self.assertFalse(public["advanced_config_ready"])
            self.assertIn("base_url", public["pending_fields"])
            self.assertIn("login.success_selector", public["pending_fields"])

    def test_list_config_issues_requires_branch_and_export_selectors(self) -> None:
        issues = list_protheus_config_issues({"base_url": "https://protheus.local", "uf_branch_map": {}})
        self.assertIn("uf_branch_map", issues)
        self.assertIn("branch.input_selector", issues)


if __name__ == "__main__":
    unittest.main()
