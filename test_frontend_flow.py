"""Smoke test manual do fluxo frontend/backend atual.

Uso:
    python test_frontend_flow.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import requests


BASE_URL = "http://localhost:5000"
FRONTEND_URL = "http://localhost:8080"
EXAMPLE_SPREADSHEET = Path(__file__).with_name("exemplo_de_planilha.xlsx")


def main() -> int:
    print("=" * 80)
    print("SMOKE TEST MANUAL - FLUXO FRONTEND/BACKEND")
    print("=" * 80)

    try:
        resp = requests.get(f"{BASE_URL}/api/progresso", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        print("\n[1/5] Backend respondeu em /api/progresso")
        print(f"   Status: {resp.status_code}")
        print(f"   Processamento ativo: {data.get('processamento_ativo')}")
    except Exception as exc:
        print(f"\n[1/5] ERRO: backend não respondeu: {exc}")
        return 1

    try:
        resp = requests.get(f"{BASE_URL}/api/ui/pasta-xmls", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        pasta = data.get("pasta_xmls")
        print("\n[2/5] Configuração atual da pasta de XMLs")
        print(f"   Status: {resp.status_code}")
        print(f"   Pasta: {pasta}")
        if pasta and not Path(pasta).exists():
            print("   AVISO: a pasta salva não existe mais no disco.")
    except Exception as exc:
        print(f"\n[2/5] ERRO: falha ao consultar pasta de XMLs: {exc}")
        return 1

    if not EXAMPLE_SPREADSHEET.exists():
        print(f"\n[3/5] AVISO: planilha de exemplo ausente: {EXAMPLE_SPREADSHEET}")
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
        filtros = resp.json()
        token = filtros.get("planilha_token")
        rotas = filtros.get("rotas") or []
        print("\n[3/5] /api/planilha-filtros")
        print(f"   Total alocações: {filtros.get('total_alocacoes')}")
        print(f"   Rotas: {len(rotas)}")
        print(f"   Token: {token}")
    except Exception as exc:
        print(f"\n[3/5] ERRO: falha ao carregar filtros: {exc}")
        return 1

    try:
        payload = {
            "planilha_token": token or "",
            "tipo_separacao": "rota",
            "baixar_pdf": "false",
            "baixar_xml": "false",
            "juntar_pdfs": "false",
            "metodo_pdf": "local",
            "filtro_rotas": json.dumps([rotas[0]]) if rotas else "[]",
            "filtro_placas": "[]",
            "filtro_clientes": "[]",
        }
        resp = requests.post(
            f"{BASE_URL}/api/processar-local",
            data=payload,
            timeout=60,
        )
        print("\n[4/5] /api/processar-local")
        print(f"   Status: {resp.status_code}")
        data = resp.json()
        print(f"   Sucesso geral: {data.get('sucesso')}")
        resumo = data.get("resumo") or {}
        print(f"   Total: {resumo.get('total_alocacoes')}")
        print(f"   Sucesso: {resumo.get('sucesso')}")
        print(f"   Erros: {resumo.get('erros')}")
        if resumo.get("resultados"):
            primeiro = resumo["resultados"][0]
            print(f"   Primeiro resultado: {primeiro.get('etapa')} - {primeiro.get('mensagem')}")
    except requests.exceptions.Timeout:
        print("\n[4/5] ERRO: timeout ao processar.")
        return 1
    except Exception as exc:
        print(f"\n[4/5] ERRO: falha ao processar: {exc}")
        return 1

    try:
        resp = requests.get(f"{FRONTEND_URL}/api/progresso", timeout=5)
        print("\n[5/5] Proxy do Vite")
        print(f"   Status: {resp.status_code}")
        if resp.ok:
            print("   Proxy OK em /api/progresso")
        else:
            print("   AVISO: frontend respondeu, mas o proxy não retornou 200.")
    except requests.exceptions.ConnectionError:
        print("\n[5/5] AVISO: frontend de desenvolvimento não está rodando em http://localhost:8080")
    except Exception as exc:
        print(f"\n[5/5] ERRO: falha ao consultar o proxy: {exc}")
        return 1

    print("\n" + "=" * 80)
    print("SMOKE TEST CONCLUÍDO")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
