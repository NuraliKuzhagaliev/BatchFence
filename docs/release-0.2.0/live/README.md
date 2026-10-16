# Fresh public AMD evidence, 0.2.0

Four actual sequential requests reached the existing configured AMD endpoint. Requested `MiMo-V2.6-Flash`; returned `self-dploy/MiMo-V2.6-Flash`. All four returned HTTP 200 and passed schema/exact-quote validation, with no repair or fallback. The denominator includes the unsuccessful receiving interpretation. These are synthetic records with agent-operated review, not an accuracy benchmark or independent human validation.

| Input | Raw model result | Application result after explicit review |
|---|---|---|
| notice1 | SUP-A, source-backed | 500 units, 3 orders, receipt |
| notice2 | SUP-A and SUP-C, source-backed | Old approval rejected 409; 800 units, 4 orders, second receipt |
| reply | Omitted SUP-B; only FG-C returned | Complete replacement rejected 422; explicitly inconclusive review retained 800 |
| reply2 | SUP-B and FG-C plus non-lot receipt/row identifiers | Reviewer selected SUP-B only; complete source replacement proposed 700; all 800 applied units remain held |

Observed provider latencies: 16,026; 12,791; 19,718; 32,413 ms. These four requests do not establish p95, general accuracy, model comparison or AMD speedup. The fourth source was clarified after observing the third response, and is not independent held-out evidence. No model prompt changes were made for this sequence.

Every input, raw run, before-review packet, reviewed packet, source quote, request ID, input hash, UTC timestamp, usage and error is preserved here. `review-reply-failure.json` is the actual 422. `inconclusive-packet.json` shows containment after the omission; `review-reply-preview.json` and `final-packet.json` show the reviewed change without automatic release. `causal-comparison.json` records SUP-C → FG-D (300) → O-104. `harness-failure.md` distinguishes a cookie serialization failure after successful execution from provider failures.

The safety regression replays the exact saved omission, without another provider call: `tests/test_upgrade.py::test_observed_live_receiving_omission_stays_uncertain`. Historical ambiguity failures from earlier versions remain in `docs/ambiguity-fix` and `docs/cloud`.

The supplied documents contain fictional identifiers, no private supplier data. All visible decision reviews are by Codex; no independent human task timing or usability validation is claimed. Media uses these saved results as explicitly labeled historical replay and performs zero fresh inference calls.
