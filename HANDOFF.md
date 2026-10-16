# Current checkpoint

Project: D:\projects\BatchFence. Local web: http://127.0.0.1:8787.

The synthetic workflow works on web and the installed Windows executable: extract/review, 500→800 holds, 3→4 order review, 100-unit evidence request, stale/edited request rejection, atomic sandbox receipt, persistence and portable read-only packet. Current unsigned installer: releases/BatchFence-0.1.0-win-x64-setup.exe. Final rebuild/checksum and submission assets remain in progress.

Actual checks so far: 25 pytest checks, frozen 30-case domain evaluation, 10 browser checks, 7 installed desktop checks, isolated offline runtime without external Node/Python on PATH. Model performance is unmeasured. Native dialog results were stubbed in automated file tests; actual OS dialog selection remains open after desktop interaction/minimization interrupted UI automation.

AMD blocker: portal requires sign-in; no private endpoint, model ID, key or provider evidence in session. Set a private .env from authenticated AMD documentation, then run .\.venv\Scripts\python.exe -m scripts.probe_amd. No live AMD HTTP calls occurred.

Hosting, public repository, video and submission are not published. Docker daemon unavailable. Publication was explicitly reserved by the user. Next independent work: finish release/submission assets, verify final package, create clean checkpoint.

Run: cd D:\projects\BatchFence; .\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8787.
