"""Web adapter calling the unmodified functions used by the original app.py."""
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
    "openai": ("openai_multiagent", "run_agent_openai"),
    "pydantic": ("pydantic_multiagent", "run_agent_pydantic"),
    "crewai": ("crewai_multiagent", "run_agent_crewai"),
    "langgraph": ("langraph_multiagent", "run_agent_langraph"),
}

def execute(kind, work):
    work = Path(work).resolve()
    payload = json.loads((work / "request.json").read_text(encoding="utf-8"))
    if kind == "ocr":
        # Do not import app.py: its eager imports initialize every AI framework.
        original = importlib.import_module("ocr")
        return original.identify_card(str(work / "image.png"))
    if kind == "research":
        module, name = ENGINES[payload["engine"]]
        function = getattr(importlib.import_module(module), name)
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
