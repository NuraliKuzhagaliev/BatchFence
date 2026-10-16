# BatchFence 0.2.0 release evidence

The public upgrade and unsigned Windows release are available. Runtime implementation: 7431360; Docker correction: ebd1402. Protected pre-upgrade checkpoints remain 2402375 (web) and v0.1.2. Later source changes add evidence and regression coverage only; the installer tag and binary stay immutable.

| Environment | Actual result | Evidence |
|---|---|---|
| Local Python | 65 passed, one upstream Starlette warning | pytest-results.xml |
| Frozen deterministic domain | 30 unchanged passing cases | domain-results.json |
| Local browser | 12 existing checks + 9 upgrade groups | browser-results.json; upgrade-browser-final/results.json |
| Public browser | 12 existing checks + 9 upgrade groups, no page errors | public-browser-results.json; public-upgrade/results.json |
| Public security | 5 checks: access denial before inference, session isolation, replay without authority, routes/assets and temporary storage | public-controls/public-controls.json |
| Installed Windows with local backend | 9 upgrade groups | installed-upgrade/results.json |
| Installed Windows with public backend | 7 core checks, zero page errors; 4 distribution groups include web-only download and desktop-only Open web app | installed-hosted/desktop-results.json; distribution-controls-results.json |
| Installed offline / scaling | Backend unreachable, external Python/Node absent from child PATH, packet read-only; 1.0/1.25 renderer scaling | desktop-offline-results.json; desktop-scale-results.json |
| Windows download | Full anonymous 113,774,692-byte download matches SHA-256 | installer.json; public-release.json |
| Linux CI | Real container build, dynamic port, 500/800 receipts/stale/isolation and named-volume restart passed | ci-success-excerpt.txt; run 38959067118 |
| Fresh AMD | Four real requests, no fallback/repair; one parent omission blocked; clarified response reviewed | live/summary.json; live/README.md |

The six feature statuses and exact regression names are in [claims-to-evidence](../claims-to-evidence.md). Screens cover 1366×768, 1440×900, 1920×1080, 390×844 and 200% CSS zoom with no horizontal overflow. Review and UI operation are by Codex, not independent human validation. The original 12 held-out domain cases are now known regression data, not new blind evaluation.

Receiving complete replacement accepts exact bounded syntax and all superseded row IDs. Arbitrary prose needs clarification; the observed omission and non-lot candidates remain visible. Free hosted SQLite is ephemeral. A named-volume CI restart does not establish public-host durability. Installed native-dialog automation uses stubs; physical OS open/save/reopen and second-machine acceptance remain human checks. Hardware provenance was not independently measured. No production, safety-certification or independent manufacturing validation claim.

Optional extra-model/recovery-verifier experiments are deferred. Dependency audit records eight moderate build-tool transitive issues; production npm audit is zero. See verification-observations.md for actual failures and corrections rather than only successful results. Event/media constraints are documented in event-check.md.

Current media: submission/BatchFence-demo-0.2.0.mp4 (146.72 s), BatchFence-pitch-0.2.0.pptx and cover-0.2.0.png. Checksums and provenance are beside them. New genuine AMD packet and both receipts also passed installed offline review: installed-fresh-offline/desktop-offline-results.json.
