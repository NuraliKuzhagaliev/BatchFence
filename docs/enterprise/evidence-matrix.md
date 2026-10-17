# Enterprise evidence matrix

Engineering checks are agent-operated. None establishes independent human/domain validation. 0.3.0 packaging and public workflow checks passed. See release-0.3.0.md and final-release.json for the exact identity.

| Requirement | Actual evidence | Status / remaining acceptance |
|---|---|---|
| Preserved incident workflow | live/pytest-final.xml:110 tests; ../evaluation-results.json:30/30; release-core.json:12checks | Passed tested synthetic scope, no regression in500/800/stale/receipt behavior |
| SQLite/PostgreSQL persistence and migration | test_foundations.py; foundation-postgres.json; modules-postgres.json actual SQLitev1 import with exact cases/receipts | Verified local PG17.11 and SQLite; legacy authority not assigned to named users |
| Original bytes and restore | modules-postgres.json:16sources exact hashes, records/users/members restored, sessions0;225ms; test unsafe/corrupt archive | Same-device drill only, owner RPO/RTO/off-device acceptance pending |
| Identity/access | test_foundations scoped source/export/audit, selector/logout, revoked approval; modules-postgres distinct test users | Implemented and tested; real identities/SSO/MFA/domain ownership pending |
| Audit/concurrency/jobs | append-only/runtime privilege tests, rollback, duplicate concurrent apply, cancellation/interrupted lease | Verified bounded local conditions, no distributed throughput claim |
| Mapped intake/OCR | test_onboarding.py; templates; ocr/actual-ocr.json and review-behavior.json; retained actual pages | Actual Tesseract5.3.0 Linux2pages52boxes; agent page review, no independent OCR acceptance |
| Typed receiving | test_upgrade.py, test_recovery.py; release-modules.json natural structured review | Synthetic source review700proposed/800held; fresh AMD typed retests 2/2 drove reviewed exact 100 recovery (live/fresh/receiving-v2) |
| Quality Signals | test_signals_knowledge.py independent unequal-n reference; statistical-evaluation.json; release-modules.json | Frozen baseline/invalid correction/mix/insufficient bounds verified;100 synthetic trials, no factory performance claim |
| Approved Knowledge | exact/cross-scope/conflict/stale tests, model-evaluation.json retrieval-only; browser forms | Applicable approved exact passages verified synthetically; fresh AMD expected sources 4/4; knowledge pipeline 11/12; domain SOP acceptance pending |
| Controlled Recovery | test_recovery.py; modules-postgres.json named test users; browser modules | Exact100, second hold preserved, stale/self/revoked rejected, duplicate receipt safe; no enterprise inventory action |
| Reference connector | modules-postgres.json actual connection refusal, explicit retry, separate process restart and same ack | Sandbox loopback connector verified; real ERP integration not implemented/authorized |
| Corrective Action | test_effectiveness.py; browser module lifecycle and withheld synthetic follow-up | Frozen criteria, missing-data block, recurrence/reopen verified; synthetic replay not prospective causal evidence |
| New model quality | frozen24items+hash; live/preflight.json; model-evaluation.json | 24/24 routes exercised: 20 model requests, four retrieval abstentions; raw extraction 6/12 exact, knowledge 11/12 pipeline. 27 total attempts. See live/README.md |
| Performance | performance.json:500each pools/edges/allocations,15runs,median68.37ms,p95max75.98ms,1.44MB Python tracked | Microbenchmark only; above-limit rejection; no network/concurrent enterprise SLA |
| Web visual/interaction | release-core.json12checks; release-modules.json6groups; release-ui/module screenshots1366/1920/390/200%zoom | Verified local agent-operated; independent comprehension pending |
| Offline packets | test_packet_canonical.py malformed rehashed extensions; promotion strips authority | Read-only module JSON snapshots, historical quantities/receipts; installed 0.3.0 offline check passed (release-desktop/offline), originals still require source store |
| Security/dependencies | security.md; production-audit.json0; full-audit.json8moderate build-tool chain | Selected controls tested, no certification; Python follow-up audit0known; OS exhaustive review not established |
| Human benefit | operator-acceptance.md protocol | 0independent participants; no ROI, customer or savings claim |
| Windows/container/release | release-artifacts.json, release-container/, release-desktop/; previous versioned assets retained | Installed 0.3.0, public tag-archive container and branch Linux CI passed; public12core/sixmodule/fivecontrol/fourdistribution checks passed |

See release-gates.md for remaining engineering and human acceptance. Code and passing builds alone are not used as acceptance evidence. Final package/CI follow-up reports supersede the pending packaging row only when successful.
