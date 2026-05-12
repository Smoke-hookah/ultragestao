"""Helpers compartilhados para filtrar alocacoes da planilha."""

from __future__ import annotations

from typing import Iterable, List, Sequence

from models.alocacao import Alocacao


def normalizar_filtros(values: Sequence[str] | None) -> List[str]:
    return [str(value).strip() for value in (values or []) if str(value).strip()]


def filtrar_alocacoes(
    alocacoes: Iterable[Alocacao],
    filtro_rotas: Sequence[str] | None = None,
    filtro_placas: Sequence[str] | None = None,
    filtro_clientes: Sequence[str] | None = None,
) -> List[Alocacao]:
    rotas = normalizar_filtros(filtro_rotas)
    placas = normalizar_filtros(filtro_placas)
    clientes = normalizar_filtros(filtro_clientes)

    if rotas and placas:
        raise ValueError("Filtro invalido: selecione rotas OU placas (nao ambos)")

    if not (rotas or placas or clientes):
        return list(alocacoes)

    rotas_set = {item.lower() for item in rotas}
    placas_set = {item.lower() for item in placas}
    clientes_set = {item.lower() for item in clientes}

    def _match(alocacao: Alocacao) -> bool:
        rota = str(getattr(alocacao, "rota", "") or "").strip().lower()
        placa = str(getattr(alocacao, "placa", "") or "").strip().lower()
        cliente = str(getattr(alocacao, "cliente", "") or "").strip().lower()
        return (rota in rotas_set) or (placa in placas_set) or (cliente in clientes_set)

    return [alocacao for alocacao in alocacoes if _match(alocacao)]
