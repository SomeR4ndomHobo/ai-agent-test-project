FROM node:22-slim AS frontend
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PYTHONUTF8=1 DATA_DIR=/data PORT=8080 HOME=/home/app
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
COPY requirements*.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd --create-home --uid 10001 app && mkdir /data && chown app:app /data
COPY --chown=app:app api_worker.py web_server.py ./
COPY --chown=app:app backend/ ./backend/
COPY --from=frontend --chown=app:app /web/dist ./frontend/dist
USER app
EXPOSE 8080
CMD ["python", "web_server.py"]
