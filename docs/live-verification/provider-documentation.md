# Authenticated AMD provider evidence

Observed 2026-10-16 in the signed-in AMD Token Factory portal:
https://notebooks.amd.com/tokenfactory → User Manual and Models.

Only the separate documentation and model-results panels were read. The credential
panel was neither read nor captured. The portal's copy control transferred the key
directly into the Git-ignored server .env; its value was never displayed or logged.

The manual identifies Token Factory as AMD Radeon Cloud's model API catalog and
says the shared endpoints are run by AMD on AMD GPUs. This is provider provenance,
not an independently measured physical GPU identity.

Confirmed configuration:

- Base: https://developer.amd.com.cn/radeon/api/v1
- Request route: POST /chat/completions appended to that base.
- Authentication: private Bearer key, server only.
- Request model ID: Gemma-4-31B-IT, present in the live 12-model catalog.
- Documented system-message rule: one system message first, satisfied by the adapter.
- JSON-object output is supported for chat models. Strict JSON-schema output is
  documented only for MiMo-V2.6-Flash; AMD_JSON_SCHEMA remains false for Gemma.
- Existing adapter uses prompt-requested JSON and exact schema/citation validation;
  no request/prompt change or repair was needed for these observed calls.
- Experimental shared service; trial/development use, no production SLA.
- Limits are shared per key/team. The manual lists typical 30/key RPM, 20/account
  RPM and 8 concurrent requests, with the account-specific caps authoritative.
  All verification calls were sequential; no dedicated instance or purchase.

Catalog observed through the authenticated Models control (12):
DeepSeek-V4.1-Flash, DeepSeek-V4-Flash, DeepSeek-V4-Flash-Vision-Exp,
Gemma-4-31B-IT, GLM-5.3-Flash, MiMo-V2.6-Flash, MinerU2.5-Pro, MiniCPM5-2B,
MiniCPM-V-4.7-1B, MiniCPM-V-4.7-35B-A3B, Qwen3.8-27B, Qwen3.8-Flash-Next.
The manual's static table listed ten, so the live catalog was used for availability.

Public corroborating guide: https://amd-aim.github.io/radeon-cloud-docs/guides/model-apis/
It documents the same OpenAI-compatible shared route. Endpoint/model configuration
was based on the authenticated event manual, not inferred from the screenshot.

Returned model ID is recorded verbatim as self-dploy/Gemma-4-31B-IT. Request IDs,
token usage, elapsed times and exact source-backed extracted facts are preserved
in ../amd-probe.json and the workflow reports/packets. Provider usage includes cost
fields; those are provider-reported accounting metadata, not proof of a monetary
charge or controlled performance benchmark. Model internal reasoning was not saved.
