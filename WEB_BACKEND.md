# Card Lab — separate website project

This folder is independent of ../AI Agent. backend/ contains byte-for-byte copies of the restored original Python files. Do not change those files to customize the website. All web-specific code is in web_server.py, api_worker.py, and frontend/.

The adapter invokes the original app.py OCR and engine functions directly. Original prompts, engine logic, reports, and CLI behavior are preserved. It provides uploaded images and label text in place of terminal input, with per-job working directories to keep website outputs separate. The original project’s .env, cards, and results were not copied or changed.

## Run

Install requirements.txt with Python 3.11. Configure OPENAI_API_KEY, TAVILY_API_KEY, and a BACKEND_ACCESS_TOKEN of at least 32 random characters as environment variables or in a new .env in this folder. Optionally set AI_AGENT_ENV_FILE to the path of your original .env for local use; it is never bundled. Run python web_server.py and open http://localhost:8080. Unlock the workspace with BACKEND_ACCESS_TOKEN.

The included frontend/dist is built. To rebuild source changes, run npm ci and npm run build in frontend. The last dependency cleanup was not rebuilt because execution approval was declined.

## Render

Deploy this folder (not AI Agent) as a Docker Web Service using render.yaml or Dockerfile. Set Dockerfile Path to ./Dockerfile, keep the repository root as build context, and leave Docker Command blank. The container starts python web_server.py. Do not launch vinext, wrangler, or workerd. Set provider secrets in Render; the Blueprint generates the access token. Add a persistent disk at /data for retained reports, and sufficient memory for PaddleOCR. The full Docker image and live provider calls remain unverified.

## Checks

python -m unittest discover -s tests -v

Tests validate the website API and its adapter with controlled functions; they do not change or invoke paid AI behavior. backend/ is an exact source copy, not a refactor. Update it only by copying future originals deliberately.
