# Public document review — rc7 candidate

Public URL: https://batchfence.onrender.com/

Status: implemented and locally checked; deployed anonymous acceptance is pending. Do not interpret this candidate record as a successful public live check.

## Judge steps

1. Open the site in a new browser session and click **Analyze your document**. No owner token or provider account is required.
2. Click **Upload your document**. Supply a nonsensitive supplier/quality notice, receiving record or batch notice as UTF-8 TXT or a readable native-text PDF. Maximum file size 2 MB; PDF 1–8 pages. Complete source context must fit the existing 18,000-character interpretation envelope including metadata and the adapter's 20 KB serialized request bound. Larger sources are rejected, never silently truncated. CSV mapping, DOCX, image-only scans and general unrelated documents are not supported by this visitor route.
3. Inspect the retained original; confirm external processing consent and click **Analyze with AMD Gemma**. Uploading and processing states are explicit. Failures never fall back to fixtures/replay.
4. Inspect source-grounded candidates, proposed dispositions, unresolved evidence, model provenance and raw output beside the original. Record original-source inspection if appropriate. Unknown lots remain unresolved against inventory; supply reviewed quantities, genealogy and allocations in an authorized workspace for any later containment calculation.
5. Export a read-only historical packet before leaving or free-host sleep/redeploy. No visitor hold, release, scope approval or enterprise action is enabled.

## Cost, access and privacy

The unchanged server-side Gemma key uses only the documented AMD shared endpoint and exact configured Gemma model. Current authenticated manual identifies all shared models as free: catalog pricing/`free=false` is generic metadata, while shared event points are nonmonetary and the provider enforces the daily cap. Every dispatch rechecks authenticated catalog and usage; failed entitlement, removed model, exhausted allowance or low margin stops before inference. No paid/dedicated route, provider proxy, purchase or key rotation.

There is **no published event-key end date** in the current manual. Daily quota reset (preflight: 18 October 2026 16:00 UTC /21:00 Qyzylorda) is not access expiry. Availability depends on actual ongoing provider access and can be withdrawn. The UI reports the latest check and quota reset. Do not promise availability through an invented deadline. This direct route needs no new Evolus indexing or platform credits; existing Evolus workflows are preserved.

Four persisted AI attempts per session, including failures; six inference starts per minute globally and two per IP; one shared concurrent inference; existing request/body/file/page/session/storage limits apply. No automatic inference retries. Only nonsensitive evidence may be uploaded; provider documents about two days of prompt/output retention. All manufacturing acceptance documents here are fictional. No independent domain/operator validation is claimed.

The historical 18/18 engineering ledger and its expiry remain unchanged. Visitor job class and quota are separate; they do not reset or reinterpret earlier attempts. Existing workspace live routes remain token-protected. Session cookies and owner-scoped source records isolate originals/results.

## Evidence and release boundaries

- [Provider metadata preflight](provider-preflight.json): genuine current catalog/usage reads, zero inference calls; reference to authenticated manual read on 18 October 2026.
- [Targeted regressions](targeted-tests.xml): 69 affected checks passed, plus production frontend build. Mocks in tests are not live provider evidence.
- Local browser: new visitor upload and unrelated-input rejection passed without inference.
- Pending: CI, deployed clean-browser fresh analysis, unrelated-input rejection and cross-session isolation; publication identities and results will be appended after actual checks.

rc6 release/tag/installer and all original failures/evidence are preserved. The new entry is web-only; the existing rc6 Windows client remains compatible with protected backend routes. CI checks the shared packaged client; no new Windows live acceptance is claimed for this web-focused change.
