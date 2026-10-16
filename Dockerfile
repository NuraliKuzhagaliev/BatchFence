FROM node:22.20.0-bookworm-slim AS frontend
WORKDIR /app
COPY package*.json ./
RUN npm ci --ignore-scripts
COPY frontend ./frontend
COPY desktop/packet-shape.mjs desktop/packet-shape.d.mts ./desktop/
COPY index.html tsconfig.json vite.config.ts ./
RUN npm run build

FROM python:3.13-slim-bookworm
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home --uid 10001 batchfence
COPY backend ./backend
COPY fixtures ./fixtures
COPY --from=frontend /app/dist ./dist
RUN mkdir -p /data && chown batchfence:batchfence /data
USER batchfence
ENV DATABASE_PATH=/data/batchfence.sqlite3 PORT=8787
EXPOSE 8787
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8787/api/health',timeout=4)"
CMD ["python","-m","uvicorn","backend.app:app","--host","0.0.0.0","--port","8787"]
