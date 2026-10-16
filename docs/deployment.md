# Deployment preparation

No deployment was published. The user explicitly reserved external publication for review.

Local run from D:\projects\BatchFence:

    .\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8787

The optional scripts/start.ps1 wrapper runs the same command when scripts are permitted by your existing policy:

    .\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8787

Open http://127.0.0.1:8787. The application health endpoint is /api/health. OpenAPI is /openapi.json.

On an authorized Docker host:

    docker build -t batchfence:0.1.0 .
    docker run --rm -p 8787:8787 --env-file .env -v batchfence-data:/data batchfence:0.1.0

These container commands are prepared and have not been executed successfully here because the Docker daemon was unavailable. Expose the service only through the approved hosting route. Mount persistent storage at /data; do not put SQLite on an ephemeral serverless filesystem.

Set APP_ORIGIN to the actual HTTPS web origin. Set the owner-controlled MAX_TOTAL_LIVE_RUNS and session quota before enabling live AMD. Provide credentials as server secrets. Keep INFERENCE_MODE=fixture until authentic AMD probes pass.

Before external distribution, configure the desktop fixed backend origin to the authorized HTTPS host, build a new installer, verify fresh-session web/desktop behavior and packet parity, checksum the exact binary, and expose working web/download URLs with version/signing status. Do not claim the local build's loopback backend works on another person's machine.

Verify persistence by creating a case, noting its evidence and receipt, restarting the deployed process, and reopening it in the same browser session. Local API and browser refresh persistence passed; a hosted restart has not been tested.

## Follow-up state (2026-10-16)

Local genuine AMD workflow and real Windows dialogs now pass their documented checks. Docker remains blocked by an observed startup failure: the Ingest server cannot rename AppData/Local/Docker/run/sailor-ingest.sock to sailor-ingest.sock.stale (file cannot be accessed by the system). WSL defaults to docker-desktop/version 2, but the Linux-engine pipe is absent. Container build/run is still unverified. Official troubleshooting: https://docs.docker.com/desktop/troubleshoot-and-support/troubleshoot/. No factory reset, unrelated data deletion or diagnostic upload was attempted.

The unchanged unsigned installer still targets loopback. The follow-up source archive includes the Dockerfile, pinned dependencies and evidence but excludes .env and private sessions. Publication needs explicit authorization for the actual public repository, hosting resource/budget, HTTPS origin and installer-download destination. No purchase, deployment or external submission occurred.
