# API reference

FastAPI exposes the current request schemas at /openapi.json. Browser writes use a same-origin HttpOnly session cookie and JSON/Origin protection. Native requests use a main-process-only capability. All case routes enforce ownership.

|Method|Route|Purpose|
|---|---|---|
|GET|/api/health|Version, explicit mode and AMD configuration presence|
|GET|/api/cases|List this session's isolated cases|
|POST|/api/cases/demo|Create a synthetic draft|
|POST|/api/cases/import|Validate a packet and create a fresh draft without historical authority|
|GET|/api/cases/{id}|Authoritative current evidence, scope, plan, history and receipts|
|POST|/api/cases/{id}/documents|Bounded base64 TXT/CSV/text-PDF intake|
|POST|/api/cases/{id}/analyze|Selected document ID and explicit live/fixture/recorded mode|
|POST|/api/cases/{id}/reviews|Current run/revision, reviewed lot IDs and explicit scope/completeness acknowledgment|
|POST|/api/cases/{id}/revision|Add the synthetic supplier correction, invalidating approval immediately|
|POST|/api/cases/{id}/approve|Bind exact plan ID/digest|
|POST|/api/cases/{id}/apply|Exact hold actions and scoped idempotency key, checked inside transaction|
|GET|/api/cases/{id}/export|Versioned historical decision packet|

The complete result is returned by the case endpoint instead of separate scope/queue endpoints. Plan comparison, requests, orders and shipment review are derived server-side.

Core action payload:

    {"plan_id":"<current plan>","digest":"<current SHA-256>","actions":[{"type":"hold","pool_id":"FG-A"}],"idempotency_key":"<fresh UUID>"}

This abbreviated example must never be used in place of the exact server-generated action list. Omitting uncertain required stock fails with POLICY_VIOLATION. Stale evidence, inventory or approval yields a409 conflict. Unknown ownership returns404. Unsupported input and schema errors return422, oversized uploads413, and quota limits429. Live-provider failures remain recorded failures with no fallback.

Exports contain no session cookie or AMD credential. Packet hashes detect changes and do not authenticate the supplier.

## Review policy 2

Review payload adds uncertain_lot_ids, excluded_lot_ids, incident_scope_status (default unresolved), resolution_quote and note. Every candidate, including negative model proposals, must occur in exactly one reviewed group; all IDs must occur in the selected source. Bounded narrowing requires resolved scope, exact source basis and an explanation. Explicit unresolved source blocks narrowing and uncertain-lot reassignment. Omissions return UNREVIEWED_LOTS; contradictions UNRESOLVED_LOT/UNRESOLVED_SCOPE; unsupported resolution SCOPE_BASIS_REQUIRED. Failed runs return REVIEW_REQUIRED. Unresolved scope can be reviewed into a broad conservative plan. Model output is retained unchanged. Legacy approvals fail stale checks.

Packet hashes now use RFC 8785-compatible canonical JSON across Python and JavaScript, including fractional provider usage metadata. Reissued earlier exports preserve their case payloads; originals remain in docs/ambiguity-fix/pre-fix-packets.
