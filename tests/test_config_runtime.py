import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ.setdefault("ALLOW_NO_API_KEYS", "1")

import config


class ConfigRuntimeTests(unittest.TestCase):
    def test_default_playwright_dir_prefers_internal_bundle_when_root_missing(self):
        with TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir)
            internal_dir = runtime_dir / "_internal" / "playwright-browsers"
            internal_dir.mkdir(parents=True)

            resolved = config._default_playwright_browsers_dir(runtime_dir)

            self.assertEqual(resolved, internal_dir)

    def test_default_playwright_dir_prefers_root_bundle_when_present(self):
        with TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir)
            root_dir = runtime_dir / "playwright-browsers"
            internal_dir = runtime_dir / "_internal" / "playwright-browsers"
            root_dir.mkdir(parents=True)
            internal_dir.mkdir(parents=True)

            resolved = config._default_playwright_browsers_dir(runtime_dir)

            self.assertEqual(resolved, root_dir)


if __name__ == "__main__":
    unittest.main()
