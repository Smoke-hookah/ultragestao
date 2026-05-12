"""Staging e manifestos da coleta Protheus."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import shutil
import time
import uuid
from typing import Any, Dict, Optional

from config import OUTPUT_DIR


DEFAULT_COLETA_TTL_SECONDS = 60 * 60


@dataclass
class ProtheusStagingStore:
    base_dir: Path
    ttl_seconds: int = DEFAULT_COLETA_TTL_SECONDS

    def __post_init__(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _token_dir(self, token: str) -> Path:
        return self.base_dir / str(token).strip()

    def _manifest_path(self, token: str) -> Path:
        return self._token_dir(token) / "manifest.json"

    def create(self) -> tuple[str, Path]:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        token = f"{timestamp}_{uuid.uuid4().hex[:12]}"
        root = self._token_dir(token)
        root.mkdir(parents=True, exist_ok=True)
        return token, root

    def save_manifest(self, token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        root = self._token_dir(token)
        root.mkdir(parents=True, exist_ok=True)
        now = int(time.time())
        manifest = dict(payload)
        manifest["token"] = token
        manifest["last_accessed"] = now
        manifest.setdefault("created", now)
        self._manifest_path(token).write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return manifest

    def load_manifest(self, token: str, touch: bool = True) -> Optional[Dict[str, Any]]:
        path = self._manifest_path(token)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None

        now = int(time.time())
        age = now - int(payload.get("last_accessed", payload.get("created", now)) or now)
        if age > int(self.ttl_seconds):
            self.discard(token)
            return None

        if touch:
            payload["last_accessed"] = now
            path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return payload

    def discard(self, token: str) -> None:
        root = self._token_dir(token)
        if root.exists():
            shutil.rmtree(root, ignore_errors=True)

    def cleanup(self) -> None:
        if not self.base_dir.exists():
            return
        now = int(time.time())
        for child in self.base_dir.iterdir():
            if not child.is_dir():
                continue
            manifest_path = child / "manifest.json"
            if not manifest_path.exists():
                continue
            try:
                payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception:
                shutil.rmtree(child, ignore_errors=True)
                continue
            age = now - int(payload.get("last_accessed", payload.get("created", now)) or now)
            if age > int(self.ttl_seconds):
                shutil.rmtree(child, ignore_errors=True)


def criar_store_coleta_protheus_padrao() -> ProtheusStagingStore:
    return ProtheusStagingStore(OUTPUT_DIR / "coleta_protheus")
