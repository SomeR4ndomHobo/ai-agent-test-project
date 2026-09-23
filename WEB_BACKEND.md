# Card Lab combined website

This separate folder wraps unchanged copies of the original AI Agent Python files. api_worker.py calls the original OCR/research functions without importing the eager CLI. For CPU compatibility it supplies enable_mkldnn=False when PaddleOCR is constructed; models and backend source remain unchanged.

## Deploy on Koyeb or Render

Use this folder as the Docker build context and Dockerfile as the build file. The image builds frontend/ and serves its assets and API together using Python on PORT (default 8080). Use /ready for the health check. Do not use npm as the production start command.

Set BACKEND_ACCESS_TOKEN to a random secret of at least 32 characters, OPENAI_API_KEY and TAVILY_API_KEY as needed, and ALLOWED_ORIGINS to your exact HTTPS website origin. Render's RENDER_EXTERNAL_URL is also accepted automatically. Keep secrets out of your repository. Enter the same access token in the website's Unlock dialog.

OCR may exceed 512 MB; disabling oneDNN fixes an inference compatibility path, not a memory limit. Full Linux Docker inference has not been verified locally. For persistent jobs, mount writable storage at /data owned by UID 10001; without it jobs disappear on container replacement.

## Local use

Install requirements.txt with Python 3.11. Copy backend.env.example to .env and configure values. Run python web_server.py and open http://localhost:8080. Optional AI_AGENT_ENV_FILE can reference your original local .env without copying it. Rebuild frontend with npm ci and npm run build from frontend/.

## Diagnostics and checks

Hosting Logs contain CARD_LAB_WORKER_FAILURE with a bounded, credential-redacted traceback. Private worker.log files stay in each job directory. Review logs before sharing them. Run python -m unittest discover -s tests -v. Tests mock expensive engines; they do not validate live OCR or paid provider calls.

The deleted deployment files were reconstructed from the earlier API backup and the latest fixes. Original AI Agent sources were copied without modification.

## Smaller dependency installation

The frontend installs only packages used by the active page and its Select/Tabs components. Unused component templates remain on disk but are outside the active TypeScript entrypoints. Their dependencies must be added if those templates are used later. The shadcn stylesheet is vendored with its license so builds do not need the UI-generator CLI. Pydantic uses pydantic-ai-slim[openai], retaining the existing OpenAI Responses backend. All four research engines remain installed. PaddleOCR and CrewAI still have substantial transitive dependencies.
