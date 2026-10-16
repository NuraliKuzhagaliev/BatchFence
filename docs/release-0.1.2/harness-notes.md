# Verification notes

The first web check stopped because the new workspace-only execution explanation added a second paragraph to the decision panel. The old test used a strict locator matching every paragraph. The locator now targets the existing decision summary explicitly; no product policy or output changed.

A screenshot readiness adjustment initially used Playwright Test expect, which is not exported by this project's Playwright library. It now waits for the actual enabled button using a locator. This failure occurred before any new inference request.
