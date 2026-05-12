from __future__ import annotations

import unittest
from unittest.mock import patch

from services.protheus_credentials import WindowsCredentialStore


class _FakeWin32CredModule:
    CRED_TYPE_GENERIC = 1
    CRED_PERSIST_LOCAL_MACHINE = 2

    def __init__(self) -> None:
        self.saved = {}

    def CredWrite(self, cred, _flags):
        self.saved[cred["TargetName"]] = {
            "UserName": cred["UserName"],
            "CredentialBlob": str(cred["CredentialBlob"]).encode("utf-16-le"),
        }

    def CredRead(self, target_name, _cred_type, _flags):
        return self.saved[target_name]

    def CredDelete(self, target_name, _cred_type, _flags):
        self.saved.pop(target_name, None)


class ProtheusCredentialStoreTests(unittest.TestCase):
    def test_save_read_and_delete_roundtrip(self) -> None:
        fake_module = _FakeWin32CredModule()
        store = WindowsCredentialStore("UltraDanfeXML/TesteProtheus")

        with patch.object(store, "_load_module", return_value=fake_module):
            store.save("operador", "segredo")
            loaded = store.read()
            self.assertEqual(loaded, {"username": "operador", "password": "segredo"})
            self.assertTrue(store.has())
            store.delete()
            self.assertFalse(store.has())


if __name__ == "__main__":
    unittest.main()
