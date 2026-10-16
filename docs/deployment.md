# Deployment preparation — 0.1.1

No external deployment, upload or publication occurred. The local build is ready for demonstration; public-release gates remain.

From D:\projects\BatchFence:

    .\.venv\Scripts\python.exe -m pip install --cache-dir .cache/pip -r requirements.txt
    npm run build
    .\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8787

Open http://127.0.0.1:8787. Health /api/health, schema /openapi.json. Private .env is configured; never print or distribute it. Current local AMD model is explicitly selected MiMo-V2.6-Flash. Set server credentials privately on any approved host and bound session/global quotas.

Prepared commands for a working authorized Docker host:

    docker build -t batchfence:0.1.1 .
    docker run --rm -p 8787:8787 --env-file .env -e DATABASE_PATH=/data/batchfence.sqlite3 -v batchfence-data:/data batchfence:0.1.1

These have not passed here. Exact failing diagnostic: C:\Users\nural\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe info, exit 1, absent //./pipe/dockerDesktopLinuxEngine. The backend log at 2026-10-16T08:17:43Z identifies com.docker.backend.exe cancelling startup while renaming %LOCALAPPDATA%/Docker/run/sailor-ingest.sock to .stale.

Read-only directory metadata identifies an AF_UNIX reparse entry (0x80000023). Direct ACL/reparse queries return ERROR_CANT_ACCESS_FILE 1920, not access-denied 5. Parent ACL already grants current user/SYSTEM/Administrators full control. afunix driver is running. No Docker processes were running at inspection; no current live socket owner was proven. Full sanitized command/log/process evidence: ambiguity-fix/docker-diagnostic.json.

The smallest external action is supported Docker/Windows repair of this specific socket/reparse access failure, followed by a passing docker info. Use [Docker troubleshooting](https://docs.docker.com/desktop/troubleshoot-and-support/troubleshoot/) and [Microsoft reparse-point documentation](https://learn.microsoft.com/en-us/windows/win32/fileio/reparse-points). No blanket ACL changes, socket deletion, factory reset, WSL unregister/shutdown, diagnostic upload or container/volume deletion was attempted. Do not assume a permission change fixes error 1920.

After repair, build/run the prepared container, exercise the full synthetic workflow, restart the container without removing its volume and verify the receipt and stock persist. Mount /data on persistent storage; do not use ephemeral serverless SQLite. Local process restart already passed; that does not prove container/hosted persistence.

Publication needs an explicit approved public repository, hosting resource/budget, HTTPS origin and download destination. Configure APP_ORIGIN and BATCHFENCE_BACKEND_ORIGIN, keep secrets server-side, rebuild the installer, and verify fresh-session web/desktop behavior and exact download checksums. The current installer targets loopback. Review signing/distribution status and event eligibility before submission. No purchase or new paid service is authorized.

The explicit DATABASE_PATH override prevents the local .env work/ path from overriding the image persistent-storage default. This command was inspected, not successfully container-tested.
