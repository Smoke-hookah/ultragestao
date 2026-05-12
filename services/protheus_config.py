"""Configuracao operacional da coleta Protheus."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from config import CONFIG_DIR


PROTHEUS_CONFIG_FILENAME = "protheus_config.json"
PLACEHOLDER_VALUES = {"", "__PREENCHER__", "__CONFIGURAR__"}


DEFAULT_PROTHEUS_CONFIG: Dict[str, Any] = {
    "base_url": "",
    "selector_version": 1,
    "protheus_user": "",
    "uf_branch_map": {
        "MG": "0202",
        "RJ": "0101",
        "SP": "0201",
    },
    "timeouts": {
        "default_ms": 12000,
        "navigation_ms": 30000,
        "download_ms": 180000,
        "file_settle_seconds": 3,
        "poll_interval_ms": 500,
    },
    "browser": {
        "headless": False,
        "slow_mo_ms": 0,
        "viewport": {"width": 1440, "height": 900},
    },
    "login": {
        "username_selector": "input[name='username']",
        "password_selector": "input[type='password']",
        "submit_selector": "button[type='submit']",
        "success_selector": "__PREENCHER__",
    },
    "branch": {
        "open_steps": [],
        "input_selector": "__PREENCHER__",
        "confirm_selector": "__PREENCHER__",
        "success_selector": "__PREENCHER__",
    },
    "xml_export": {
        "mode": "target_dir",
        "open_steps": [],
        "nf_from_selector": "__PREENCHER__",
        "nf_to_selector": "__PREENCHER__",
        "target_dir_selector": "__PREENCHER__",
        "submit_selector": "__PREENCHER__",
        "completion_selector": "__PREENCHER__",
        "expected_glob": "*.xml",
        "extract_zip_downloads": True,
    },
    "boleto_export": {
        "mode": "download",
        "open_steps": [],
        "nf_from_selector": "__PREENCHER__",
        "nf_to_selector": "__PREENCHER__",
        "submit_selector": "__PREENCHER__",
        "completion_selector": "__PREENCHER__",
        "download_filename": "boletos.pdf",
    },
}


def _config_path(config_path: Path | None = None) -> Path:
    return Path(config_path or (CONFIG_DIR / PROTHEUS_CONFIG_FILENAME))


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _normalize_uf_branch_map(value: Dict[str, Any] | None) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for raw_key, raw_value in (value or {}).items():
        key = str(raw_key or "").strip().upper()
        branch = str(raw_value or "").strip()
        if key and branch:
            result[key] = branch
    return result


def ensure_protheus_config(config_path: Path | None = None) -> Path:
    path = _config_path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(
            json.dumps(DEFAULT_PROTHEUS_CONFIG, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    return path


def load_protheus_config(config_path: Path | None = None) -> Dict[str, Any]:
    path = ensure_protheus_config(config_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        payload = {}

    merged = _deep_merge(DEFAULT_PROTHEUS_CONFIG, payload if isinstance(payload, dict) else {})
    merged["uf_branch_map"] = _normalize_uf_branch_map(merged.get("uf_branch_map"))
    return merged


def save_protheus_public_config(
    payload: Dict[str, Any],
    config_path: Path | None = None,
) -> Dict[str, Any]:
    path = ensure_protheus_config(config_path)
    current = load_protheus_config(path)

    base_url = str(payload.get("base_url") or current.get("base_url") or "").strip()
    user = str(payload.get("protheus_user") or current.get("protheus_user") or "").strip()
    uf_branch_map = _normalize_uf_branch_map(payload.get("uf_branch_map") or current.get("uf_branch_map"))

    current["base_url"] = base_url
    current["protheus_user"] = user
    current["uf_branch_map"] = uf_branch_map

    path.write_text(json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8")
    return current


def resolve_branch_for_uf(config: Dict[str, Any], uf: str) -> str:
    uf_key = str(uf or "").strip().upper()
    branch = str((config.get("uf_branch_map") or {}).get(uf_key) or "").strip()
    if not uf_key:
        raise ValueError("UF obrigatoria para selecionar a filial do Protheus")
    if not branch:
        raise ValueError(f"Filial nao configurada para a UF {uf_key}")
    return branch


def _is_placeholder(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() in PLACEHOLDER_VALUES
    return False


def list_protheus_config_issues(config: Dict[str, Any]) -> List[str]:
    issues: List[str] = []

    if _is_placeholder(config.get("base_url")):
        issues.append("base_url")

    login = config.get("login") or {}
    for field in ("username_selector", "password_selector", "submit_selector", "success_selector"):
        if _is_placeholder(login.get(field)):
            issues.append(f"login.{field}")

    branch = config.get("branch") or {}
    for field in ("input_selector", "confirm_selector", "success_selector"):
        if _is_placeholder(branch.get(field)):
            issues.append(f"branch.{field}")

    xml_export = config.get("xml_export") or {}
    xml_required: Iterable[str] = (
        "nf_from_selector",
        "nf_to_selector",
        "submit_selector",
        "completion_selector",
    )
    if str(xml_export.get("mode") or "").strip().lower() == "target_dir":
        xml_required = (*xml_required, "target_dir_selector")
    for field in xml_required:
        if _is_placeholder(xml_export.get(field)):
            issues.append(f"xml_export.{field}")

    boleto_export = config.get("boleto_export") or {}
    for field in ("nf_from_selector", "nf_to_selector", "submit_selector", "completion_selector"):
        if _is_placeholder(boleto_export.get(field)):
            issues.append(f"boleto_export.{field}")

    if not _normalize_uf_branch_map(config.get("uf_branch_map")):
        issues.append("uf_branch_map")

    return sorted(set(issues))


def get_public_protheus_config(config_path: Path | None = None, has_password: bool = False) -> Dict[str, Any]:
    path = ensure_protheus_config(config_path)
    config = load_protheus_config(path)
    issues = list_protheus_config_issues(config)
    return {
        "base_url": config.get("base_url") or "",
        "selector_version": int(config.get("selector_version") or 1),
        "protheus_user": config.get("protheus_user") or "",
        "uf_branch_map": _normalize_uf_branch_map(config.get("uf_branch_map")),
        "has_password": bool(has_password),
        "config_path": str(path),
        "advanced_config_ready": len(issues) == 0,
        "pending_fields": issues,
    }
