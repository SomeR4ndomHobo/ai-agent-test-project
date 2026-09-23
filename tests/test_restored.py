import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import web_server
import api_worker

class RestoredTests(unittest.TestCase):
    def test_public_assets_and_protected_api(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"BACKEND_ACCESS_TOKEN": "t" * 48}):
            app = web_server.create_app(temp)
            client = app.test_client()
            with client.get("/", headers={"Origin": "https://example.com"}) as response:
                self.assertEqual(response.status_code, 200)
                self.assertIn("text/html", response.content_type)
            css = next((web_server.BASE / "frontend/dist/assets").glob("*.css"))
            with client.get("/assets/" + css.name, headers={"Origin": "https://example.com"}) as response:
                self.assertEqual(response.status_code, 200)
                self.assertIn("text/css", response.content_type)
            self.assertEqual(client.get("/health").status_code, 401)
            self.assertEqual(client.get("/ready").status_code, 200)

    def test_redaction(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"TEST_API_KEY": "private-value"}):
            Path(temp, "worker.log").write_text("private-value Bearer abc123 sk-testsecret")
            text = web_server.worker_diagnostic(temp)
            for secret in ("private-value", "abc123", "sk-testsecret"):
                self.assertNotIn(secret, text)

    def test_ocr_configuration_and_restore(self):
        constructor = Mock()
        package = types.SimpleNamespace(PaddleOCR=constructor)
        def load(name):
            self.assertEqual(name, "ocr")
            return package.PaddleOCR(use_doc_unwarping=False)
        with patch.dict(sys.modules, {"paddleocr": package}), patch.object(api_worker.importlib, "import_module", side_effect=load):
            api_worker.load_website_ocr()
        constructor.assert_called_once_with(use_doc_unwarping=False, enable_mkldnn=False)
        self.assertIs(package.PaddleOCR, constructor)

    def test_restore_after_failure(self):
        constructor = Mock()
        package = types.SimpleNamespace(PaddleOCR=constructor)
        with patch.dict(sys.modules, {"paddleocr": package}), patch.object(api_worker.importlib, "import_module", side_effect=RuntimeError("failed")):
            with self.assertRaises(RuntimeError):
                api_worker.load_website_ocr()
        self.assertIs(package.PaddleOCR, constructor)
