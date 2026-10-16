# BatchFence execution

Phase 0: Windows 11 x64 build 26200; Node 22.20.0, Python 3.13.2, Git available. No existing BatchFence repository at selected location. Project lives entirely on D:.

AMD portal redirects to sign-in; AMD environment fields absent. Live gate blocked pending private endpoint/model/key and provider provenance. No fixture run will be labeled live.

- [x] Phase 0 feasibility: installer built, installed and launched on Windows 11 x64. AMD portal requires sign-in.
- [x] Phase 1: exact 500→800 / 3→4 results; 25 domain/API tests pass. Frozen 30-case domain pack passes 18 development + 12 held-out.
- [ ] Phase 2 live gate: adapter, citation validation, review and fixture mode implemented. Private AMD configuration absent; zero live HTTP calls. Four-probe script prepared.
- [x] Phase 3 fixture slices: web and installed desktop review, plan, approval, sandbox execution, receipt, queues and packet handoff verified.
- [ ] Phase 4 full gate: 10 browser checks, 7 installed checks, isolated offline runtime passed. Actual native OS dialog selection and genuine AMD remain incomplete. Screenshots captured and mobile readability fixed.
- [ ] Phase 5: optional F9/Evolus omitted while required external gates remain open.
- [ ] Phase 6: release/submission assets in progress. Publication/submission unauthorized. Docker daemon unavailable.

Run: .\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8787

Checks: npm run build; .\.venv\Scripts\python.exe -m pytest -q --basetemp work\pytest-verify; .\.venv\Scripts\python.exe -m scripts.evaluate; node scripts\browser-smoke.cjs; node scripts\desktop-smoke.cjs; node scripts\desktop-offline.cjs.
