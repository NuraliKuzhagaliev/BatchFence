FROM node:22.20.0-bookworm-slim AS frontend
WORKDIR /app
COPY package*.json ./
RUN npm ci --ignore-scripts
COPY frontend ./frontend
COPY fixtures/resolution ./fixtures/resolution
COPY desktop/packet-shape.mjs desktop/packet-shape.d.mts ./desktop/
COPY index.html tsconfig.json vite.config.ts ./
RUN npm run build

FROM python:3.13-slim-bookworm
WORKDIR /app
COPY requirements.txt ./
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr poppler-utils && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home --uid 10001 batchfence
COPY backend ./backend
COPY scripts ./scripts
COPY fixtures ./fixtures
COPY --from=frontend /app/dist ./dist
RUN mkdir -p /var/data && chown batchfence:batchfence /var/data
USER batchfence
ENV DATABASE_PATH=/var/data/batchfence.sqlite3 PORT=8787 PYTHONUNBUFFERED=1
EXPOSE 8787
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8787')+'/api/health',timeout=4)"
CMD ["python", "-m", "backend.serve"]
