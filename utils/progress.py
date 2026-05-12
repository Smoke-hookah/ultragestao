"""Estado compartilhado de progresso (backend).

Este módulo existe para evitar import circular entre `api.py` e `services/orquestrador.py`.
"""

from __future__ import annotations

from typing import Any, Dict


progresso_atual: Dict[str, Any] = {
    "etapa": "",
    "percentual": 0,
    "mensagem": "",
    "detalhes": "",
}


def set_progresso(etapa: str = "", percentual: int = 0, mensagem: str = "", detalhes: str = "") -> None:
    # Mutação in-place para manter referências estáveis em todo o app.
    progresso_atual["etapa"] = etapa
    progresso_atual["percentual"] = int(percentual or 0)
    progresso_atual["mensagem"] = mensagem
    progresso_atual["detalhes"] = detalhes
