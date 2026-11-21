# BatchFence

BatchFence helps quality teams review supplier notices and trace which lots may be affected. It keeps source passages, AI proposals, reviewed facts and resulting decisions linked.

[Open BatchFence](https://batchfence.onrender.com/) · [Windows release and checksums](https://github.com/NuraliKuzhagaliev/BatchFence/releases/tag/v0.4.0-rc.6) · [Project presentation](presentations/BatchFence_Deck.pptx)

## Review your own document

1. On the public website, choose **Analyze your document** to open an isolated review session.
2. Upload a nonsensitive supplier or quality notice, batch record, or receiving document. The visitor route accepts **UTF-8 TXT** and **PDF with readable text**, up to **2 MB** and **8 PDF pages**. The source must also fit the analysis context. Scans that require OCR need a separate workflow.
3. Review the named provider and consent to processing the document text. Choose **Analyze with Gemma** when the provider status is available. Visitors use their own browser session without a workspace token or provider account.
4. Check proposed lot identities and statuses against the original passages. Record your source inspection and export the review packet.

A visitor review preserves unresolved inventory context. Inventory quantity, lineage and allocations require reviewed evidence in an authorized workspace. The public workflow cannot approve or apply a hold or release.

**Verified on the public site on 21 November 2026.** A clean browser uploaded a new fictional supplier PDF without a workspace token. Cloudflare returned HTTP 200 in 11.62 seconds using `@cf/google/gemma-4-26b-a4b-it`. All three proposed lot labels matched this notice and the app kept inventory scope unresolved. A second browser session could not read the source or results. [Live response and test evidence](docs/cloudflare-visitor/result.json) · [Example PDF](docs/cloudflare-visitor/norwick-revised-supplier-notice.pdf) · [Deployed screenshot](docs/cloudflare-visitor/verified-review.png) · [Retained first attempt](docs/cloudflare-visitor/attempt-1-incomplete.json)

## Provider and hosting availability

The Cloudflare Workers AI route requests **Gemma 4 26B A4B IT**. It checks the account's free-only subscription state and model catalog before sending source text. A successful status check confirms that preflight passed. The inference request determines whether the shared daily quota remains. The current **Workers Free** allocation is 10,000 Neurons per day and resets at **00:00 UTC**. The quota and service terms can change. BatchFence allows six analysis attempts per browser session, applies shared throttles, and reports provider or quota failures in the review. It does not fall back to fixtures or paid inference. [Cloudflare pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/) · [Cloudflare model](https://developers.cloudflare.com/workers-ai/models/gemma-4-26b-a4b-it/) · [Data use](https://developers.cloudflare.com/workers-ai/platform/data-usage/)

Render Free can sleep. Keep your originals and export packets before closing a session. Temporary server files can disappear on a restart, redeploy, or idle shutdown. [Render Free](https://render.com/docs/free)

See [deployment and verification](DEPLOYMENT.md#cloudflare-workers-ai-for-public-document-review) and [the handoff](HANDOFF.md) for the current rollout status.

## Hackathon edition and genuine AMD evidence

[Original hackathon README](README.hackathon.md) describes the edition built with **AMD TokenFactory and Evolus resources provided during the hackathon**. Its access, quota and version statements are historical. It includes the original live-inference evidence: a fresh uploaded PDF drove source-backed proposals from AMD Gemma on 18 October 2026. The saved AMD response records the model, HTTP status, request ID and measured latency. These records are independent of the later Cloudflare route. [Original AMD response](docs/judge-access/public/fresh-analysis.json) · [Original browser acceptance](docs/judge-access/public/result.json)

## Develop and deploy

See [deployment and environment variables](DEPLOYMENT.md), [.env.example](.env.example), and [the handoff](HANDOFF.md). The Windows installer remains the published hackathon release. The current Cloudflare change targets the public website.
