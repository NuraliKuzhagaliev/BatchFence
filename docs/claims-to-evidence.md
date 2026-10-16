# Claims to evidence — 0.2.0

The six features were added in dependency order. Existing AMD adapter, citations, deterministic containment, exact approvals, stale rejection, transaction receipts, isolated sessions and offline packet viewer were preserved. Application code is 7431360, with Linux packaging correction ebd1402; later release-evidence commits do not change the packaged renderer.

| Feature | Status | Actual behavior | Concrete check |
|---|---|---|---|
| Cause-aware evidence queue | Implemented | Shared boundary versus FG-C receiving causes; exact source rows and deduplicated totals | [test_shared_boundary_cause_not_six_missing_receipts](../tests/test_upgrade.py) |
| Evidence Impact Planner | Implemented | Read-only 500→400 / 800→700; partial/inconclusive unchanged; joint overlap counted once | [test_readonly_complete_identity_impact](../tests/test_upgrade.py) |
| Supplier-response reconciliation | Implemented, bounded input | Exact source, explicit replacement, inconclusive/conflict retention; fresh omission rejected 422; 700 proposed with 800 held | [test_observed_live_receiving_omission_stays_uncertain](../tests/test_upgrade.py) |
| Causal revision comparison | Implemented | Immutable before/after; SUP-C adds FG-D 300 and O-104; offline supports saved snapshots only | [test_causal_revision_path_300_and_order104](../tests/test_upgrade.py) |
| Guided review and visual refinement | Implemented | Per-lot unresolved defaults, source adjacency, early genealogy, elapsed timer, responsive layouts | [public-upgrade/results.json](release-0.2.0/public-upgrade/results.json) |
| Verification panel and challenges | Implemented | Raw/reviewed evidence separated; six actual policy challenges on isolated copies | [test_executable_challenges_do_not_change_visitor_case](../tests/test_upgrade.py) |

Additional evidence: [65 regressions](release-0.2.0/pytest-results.xml), [30 frozen deterministic cases](release-0.2.0/domain-results.json), [12 public browser checks](release-0.2.0/public-browser-results.json), [9 public upgrade groups](release-0.2.0/public-upgrade/results.json), [fresh AMD raw versus reviewed outcomes](release-0.2.0/live/README.md), [Windows release](release-0.2.0/public-release.json), [Linux container restart](release-0.2.0/ci-success-excerpt.txt).

Four fresh AMD calls are not a model accuracy benchmark. An omitted parent was contained; a clarified reply still proposed receipt/row IDs as lots, and explicit review selected only the actual supplier. No independent operator validation, monetary-savings claim, worldwide novelty claim, free-host durability claim or production certification. Carrying value is inventory value, not cash benefit. No messages were sent and no external inventory system is connected. Optional Gemma and portable recomputation experiments were deferred.
