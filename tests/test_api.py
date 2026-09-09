import base64
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image
from web_server import create_app

TOKEN = 't' * 48
ORIGIN = 'https://card-lab-research.workspace-838424.chatgpt.site'

class ApiTests(unittest.TestCase):
    def setUp(self):
        os.environ['BACKEND_ACCESS_TOKEN'] = TOKEN
        os.environ['ALLOWED_ORIGINS'] = ORIGIN
        self.tmp = tempfile.TemporaryDirectory()
        def worker(kind, payload, work):
            if kind == 'ocr':
                self.assertTrue((work / 'image.png').exists())
                return {'raw_ocr': [{'text': 'TEST CARD', 'confidence': .98}], 'ocr_confidence': .98}
            return {'report': 'Test worker report for ' + payload['engine']}
        self.app = create_app(self.tmp.name, worker=worker)
        self.client = self.app.test_client()
        self.headers = {'Authorization': 'Bearer ' + TOKEN, 'Origin': ORIGIN}

    def tearDown(self):
        self.tmp.cleanup()

    def wait(self, job_id, client=None):
        client = client or self.client
        for _ in range(100):
            response = client.get('/jobs/' + job_id, headers=self.headers)
            job = response.get_json()
            if job['status'] not in ('queued', 'running'):
                return job
            time.sleep(.02)
        self.fail('Job did not finish')

    def test_authentication(self):
        self.assertEqual(self.client.get('/health').status_code, 401)
        self.assertEqual(self.client.get('/health', headers=self.headers).status_code, 200)
        self.assertEqual(self.client.get('/ready').status_code, 200)

    def test_combined_website_and_private_api(self):
        self.assertEqual(self.client.get('/').status_code, 200)
        self.assertEqual(self.client.get('/favicon.svg').status_code, 200)
        self.assertEqual(self.client.get('/health').status_code, 401)
        self.assertNotEqual(self.client.get('/.env').status_code, 200)
        self.assertNotEqual(self.client.get('/assets/../../.env').status_code, 200)
        own_origin = {**self.headers, 'Origin': 'http://localhost'}
        self.assertEqual(self.client.get('/health', headers=own_origin).status_code, 200)

    def test_origin_and_preflight(self):
        bad = {**self.headers, 'Origin': 'https://untrusted.example'}
        self.assertEqual(self.client.get('/health', headers=bad).status_code, 403)
        response = self.client.options('/jobs/ocr', headers={'Origin': ORIGIN})
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.headers['Access-Control-Allow-Origin'], ORIGIN)

    def test_ocr_and_cleanup(self):
        out = io.BytesIO()
        Image.new('RGB', (40, 70), 'white').save(out, format='PNG')
        response = self.client.post('/jobs/ocr', json={'image': base64.b64encode(out.getvalue()).decode()}, headers=self.headers)
        self.assertEqual(response.status_code, 202)
        job = self.wait(response.json['id'])
        self.assertEqual(job['status'], 'succeeded')
        self.assertEqual(job['result']['raw_ocr'][0]['text'], 'TEST CARD')
        self.assertFalse((Path(self.tmp.name) / job['id'] / 'image.png').exists())

    def test_all_engine_contracts(self):
        for engine in ['openai', 'pydantic', 'crewai', 'langgraph']:
            response = self.client.post('/jobs/research', json={'engine': engine, 'lines': [{'text': 'Label'}]}, headers=self.headers)
            self.assertEqual(response.status_code, 202)
            job = self.wait(response.json['id'])
            self.assertEqual(job['status'], 'succeeded')
            self.assertIn(engine, job['result']['report'])

    def test_invalid_inputs(self):
        for image in ['not-base64', base64.b64encode(b'not-an-image').decode()]:
            self.assertEqual(self.client.post('/jobs/ocr', json={'image': image}, headers=self.headers).status_code, 400)
        for payload in [{'engine':'unknown','lines':[{'text':'x'}]}, {'engine':'openai','lines':[]}, {'engine':'openai','lines':[{'text':'  '}]}]:
            self.assertEqual(self.client.post('/jobs/research', json=payload, headers=self.headers).status_code, 400)
        self.assertEqual(self.client.get('/jobs/not-a-job', headers=self.headers).status_code, 404)

    def test_restart_marks_interrupted_work_failed(self):
        jid = 'a' * 32
        directory = Path(self.tmp.name) / jid
        directory.mkdir()
        (directory / 'job.json').write_text(json.dumps({'id':jid,'status':'running','kind':'research'}))
        client = create_app(self.tmp.name).test_client()
        self.assertEqual(client.get('/jobs/' + jid, headers=self.headers).json['status'], 'failed')

    def test_bounded_queue(self):
        release = threading.Event()
        def worker(*_):
            release.wait(3)
            return {'report': 'done'}
        client = create_app(self.tmp.name, worker=worker).test_client()
        ids = []
        try:
            for _ in range(4):
                r = client.post('/jobs/research', json={'engine':'openai','lines':[{'text':'Card'}]}, headers=self.headers)
                self.assertEqual(r.status_code, 202)
                ids.append(r.json['id'])
            r = client.post('/jobs/research', json={'engine':'openai','lines':[{'text':'Card'}]}, headers=self.headers)
            self.assertEqual(r.status_code, 429)
        finally:
            release.set()
            for jid in ids:
                self.wait(jid, client)

if __name__ == '__main__':
    unittest.main()
