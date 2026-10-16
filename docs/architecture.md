# Architecture

BatchFence is a finite containment workflow for a fictional decorative-housing manufacturer. React/TypeScript renders both clients. FastAPI serves the built web assets and typed JSON APIs. SQLite stores isolated cases and receipts with foreign keys, WAL and schema version 1.

## Interpretation and authority

The provider proposes affected-lot candidates with document/block/exact-quote citations. Pydantic rejects extra extraction fields, invented source references and absent lot identifiers. Human review accepts or corrects critical lot IDs and acknowledges scope completeness and supersession. Exact quotes establish source existence, not semantic correctness.

The live adapter is implemented but has not made a successful AMD HTTP request. It requires the actual documented HTTPS inference base, model ID, private API key and a provider-evidence reference. The portal address is never treated as an inference URL. The implemented interface is explicitly gated on confirmed OpenAI chat compatibility. Fixture mode is a deterministic synthetic parser. Recorded mode refuses to run without a genuine preserved recording.

CPU code traverses confirmed and possible ancestry, counts unique current terminal pools, keeps unknown ancestry uncertain, uses integer cents, validates allocation totals and rejects cycles/dangling references. The graph is an explanation surface. The backend owns every total and allowed action.

## Action integrity

Canonical SHA-256 inputs include the case ID, evidence hashes/revisions, reviewed scope, bounded-completeness state, inventory snapshot/version, lineage, allocations, policy and exact actions. Integral floats normalize to integers for portable JavaScript/Python packet hashes.

Approval binds this exact plan. Apply executes under SQLite BEGIN IMMEDIATE: read ownership and current versions, find an existing scoped idempotency key, recompute the plan, compare the complete action list, apply hold statuses, increment stock version, and write a receipt in one commit. A reused key with a different request fails. Duplicate identical requests return existing state. New evidence immediately invalidates pending approval. Evidence after execution creates a new review and never releases existing held stock.

Each anonymous browser receives a random HttpOnly SameSite=Strict session cookie. The database stores its SHA-256 owner digest. Cookies are Secure when APP_ORIGIN is HTTPS. Writes require JSON and an allowed Origin; cross-site fetch metadata is rejected. Native sessions keep their capability only in main-process memory. Case ownership is enforced on every read and mutation.

## Desktop boundary

Electron packages the same React build under batchfence://app/. Node integration is off, context isolation and renderer sandbox are on. CSP prohibits remote scripts. Main denies permissions, arbitrary windows and navigation. It validates IPC sender/frame, limits API methods/routes/body sizes and uses a configured fixed origin. HTTPS is required for remote servers; loopback HTTP supports local verification.

The preload exposes request, chooseFiles, savePacket, openPacket and a bounded request-draft clipboard write. The clipboard method validates the sender and limits text to4000 UTF-8 bytes. It never reads clipboard content. No raw IPC, shell commands or general filesystem operations are exposed. Main handles bounded bytes from explicit OS file dialogs. Credentials remain server-side. The installer includes neither Python nor model weights.

Packets hold historical evidence, reviews, scope and receipts without session tokens. Their hashes detect changed content and do not authenticate suppliers. Offline packets are read-only. Promotion creates a new draft and strips historical plan/approval/receipt authority. Reconnection refreshes current case state before enabling actions.

## Deployment

One container builds the frontend, then serves assets and API from Python on port 8787. Mount /data persistently for SQLite. APP_ORIGIN must match the final HTTPS origin. No hosted deployment was created: external publication was not authorized. Docker daemon was unavailable, so the Dockerfile is prepared and not build-verified.

Primary design references checked on 2026-10-16: [Electron security](https://www.electronjs.org/docs/latest/tutorial/security), [context isolation](https://www.electronjs.org/docs/latest/tutorial/context-isolation), [IPC](https://www.electronjs.org/docs/latest/tutorial/ipc), [FastAPI](https://fastapi.tiangolo.com/tutorial/).

## 0.1.1 safety corrections

Architecture and delivery targets are unchanged. backend/review_safety.py performs conservative source checks independently of model qualifiers. Explicit affected/unresolved/excluded dispositions and source-backed incident boundary are recorded before deterministic calculation. Unresolved incident scope disables narrowing; possible ancestry is propagated regardless of affected seed selection. Review policy version participates in exact-plan inputs. Failed-run display persists after refresh. Python canonical JSON now uses rfc8785 to match existing JavaScript packet hashing for actual AMD numeric metadata.

Final offline provenance correction: the disabled mode selector now shows the packet’s recorded model mode, with an explicit historical/no-new-inference caption. It no longer displays a default fixture selection for a live AMD packet.
