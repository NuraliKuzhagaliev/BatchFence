# Verification observations

- First Linux container build at 7431360 failed because frontend fixture imports were not copied into its Docker stage. ebd1402 adds the exact COPY and isolates fresh CI evidence; run 38959067118 then passed the real Linux build and named-volume restart.
- The first staged review succeeded, but the helper could not serialize hostless and domain cookies. It was corrected without repeating the successful review; see live/harness-failure.md.
- First receiving extraction omitted the required supplier candidate. The real API rejected narrowing 422; inconclusive review retained 800. The clarified source and its additional raw false candidates remain recorded separately.
- A later pytest invocation omitted the established D: basetemp and failed 35 fixture setups in the sandbox temp folder; 30 tests ran. With a fresh D: work/pytest-020-final directory, all 65 passed. No permissions were changed.
- Media capture initially loaded Playwright before its existing project ffmpeg cache setting, then raced a completed review and incorrectly requested server-only causal cards from an offline packet. The capture helpers now set the cache before loading Playwright, wait on completed UI results, and use supported offline snapshots. These are harness failures, not successful recordings.
- Presentation validation initially found the artifact tool default Aptos despite a fontFamily field. Adding its explicit typeface fixed the mismatch. Local finalizer hard-link permission required the existing authorized execution escalation; no security control was weakened.
- npm audit reports eight moderate issues through the desktop build-tool chain (sprintf-js → roarr → global-agent → electron-builder tooling), no high/critical; npm audit --omit=dev reports zero. The suggested builder downgrade is outside this focused release; no force audit fix or published-binary replacement was performed. See dependency-audit.json.

- The newer offline packet contains two receipts. The older one-receipt selector correctly became ambiguous; the helper now asserts the expected receipt count. The installed executable then opened both genuine fresh-run receipts offline.
