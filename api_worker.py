"""Web adapter around the unmodified original app.py entrypoints."""
import importlib
import json
import os
from pathlib import Path
import sys
from dotenv import load_dotenv

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / "backend"))
# Use host environment variables, or explicitly configure a local .env path.
load_dotenv(BASE / ".env")
if os.environ.get("AI_AGENT_ENV_FILE"):
    load_dotenv(os.environ["AI_AGENT_ENV_FILE"])
ENGINES = {
    "openai": "run_agent_openai",
    "pydantic": "run_agent_pydantic",
    "crewai": "run_agent_crewai",
    "langgraph": "run_agent_langraph",
}

def execute(kind, work):
    work = Path(work).resolve()
    payload = json.loads((work / "request.json").read_text(encoding="utf-8"))
    original = importlib.import_module("app")
    if kind == "ocr":
        return original.identify_card(str(work / "image.png"))
    if kind == "research":
        function = getattr(original, ENGINES[payload["engine"]])
        return {"report": function(payload["lines"], "card")}
    raise ValueError("Unknown job type")

def main():
    kind, work = sys.argv[1], Path(sys.argv[2]).resolve()
    os.chdir(work)
    (work / "results").mkdir(exist_ok=True)
    result = execute(kind, work)
    (work / "response.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    main()
