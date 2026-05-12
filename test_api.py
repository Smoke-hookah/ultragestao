"""Smoke test manual para a API atual do UltraDanfeXML.

Uso:
    python test_api.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import requests


BASE_URL = "http://localhost:5000"
EXAMPLE_SPREADSHEET = Path(__file__).with_name("exemplo_de_planilha.xlsx")


def print_json(label: str, payload) -> None:
    print(f"   {label}: {json.dumps(payload, indent=2, ensure_ascii=False)}")


def main() -> int:
    print("=" * 72)
    print("SMOKE TEST MANUAL - API ATUAL")
    print("=" * 72)

    try:
        resp = requests.get(f"{BASE_URL}/api/progresso", timeout=5)
        resp.raise_for_status()
        print("\n1. GET /api/progresso")
        print(f"   Status: {resp.status_code}")
        print_json("Response", resp.json())
    except Exception as exc:
        print(f"\n1. GET /api/progresso\n   ERRO: {exc}")
        return 1

    try:
        resp = requests.get(f"{BASE_URL}/api/ui/pasta-xmls", timeout=5)
        resp.raise_for_status()
        print("\n2. GET /api/ui/pasta-xmls")
        print(f"   Status: {resp.status_code}")
        print_json("Response", resp.json())
    except Exception as exc:
        print(f"\n2. GET /api/ui/pasta-xmls\n   ERRO: {exc}")
        return 1

    if not EXAMPLE_SPREADSHEET.exists():
        print(f"\n3. POST /api/planilha-filtros\n   AVISO: planilha de exemplo ausente: {EXAMPLE_SPREADSHEET}")
        return 0

    try:
        with EXAMPLE_SPREADSHEET.open("rb") as handle:
            resp = requests.post(
                f"{BASE_URL}/api/planilha-filtros",
                files={
                    "planilha": (
                        EXAMPLE_SPREADSHEET.name,
                        handle,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
                timeout=30,
            )
        resp.raise_for_status()
        payload = resp.json()
        print("\n3. POST /api/planilha-filtros")
        print(f"   Status: {resp.status_code}")
        print(f"   Total alocações: {payload.get('total_alocacoes')}")
        print(f"   Rotas: {len(payload.get('rotas', []))}")
        print(f"   Placas: {len(payload.get('placas', []))}")
        print(f"   Clientes: {len(payload.get('clientes', []))}")
        print(f"   Token: {payload.get('planilha_token')}")
    except Exception as exc:
        print(f"\n3. POST /api/planilha-filtros\n   ERRO: {exc}")
        return 1

    print("\n" + "=" * 72)
    print("SMOKE TEST CONCLUÍDO")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
