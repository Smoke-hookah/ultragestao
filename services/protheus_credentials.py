"""Credenciais do Protheus no Windows Credential Manager."""

from __future__ import annotations

import os
from typing import Dict, Optional

from utils.logger import logger


DEFAULT_CREDENTIAL_TARGET = "UltraDanfeXML/ProtheusWeb"


class WindowsCredentialStore:
    def __init__(self, target_name: str = DEFAULT_CREDENTIAL_TARGET):
        self.target_name = str(target_name or DEFAULT_CREDENTIAL_TARGET).strip()

    def _load_module(self):
        if os.name != "nt":
            raise RuntimeError("Windows Credential Manager disponivel apenas no Windows")
        try:
            import win32cred  # type: ignore

            return win32cred
        except Exception as error:
            raise RuntimeError(
                "Modulo win32cred indisponivel. Instale pywin32 para usar o login automatico do Protheus."
            ) from error

    def save(self, username: str, password: str) -> None:
        win32cred = self._load_module()
        cred = {
            "Type": win32cred.CRED_TYPE_GENERIC,
            "TargetName": self.target_name,
            "UserName": str(username or "").strip(),
            "CredentialBlob": str(password or ""),
            "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE,
        }
        win32cred.CredWrite(cred, 0)

    def read(self) -> Optional[Dict[str, str]]:
        win32cred = self._load_module()
        try:
            row = win32cred.CredRead(self.target_name, win32cred.CRED_TYPE_GENERIC, 0)
        except Exception:
            return None

        blob = row.get("CredentialBlob") or b""
        if isinstance(blob, bytes):
            password = blob.decode("utf-16-le", errors="ignore")
        else:
            password = str(blob)

        return {
            "username": str(row.get("UserName") or "").strip(),
            "password": password,
        }

    def has(self) -> bool:
        return self.read() is not None

    def delete(self) -> None:
        win32cred = self._load_module()
        try:
            win32cred.CredDelete(self.target_name, win32cred.CRED_TYPE_GENERIC, 0)
        except Exception as error:
            logger.debug(f"Nao foi possivel remover credencial {self.target_name}: {error}")


def criar_credencial_protheus_padrao() -> WindowsCredentialStore:
    return WindowsCredentialStore()
