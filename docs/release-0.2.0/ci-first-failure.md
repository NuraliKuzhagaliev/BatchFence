# First 0.2.0 Linux build failure

Run 38958781303, job 117168258946, commit 7431360. All 64 pytest tests, 30 domain cases, ordinary frontend build and publication audit passed. The Docker build failed in `RUN npm run build` in the frontend stage (Dockerfile line 8): Vite could not resolve `../fixtures/resolution/receiving-complete.txt?raw` and `receiving-inconclusive.txt?raw`. Those files existed in the repository and local build but were only copied into the Python runtime stage.

Fix: copy `fixtures/resolution` into the frontend stage before building. This does not change the installed renderer or published installer bytes. No permissions, sockets, containers or volumes were altered. This is distinct from the historical Windows Docker socket blocker.

The failed CI artifact may contain the older tracked docs/cloud/container-results.json because that file was not regenerated. It is not evidence of a successful current container test. CI now writes fresh container evidence to work/ci-evidence and uploads that path only. The next run must demonstrate the real build and named-volume restart.
