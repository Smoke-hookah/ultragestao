from __future__ import annotations

from dataclasses import dataclass
from queue import Queue
from typing import Callable, TypeVar

from utils.logger import logger
from services.api_client import ClienteAPI

T = TypeVar("T")


@dataclass(frozen=True)
class PoolStats:
    total_keys: int


class ApiClientPool:
    """Pool de clientes HTTP, 1 por Api-Key.

    Motivo:
    - requests.Session não é segura para uso concorrente.
    - Com um pool, cada thread pega um cliente exclusivo, faz a chamada e devolve.
    """

    def __init__(self, api_keys: list[str]):
        if not api_keys:
            raise ValueError("ApiClientPool requer ao menos 1 Api-Key")

        # Fila geral (pega qualquer chave)
        self._q: Queue[ClienteAPI] = Queue()
        # Filas por Api-Key (pega uma chave específica com exclusividade)
        self._q_by_key: dict[str, Queue[ClienteAPI]] = {}

        for k in api_keys:
            client = ClienteAPI(api_key=k)
            self._q.put(client)
            qk: Queue[ClienteAPI] = Queue(maxsize=1)
            qk.put(client)
            self._q_by_key[k] = qk

        self.api_keys = list(api_keys)

        self.stats = PoolStats(total_keys=len(api_keys))
        logger.info(f"ApiClientPool inicializado com {self.stats.total_keys} Api-Key(s)")

    def with_client(self, fn: Callable[[ClienteAPI], T]) -> T:
        """Executa fn com qualquer cliente disponível (qualquer Api-Key)."""
        client = self._q.get()
        try:
            return fn(client)
        finally:
            self._q.put(client)

    def with_client_info(self, fn: Callable[[ClienteAPI], T]) -> tuple[str, T]:
        """Como with_client, mas retorna também a Api-Key utilizada."""
        client = self._q.get()
        try:
            return client.api_key, fn(client)
        finally:
            self._q.put(client)

    def with_client_for_api_key(self, api_key: str, fn: Callable[[ClienteAPI], T]) -> T:
        """Executa fn com um cliente específico (Api-Key fixa).

        Se a api_key não existir no pool, cai para qualquer cliente.
        """
        qk = self._q_by_key.get(api_key)
        if qk is None:
            return self.with_client(fn)

        client = qk.get()
        try:
            return fn(client)
        finally:
            qk.put(client)
