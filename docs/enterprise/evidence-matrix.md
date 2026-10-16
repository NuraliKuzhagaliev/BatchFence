# Enterprise evidence matrix

Status begins pending; code presence is not verification. Evidence is versioned and separated from 0.2.0 history. Owner E = engineering agent; H = human/domain owner.

| Requirement | Owner / surface | Positive acceptance | Negative acceptance | Evidence / status |
|---|---|---|---|---|
| Baseline preservation | E / branch, legacy tests | 65 prior tests; immutable release | no published tag replacement | baseline pytest: 65 passed; e70f4a0 protected |
| Persistence/migration | E / repository, migrations | SQLite to PostgreSQL hashes/counts | legacy approval not named authority | tests/test_foundations.py; pending |
| Restore | E+H / backup CLI | isolated records+sources+receipt workflow, measured age/time | corrupt/unsafe archive rejected | docs/enterprise/restore.json; pending; owner RPO/RTO unset |
| Identity/access | E+H / auth, API, desktop | named scoped membership | revoked role, other org/site, self-release | tests/test_identity.py; pending |
| Audit/concurrency/jobs | E / transactions, jobs | atomic audit, exact once, bounded jobs | stale/duplicate/cancel/restart | tests/test_foundations.py; pending |
| Mapped imports/OCR | E+H / intake | reviewed provenance, source image+text | duplicate/cycle/overflow/unknown/unconfirmed OCR | tests/test_onboarding.py; pending |
| Typed receiving | E+H / reconciliation | explicit old/new complete replacement | missing/uncertain parent not exclusion | tests/test_receiving.py; pending |
| Quality Signals | E+H / signals | reference pooled p and linked observations | drift/mix/missing/degenerate/correction | tests/test_signals.py; pending |
| Approved Knowledge | E+H / retrieval, AMD | approved applicable passages/check evidence | malicious/expired/conflict/cross-org | tests/test_knowledge.py; pending |
| Controlled Recovery | E+H / ledger,outbox | 800 applied/700 proposed, exact 100 recovery | second hold/stale/self/timeout/race | tests/test_recovery.py; pending |
| Corrective Action | E+H / actions | frozen plan, follow-up, recurrence | early close/missing/confounded | tests/test_effectiveness.py; pending |
| Model quality | E+H / frozen 24 inputs | raw precision/recall/support + correction | ambiguous/adversarial no authority | evaluation/enterprise; pending; synthetic agent labels |
| Performance | E / bounded datasets | multi-case and shared-stock measurements | bounds reject atomically | docs/enterprise/performance.json; pending |
| Visual/platform | E+H / React,Electron | actual screenshots/scaling/offline packet | offline action, denied/loading states | docs/enterprise/ui; pending; native dialogs may require H |
| Security | E / threat model, tests | selected OWASP controls | traversal/SSRF/session/exhaustion/injection | docs/enterprise/security.md; pending; no certification |
| Human benefit | H / operator protocol | 3 unfamiliar participants + domain review | equivalent manual comparison and negative value | pending; no invented participants |
| Packaging/deployment | E / tag, CI, existing free Render | clean source-tag image and signed hashes | no changed old assets/paid resource | pending; 0.2.0 remains live |
