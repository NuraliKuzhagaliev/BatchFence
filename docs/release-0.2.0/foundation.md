# Foundation checkpoint

Protected baseline: 2402375 / v0.1.2. New acceptance tests were first run before implementation: six failed (missing cause types, server node annotations and scenarios). The current API/domain checkpoint passes 63 tests (one upstream Starlette deprecation warning).

Verified new checks: shared boundary cause; unresolved intermediary; conditional 500→400 and 800→700; retained applied holds; partial/inconclusive unchanged; overlap recomputation; explicit complete-replacement review; contradictory reply cannot narrow; exact SUP-C→FG-D→O-104 causal delta; scenario immutability and ownership.

One initial test mistakenly reused an already-consumed idempotency key and expected rejection. The API correctly returned the prior receipt; the test now uses a new key to test a new stale execution attempt. No execution behavior changed for that test error.

Synthetic tests only. No fresh AMD request has been made for this upgrade yet. UI, full release gates, installed application and public deployment remain pending.
