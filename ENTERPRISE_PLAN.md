# Enterprise pilot implementation checkpoint

Protected public release: e70f4a0 / Windows v0.2.0 (immutable). Development branch: enterprise-pilot-0.3. No main push or expanded release before gates pass. No 0.2.1 work found; planned next application version 0.3.0.

## Dependency order
1. Baseline and risk/evidence register. Baseline: 65 pytest pass (2026-10-17); no uncommitted work or applicable AGENTS.md found.
2. Incremental SQLite/PostgreSQL repository, named local identities, membership/roles, append-only transactional audit, persistent sources, migration/isolated restore. Preserve legacy snapshots as anonymous historical records.
3. Guided mapped imports and typed receiving review; source-preserving bounded OCR; separate proposed/applied/pending/confirmed quantities.
4. Frozen p-chart signals and applicable approved knowledge, linked to the existing incident.
5. Shared whole-pool hold ledger, distinct recovery approval, transactional sandbox execution and reference connector/outbox.
6. Corrective-action lifecycle, frozen effectiveness criteria, sufficient/insufficient follow-up and recurrence.
7. Frozen 24-item model set, bounded live budget, domain/security/concurrency/performance and web/Windows checks; critical integrated review.
8. Coherent clean tag/archive/installer, local pilot restore, existing free Render deployment, media and published verification.

## Operating decisions
Single-organization private pilot, tested against a second organization. Local bootstrap only; no default credentials. PostgreSQL pilot and SQLite demo share versioned snapshots via a small repository adapter. Serial committing transactions favor correctness within measured bounds; no claims of unlimited throughput. External model work occurs outside write locks. Whole-pool recovery only. Reference connector is local sandbox, never real enterprise execution. Confidential data requires separate owner approval before external inference.

## Evidence and ownership
Engineering owner: Codex (agent-operated checks, not independent human). Human acceptance owner: repository owner plus a quality professional and independent participants, pending. Each gate is tracked in docs/enterprise/evidence-matrix.md. Risk register: docs/enterprise/risks.md.

## Current checkpoint
Baseline inspected; entire enterprise brief read. First implementation phase: persistence, identities, data contracts and restore tooling. Existing public 0.2.0 is unchanged.

Foundation milestone: 73 tests pass; actual PostgreSQL migration/runtime restrictions, 500/800/stale/concurrent duplicate and 11-source isolated restore pass. Private Compose build acceptance in progress. Named users are test identities; no independent human acceptance. No AMD calls/prompt changes.

Backend integration milestone: all four module server workflows are implemented with targeted synthetic checks; full client integration and release acceptance remain pending. 800→700→100 recovery checks preserve other incident holds. Frozen effectiveness plan and recurrence mechanics pass targeted tests. Raw fresh AMD evaluation not yet run.
