# Continuation coverage map

| Requirement | Existing implementation | Missing change | Acceptance evidence to collect |
|---|---|---|---|
| Evolus/Gemma flow | provider_tasks, scoped jobs, source store, typed receiving | documented external adapters, step provenance, polling, stale result checks | contract tests, authenticated API/model execution or precise blocker |
| Next Useful Evidence | causes.evidence_queue, scenarios, request-linked uploads | persisted drafts/closure review and configurable transparent ranking | deduplication, contradictory/irrelevant/duplicate response and revision tests |
| Release Readiness | recovery.snapshot/check_current, policies, hold ledger, dual control | source-linked stage checklist without a score | unknown/stale/self-approval/concurrent-hold tests; 800/700/100 |
| Document Change Impact | immutable procedure versions, revision comparison | scoped reference graph and deduplicated re-review | several cases, future version, withdrawal, receipt preservation, races |
| Multilingual Evidence | source bytes/text, original quotes | derived translation, critical-field review and approval guard | EN/RU/IT, negation, dates, IDs, injection, no qualified-review abstention |
| Label Photo Verification | source store, OCR review, desktop import | bounded image/crop/transcript review | match/mismatch/ambiguity/multiple/unreadable/duplicates/isolation; live vision separate |
| Shift Handover | quantities, audit/history, module packets | immutable brief, references, deterministic validation and review/staleness | changes/no changes/missing owner/invented numbers/revoked access/offline |

Existing 0.3.0 evidence remains under docs/enterprise. Current result status is maintained in CONTINUATION_PLAN.md and HANDOFF.md; this initial map is not a completion claim.
