import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from web_server import create_app

class RenderOriginTests(unittest.TestCase):
    def test_https_origin_behind_http_proxy(self):
        origin = "https://ai-agent-test-project.onrender.com"
        with patch.dict(os.environ, {"RENDER_EXTERNAL_URL": origin, "ALLOWED_ORIGINS":"", "BACKEND_ACCESS_TOKEN":"t"*48}), tempfile.TemporaryDirectory() as temp:
            client = create_app(temp).test_client()
            headers = {"Origin": origin}
            with client.get("/", headers=headers) as response:
                self.assertEqual(response.status_code, 200)
                assets = re.findall(r'(?:src|href)="(/assets/[^"]+)"', response.get_data(as_text=True))
            self.assertTrue(assets)
            for asset in assets:
                with client.get(asset, headers=headers) as response:
                    self.assertEqual(response.status_code, 200)
                    self.assertIn(response.mimetype, ("text/javascript", "application/javascript", "text/css"))
                    self.assertEqual(response.headers["Access-Control-Allow-Origin"], origin)
            self.assertEqual(client.get("/health", headers=headers).status_code, 401)
            self.assertEqual(client.get("/health", headers={**headers,"Authorization":"Bearer "+"t"*48}).status_code, 200)
            self.assertEqual(client.get("/health", headers={"Origin":"https://untrusted.example","Authorization":"Bearer "+"t"*48}).status_code, 403)

if __name__ == "__main__": unittest.main()
