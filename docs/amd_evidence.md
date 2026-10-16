# AMD evidence and unresolved gate

**Live gate: BLOCKED. No model has run on AMD for this implementation.**

The event portal https://notebooks.amd.com/tokenfactory showed the AMD AI Notebooks sign-in page during inspection. This session had none of AMD_API_BASE_URL, AMD_API_KEY, AMD_MODEL_ID or AMD_PROVIDER_EVIDENCE configured. docs/amd-probe.json records the preflight check: zero live HTTP requests and no fixture fallback.

The server-side adapter supports a confirmed OpenAI-compatible chat endpoint with versioned instructions, bounded source blocks, 2,400 output tokens and a 45-second request timeout. JSON-schema output is opt-in only after the actual endpoint confirms support. Invalid JSON/citations fail visibly. No repair is attempted and no other provider is silently used.

To unblock:

1. Sign in to the AMD portal yourself and inspect its authenticated inference documentation.
2. Copy .env.example to .env privately. Set the documented AMD_API_BASE_URL, AMD_MODEL_ID, AMD_API_KEY, AMD_PROVIDER_EVIDENCE, and AMD_API_STYLE=openai-chat only if that interface is confirmed. Set INFERENCE_MODE=live. Never use VITE_ variables for secrets.
3. Run .\.venv\Scripts\python.exe -m scripts.probe_amd. It makes four bounded synthetic capability probes, including ambiguity, injection content and changed identifiers.
4. Inspect actual lot/citation correctness. Run a fresh UI notice and a changed notice. Preserve sanitized request IDs, model identifiers, timings and outputs. Re-run the full workflow and evaluation with real inference before any AMD eligibility claim.

Gemma availability, model license for the selected variant, physical GPU model, serving configuration and account quotas are unknown. No Gemma/Google/Evolus integration or prize eligibility is claimed. The configured endpoint's provider provenance must be checked, not inferred from an environment variable's name.
