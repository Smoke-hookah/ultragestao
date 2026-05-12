from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from services.protheus_staging import ProtheusStagingStore


class ProtheusStagingStoreTests(unittest.TestCase):
    def test_manifest_roundtrip_and_expiration(self) -> None:
        with tempfile.TemporaryDirectory(prefix="protheus_stage_") as tmp:
            store = ProtheusStagingStore(Path(tmp), ttl_seconds=1)
            token, root = store.create()
            manifest = store.save_manifest(token, {"hello": "world"})

            self.assertTrue(root.exists())
            loaded = store.load_manifest(token)
            self.assertEqual(loaded["hello"], "world")
            self.assertEqual(manifest["token"], token)

            time.sleep(2.1)
            expired = store.load_manifest(token)
            self.assertIsNone(expired)
            self.assertFalse(root.exists())


if __name__ == "__main__":
    unittest.main()
