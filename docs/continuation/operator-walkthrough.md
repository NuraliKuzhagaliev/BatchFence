# Operator and reproducibility guide

Version0.4.0-rc.1 is an engineering preview. All supplied inventory is synthetic. The live evidence below came from real provider calls; reviews/approvals were agent-operated engineering checks. Owner performed the physical Windows dialogs. Independent quality, language and unfamiliar-operator acceptance remains pending.

## Open and operate

Web destination https://batchfence.onrender.com. Public storage is temporary: export a decision packet before restart. Windows Preview defaults to that same backend, or set BATCHFENCE_BACKEND_ORIGIN=http://127.0.0.1:8788 before launch for the existing named private pilot. The preview has a separate install identity and preserves stable0.3.0. Installer is unsigned. Open exported packets offline to inspect historical sources/handovers; actions and inference require a connected authorized backend.

Start a synthetic workspace, import evidence, inspect exact source passages, then explicitly review identities and incident completeness. Generate a proposal only after the required facts are reviewed. Check proposed versus applied quantities, approve the exact current plan and execute the sandbox adapter. Receipt retries are idempotent. Unknown ancestry/scope remains uncertain. A source revision invalidates pending authority. New assistance buttons require private backend configuration and a current finite free allowance; UNAVAILABLE is a genuine gate, never an implicit fixture fallback.

In Sources select an original and explicitly choose direct Gemma or Evolus. Review typed roles/statuses and quotes. If a raw proposal fails validation, the correction editor records an attributed, source-validated correction while retaining the failure. Correction does not approve critical facts or inventory. Requests shows computed missing facts, affected unique units, transparent rank and a saved draft; sending is disabled. Attach a response and verify actual closure criteria. Recovery shows clause-linked prerequisites and separate approval/acknowledgement. Source versions and affected references appear under Revisions. Handover selects authorized snapshot facts with an as-of timestamp and becomes stale after material changes.

For Italian/Russian evidence retain the original, request a derived English translation and have a qualified reviewer verify critical meaning against the original. Ambiguous numbers/dates and conflicting language remain open. Import/crop a bounded PNG/JPEG/WebP label, inspect original versus crop, then read it manually or explicitly request verified Gemma vision. Confirm exact spelling and the source relationship; an exact mismatch or unreadable/multiple label cannot support narrowing. Synthetic image tests do not prove real-photo robustness.

## Full actual engineering sequence

1. live/evolus-product-flow.json: actual extractor/agent workflow, first500, revised raw invented metadata rejected, explicit agent correction and separate scope approval800, two receipts, stale409.
2. live/product-flow.json and flow-*.json: direct Gemma ambiguous response retained800, computed missing-evidence request, Italian complete response and original-linked translation, explicit qualified engineering review.
3. Same flow: actual image response SUP-001 cannot be associated with document SUP-B (HTTP422), no fabricated image region.
4. Deterministic proposal700 versus applied800. Relevant source change makes an old recovery approval stale. Reassess and use a distinct simulated engineering approval to acknowledge100 sandbox recovery, leaving700 and preserving both original receipts.
5. Actual Gemma handover selection, export live/decision-packet.json. Windows offline check opens that retained packet with no external Node/Python and no actions. Separate Evolus packet live/evolus-decision-packet.json ends800, not the same case as direct Gemma.
6. live/evolus-library-result.json: actual isolated Blob membership/upload/download/hash, first caveat omission rejected, exact passage-key retest passed with full original and wrong-product abstention.

Media in submission/continuation displays stored genuine results, with explicit provenance. No fresh inference during filming. It is separate from this complete sequence and does not manufacture a continuous single case across the two actual provider flows.

## Checks (from D:\projects\BatchFence)

`npm ci --ignore-scripts`; `.venv\Scripts\python.exe -m pip install -r requirements.txt`; `npm run build`.

`.venv\Scripts\python.exe -m pytest -q --basetemp work/pytest-NEW` (171 passed). `.venv\Scripts\python.exe -m scripts.evaluate` (30 domain cases). `.venv\Scripts\python.exe -m scripts.scope_comparison_report` is offline. One-shot live scripts must not be rerun with the exhausted cap.

Browser scripts: browser-smoke.cjs, enterprise-browser.cjs, continuation-browser.cjs accept BATCHFENCE_BASE_URL. The latter also accepts BATCHFENCE_TEST_EXE and BATCHFENCE_BACKEND_ORIGIN for installed desktop. Native-dialog-check.cjs uses actual owner selections and saves native/native-dialog-results.json. desktop-smoke.cjs, desktop-offline.cjs, desktop-scale-check.cjs and desktop-pilot.cjs have exact current reports under windows/.

`docker build -t batchfence:continuation040rc1 .`. Existing container-check.py verifies eight checks. `scripts/continuation_container.py` verifies actual Pillow/translation/receipt/handover restart persistence. Reports under container/. Docker's original sandbox named-pipe denial is documented separately; host engine access worked without permission changes, resets, or data deletion.

## Human and external gates

Rotate the previously exposed portal key privately and update authorized local/provider/Render settings. Do not send keys in chat. Cloud live Gemma/Evolus remains disabled until private manifest, exact contract hashes, valid allowance and persistent budget can be configured safely. Never copy a new budget into an empty cloud DB to bypass48/48. Complete independent professional policy/source review, EN/RU/IT language review, physical-photo sampling and three unfamiliar operators. Provision real scoped users/data approval and off-device backup/restore against owner-defined RPO/RTO before any production pilot. Do not submit the event entry or execute real inventory actions.
