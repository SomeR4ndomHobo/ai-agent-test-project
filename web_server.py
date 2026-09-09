"""Card Lab single-owner API. Run one server process; mount DATA_DIR persistently."""
import base64
import binascii
import hmac
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from PIL import Image, UnidentifiedImageError

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / ".env")
Image.MAX_IMAGE_PIXELS = 25_000_000
ENGINES = {"openai", "pydantic", "crewai", "langgraph"}
MAX_IMAGE = 10 * 1024 * 1024
MAX_REQUEST = 14 * 1024 * 1024
MAX_JOBS = 4

def create_app(data_dir=None, worker=None):
    token = os.environ.get("BACKEND_ACCESS_TOKEN", "")
    if len(token) < 32:
        raise RuntimeError("Set BACKEND_ACCESS_TOKEN to a random secret of at least 32 characters.")
    origins = {s.strip().rstrip("/") for s in os.environ.get("ALLOWED_ORIGINS", "").split(",") if s.strip()}
    if "*" in origins:
        raise RuntimeError("ALLOWED_ORIGINS must list exact website origins.")
    data = Path(data_dir or os.environ.get("DATA_DIR", BASE / "data")).resolve()
    data.mkdir(parents=True, exist_ok=True)
    app = Flask(__name__, static_folder=None)
    frontend = BASE / 'frontend' / 'dist'
    app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST
    executor = ThreadPoolExecutor(max_workers=1)
    capacity = threading.BoundedSemaphore(MAX_JOBS)
    lock = threading.RLock()
    jobs = {}
    # Recover interrupted work without resubmitting paid agent calls.
    for path in data.glob("*/job.json"):
        try:
            job = json.loads(path.read_text(encoding="utf-8"))
            if job["status"] in ("running", "queued"):
                job.update(status="failed", error="The backend restarted during this job. Start a new request.")
                path.write_text(json.dumps(job), encoding="utf-8")
            jobs[job["id"]] = json.loads(json.dumps(job))
        except (OSError, ValueError, KeyError):
            continue

    def save(job):
        with lock:
            job["updated_at"] = time.time()
            jobs[job["id"]] = json.loads(json.dumps(job))
            path = data / job["id"] / "job.json"
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(job), encoding="utf-8")
            tmp.replace(path)

    def execute(job, payload):
        workdir = data / job["id"]
        try:
            job["status"] = "running"
            save(job)
            if worker:
                result = worker(job["kind"], payload, workdir)
            else:
                (workdir / "request.json").write_text(json.dumps(payload), encoding="utf-8")
                # Each OCR request has its own CWD: the original OCR code uses fixed result paths.
                with (workdir / "worker.log").open("w", encoding="utf-8") as log:
                    completed = subprocess.run(
                        [sys.executable, str(BASE / "api_worker.py"), job["kind"], str(workdir)],
                        cwd=workdir, stdout=log, stderr=log, timeout=900,
                        env={**os.environ, "PYTHONUTF8": "1"},
                    )
                result_path = workdir / "response.json"
                if completed.returncode or not result_path.exists():
                    raise RuntimeError("The Python engine failed. Check the private worker log and configured dependencies/API keys.")
                result = json.loads(result_path.read_text(encoding="utf-8"))
            job.update(status="succeeded", result=result)
        except subprocess.TimeoutExpired:
            job.update(status="failed", error="The engine exceeded its 15-minute limit. Please retry.")
        except Exception as exc:
            app.logger.warning("Job %s failed (%s)", job["id"], type(exc).__name__)
            job.update(status="failed", error=str(exc) if isinstance(exc, RuntimeError) else "The job could not be completed. Check the backend logs.")
        finally:
            # Remove images and request inputs after processing. Keep the report and private diagnostic log.
            for name in ("image.png", "request.json", "response.json", "label_processed.jpg"):
                (workdir / name).unlink(missing_ok=True)
            for name in ("label_crop.jpg",):
                (workdir / "results" / name).unlink(missing_ok=True)
            save(job)
            capacity.release()

    @app.before_request
    def authorize():
        origin = request.headers.get("Origin")
        if origin and origin.rstrip("/") not in origins and origin.rstrip('/') != request.host_url.rstrip('/'):
            return jsonify(detail="This website origin is not allowed."), 403
        if request.method == "OPTIONS":
            return "", 204
        if request.path in ('/', '/favicon.svg', '/ready') or request.path.startswith('/assets/'):
            return None
        supplied = request.headers.get("Authorization", "")
        if not hmac.compare_digest(supplied.encode(), ("Bearer " + token).encode()):
            return jsonify(detail="Invalid backend access token."), 401

    @app.after_request
    def headers(response):
        origin = request.headers.get("Origin", "").rstrip("/")
        if origin in origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.errorhandler(413)
    def too_large(_):
        return jsonify(detail="The image exceeds the 10 MB limit."), 413

    @app.get("/ready")
    def ready():
        return jsonify(status="ready")

    @app.get('/')
    def website():
        if not (frontend / 'index.html').is_file():
            return jsonify(detail='Build the frontend first: cd frontend && npm run build'), 503
        return send_from_directory(frontend, 'index.html')

    @app.get('/assets/<path:filename>')
    def website_asset(filename):
        return send_from_directory(frontend / 'assets', filename)

    @app.get('/favicon.svg')
    def favicon():
        return send_from_directory(frontend, 'favicon.svg')

    @app.get("/health")
    def health():
        return jsonify(status="ready", engines=sorted(ENGINES))

    @app.post("/jobs/<kind>")
    def submit(kind):
        if kind not in ("ocr", "research"):
            return jsonify(detail="Unknown job type."), 404
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(detail="Expected a JSON object."), 400
        image_bytes = None
        if kind == "ocr":
            value = payload.get("image")
            if not isinstance(value, str):
                return jsonify(detail="Provide an image encoded as base64."), 400
            try:
                image_bytes = base64.b64decode(value, validate=True)
                if len(image_bytes) > MAX_IMAGE:
                    return jsonify(detail="Choose an image smaller than 10 MB."), 413
                with Image.open(io.BytesIO(image_bytes)) as image:
                    if image.format not in ("JPEG", "PNG", "WEBP"):
                        raise ValueError()
                    if image.width * image.height > 25_000_000:
                        raise ValueError()
                    image.verify()
                with Image.open(io.BytesIO(image_bytes)) as image:
                    image = image.convert("RGB")
                    output = io.BytesIO()
                    image.save(output, format="PNG")
                    image_bytes = output.getvalue()
            except (ValueError, binascii.Error, UnidentifiedImageError, OSError, Image.DecompressionBombError):
                return jsonify(detail="Provide a valid JPG, PNG, or WebP image under 25 megapixels."), 400
            payload = {}
        else:
            if payload.get("engine") not in ENGINES:
                return jsonify(detail="Choose OpenAI, Pydantic, CrewAI, or LangGraph."), 400
            lines = payload.get("lines")
            if not isinstance(lines, list) or not 1 <= len(lines) <= 100:
                return jsonify(detail="Provide 1–100 label lines."), 400
            if any(not isinstance(line, dict) or not isinstance(line.get("text"), str) or len(line["text"]) > 1000 for line in lines):
                return jsonify(detail="Invalid label text."), 400
            clean = [{"text": line["text"].strip(), "confidence": None} for line in lines if line["text"].strip()]
            if not clean or sum(len(line["text"]) for line in clean) > 12000:
                return jsonify(detail="Provide between 1 and 12,000 characters of label text."), 400
            payload = {"engine": payload["engine"], "lines": clean}
        if not capacity.acquire(blocking=False):
            return jsonify(detail="The research queue is full. Try again after a job finishes."), 429
        job = {"id": uuid.uuid4().hex, "kind": kind, "status": "queued", "created_at": time.time()}
        workdir = data / job["id"]
        try:
            workdir.mkdir()
            if image_bytes:
                (workdir / "image.png").write_bytes(image_bytes)
            save(job)
            executor.submit(execute, job, payload)
        except Exception:
            capacity.release()
            raise
        return jsonify(id=job["id"], status="queued"), 202

    @app.get("/jobs/<job_id>")
    def get_job(job_id):
        if not re.fullmatch(r"[a-f0-9]{32}", job_id):
            return jsonify(detail="Job not found."), 404
        with lock:
            job = jobs.get(job_id)
            if not job:
                return jsonify(detail="Job not found."), 404
            return jsonify(job.copy())

    return app

if __name__ == "__main__":
    from waitress import serve
    serve(create_app(), host="0.0.0.0", port=int(os.environ.get("PORT", "8080")),
          threads=4, max_request_body_size=MAX_REQUEST)
