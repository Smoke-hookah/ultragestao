"""Persistência simples de histórico de PUT (upload de XML) por chave.

Regra: se uma chave teve PUT com sucesso nos últimos N dias,
pula o PUT e faz somente GET.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from config import CONFIG_DIR
from utils.logger import logger


def _utcnow_local() -> datetime:
    # O sistema já trabalha em horário local; manter consistente.
    return datetime.now()


@dataclass
class HistoricoPut:
    caminho: Path
    dias_validade: int = 60

    def carregar(self) -> Dict[str, dict]:
        """Retorna mapa {chave: {"ts": iso_datetime, "api_key": str|None}}.

        Compatibilidade:
        - Formato antigo: {chave: "2026-01-12T01:48:22"}
        - Formato novo: {chave: {"ts": "...", "api_key": "..."}}
        """
        if not self.caminho.exists():
            return {}
        try:
            raw = json.loads(self.caminho.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return {}

            out: Dict[str, dict] = {}
            for k, v in raw.items():
                chave = str(k)
                if isinstance(v, str):
                    out[chave] = {"ts": v, "api_key": None}
                elif isinstance(v, dict):
                    ts = v.get("ts") or v.get("timestamp") or v.get("data")
                    api_key = v.get("api_key") or v.get("apikey") or v.get("apiKey")
                    if ts:
                        out[chave] = {"ts": str(ts), "api_key": str(api_key) if api_key else None}
                # valores desconhecidos: ignora
            return out
        except Exception as e:
            logger.warning(f"Não foi possível ler histórico de PUT ({self.caminho}): {e}")
            return {}

    def salvar(self, dados: Dict[str, dict]) -> None:
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        self.caminho.write_text(
            json.dumps(dados, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def registrar_sucesso(self, chave: str, api_key: Optional[str], dados: Dict[str, dict]) -> Dict[str, dict]:
        dados[str(chave)] = {
            "ts": _utcnow_local().isoformat(timespec="seconds"),
            "api_key": api_key,
        }
        return dados

    def dentro_da_validade(self, chave: str, dados: Dict[str, dict]) -> bool:
        entry = dados.get(str(chave))
        if not entry:
            return False
        try:
            dt = datetime.fromisoformat(str(entry.get("ts")))
        except Exception:
            return False
        return _utcnow_local() - dt <= timedelta(days=self.dias_validade)

    def api_key_para_chave(self, chave: str, dados: Dict[str, dict]) -> Optional[str]:
        entry = dados.get(str(chave))
        if not entry:
            return None
        api_key = entry.get("api_key")
        return str(api_key) if api_key else None


def criar_historico_padrao() -> HistoricoPut:
    return HistoricoPut(caminho=CONFIG_DIR / "historico_put.json", dias_validade=60)
