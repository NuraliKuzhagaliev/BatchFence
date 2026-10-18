import { useEffect, useRef, useState, type ReactNode } from "react";
import { Upload, Sparkles, RefreshCw, FileDown, ArrowLeft } from "lucide-react";
import { request, fileUpload, savePacket } from "./platform";
import type { Case, Document, Packet } from "./types";

type RecordData = Record<string, any>;
export function VisitorReview({ state, update, renderOriginal, leave, readOnly = false }: {
  state: Case; update: (value: Case) => void;
  renderOriginal: (doc?: Document) => ReactNode; leave: () => void; readOnly?: boolean;
}) {
  const [selected, setSelected] = useState(state.documents[0]?.id || "");
  const [records, setRecords] = useState<RecordData[]>(state.enterprise_packet?.assist || []);
  const [availability, setAvailability] = useState<RecordData>({ status: "checking provider" });
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [consent, setConsent] = useState(false);
  const [reviewed, setReviewed] = useState(false);
  const [note, setNote] = useState("");
  const input = useRef<HTMLInputElement>(null);
  const doc = state.documents.find(d => d.id === selected) || state.documents.at(-1);
  const route = `/api/cases/${state.id}`;
  async function refresh() {
    if (!readOnly) {
      setRecords(await request<RecordData[]>("GET", route + "/visitor-analysis"));
      setAvailability(await request<RecordData>("GET", "/api/visitor/status"));
    }
  }
  useEffect(() => { void refresh().catch(e => setError(String(e.message))); }, [state.id, state.revision, readOnly]);
  async function act(label: string, work: () => Promise<unknown>) {
    setBusy(label); setError("");
    try { await work(); } catch (e) { setError(e instanceof Error ? e.message : "Operation unavailable; retained originals remain available."); }
    finally { setBusy(""); }
  }
  const result = records.filter(r => r.document_ids?.includes(doc?.id)).at(-1);
  const current = result && result.snapshot_hash && !result.stale;
  return <section className="visitor-review">
    <div className="button-row">
      <button className="text-button" onClick={leave} disabled={!!busy}><ArrowLeft size={16} /> Back to workbench</button>
      <span className="pill navy">{readOnly ? "READ-ONLY PACKET" : "YOUR ISOLATED REVIEW SESSION"}</span>
    </div>
    <h2>Bring your own evidence.</h2>
    <p>Upload a supplier or quality notice, batch record or receiving evidence. Inspect the original beside genuine AMD Gemma proposals. No provider account or workspace access key is needed.</p>
    <div className="module-card">
      <strong>Provider: {availability.status}</strong>
      {availability.message && <p>{availability.message}</p>}
      {availability.checked_at && <p className="caption">Checked {new Date(availability.checked_at).toLocaleString()} · {availability.requested_model_id} · quota resets {new Date(availability.quota_reset_at).toLocaleString()}. Event access has no published end date and may be withdrawn. This reset is not an access expiry.</p>}
      <p>Source review only. Unknown lots remain unresolved against inventory. Supply reviewed quantities, lineage and allocations before any containment calculation in an authorized workspace. No hold, release or enterprise approval is available here.</p>
      <p className="caption">UTF-8 TXT or readable text PDF · 2 MB per file · PDF: up to 8 pages · bounded interpretation context (18,000 characters including source metadata). No silent truncation. Four AI attempts per session; failed attempts count. Shared rate limits apply. Storage on the free host is temporary.</p>
      {!readOnly && <>
        <input ref={input} type="file" hidden accept=".txt,.pdf,text/plain,application/pdf" onChange={e => {
          const file = e.target.files?.[0]; e.target.value = ""; if (!file) return;
          void act("Uploading and reading original", async () => {
            const next = await request<Case>("POST", route + "/documents", { ...await fileUpload(file), synthetic: false });
            update(next); setSelected(next.documents.at(-1)!.id); setReviewed(false); setConsent(false); setNote("");
          });
        }} />
        <div className="button-row">
          <button className="button primary" disabled={!!busy} onClick={() => input.current?.click()}><Upload size={16} /> Upload your document</button>
          <button className="button" disabled={!!busy} onClick={() => void act("Checking result", refresh)}><RefreshCw size={16} /> Refresh result</button>
          <button className="button" disabled={!!busy} onClick={() => void act("Exporting review packet", async () => { await savePacket(await request<Packet>("GET", route + "/export")); })}><FileDown size={16} /> Export packet</button>
        </div>
      </>}
    </div>
    {busy && <p className="visitor-feedback" role="status">{busy === "Processing with live AMD Gemma" ? "Processing · extracting identities and interpreting source evidence. No inventory action will run." : busy}…</p>}
    {error && <p className="error-message" role="alert">{error}</p>}
    {state.documents.length > 0 && <label>Uploaded original<select aria-label="Uploaded original" value={doc?.id} disabled={!!busy} onChange={e => { setSelected(e.target.value); setReviewed(false); }}>{state.documents.map(d => <option key={d.id} value={d.id}>{d.filename}</option>)}</select></label>}
    {doc && <div className="visitor-columns">
      <article className="module-card"><h3>Original evidence</h3><p className="caption">{doc.filename} · retained original · {doc.original_hash.slice(0, 16)}…</p>{renderOriginal(doc)}</article>
      <article className="module-card"><h3>AI proposals and uncertainties</h3>
        {!readOnly && <>
          <label className="check"><input type="checkbox" checked={consent} disabled={!!busy} onChange={e => setConsent(e.target.checked)} /> I may share this nonsensitive document with AMD for AI processing. It contains no personal, health, financial or confidential enterprise data.</label>
          <p className="caption">The provider documents prompt/output retention of about two days. Never upload credentials. This is a scoped document-review tool, not a general chat or provider proxy.</p>
          <button className="button primary" disabled={!!busy || !consent || result?.status === "running"} onClick={() => void act("Processing with live AMD Gemma", async () => {
            const value = await request<RecordData>("POST", route + "/visitor-analysis", { document_id: doc.id, revision: state.revision, idempotency_key: crypto.randomUUID(), external_processing_consent: consent });
            await refresh(); if (!value.status.startsWith("completed")) setError(value.error || value.status);
          })}><Sparkles size={16} /> Analyze with AMD Gemma</button>
        </>}
        {!result && <p>Uploaded · ready for analysis. No AI response has been generated yet.</p>}
        {result && <>
          <h4>{result.status}{result.stale ? " · stale after source change" : ""}</h4>
          <p>{result.error || result.authority}</p>
          {result.provenance && <p className="caption">Actual model: {result.provenance.model_id || "not returned"} · requested: {result.provenance.requested_model_id} · HTTP {result.provenance.http_status} · {result.provenance.elapsed_ms} ms · {result.provenance.at}</p>}
          {result.draft?.candidates?.map((c: RecordData, i: number) => <div className="visitor-candidate" key={i}>
            <strong>{c.value}</strong><p>{c.kind} · model proposal: {c.incident_status || c.disposition}</p>
            {c.inventory_status && <p className="assist-uncertain">Inventory: {c.inventory_status}</p>}
            {c.origin && <p>{c.origin}</p>}
            <blockquote>{c.source.quote}</blockquote><span className="caption">{c.source.block_id} · exact original passage</span>
          </div>)}
          {result.draft && <><h4>Uncertainties and missing context</h4><p>Proposed source scope: {result.draft.incident_scope}. Inventory scope: unresolved.</p><ul>{result.draft.unresolved.map((s: string, i: number) => <li key={i}>{s}</li>)}</ul>
            {!!result.draft.request_drafts.length && <><h4>Suggested evidence requests</h4><ul>{result.draft.request_drafts.map((s: string, i: number) => <li key={i}>{s}</li>)}</ul></>}
          </>}
          {result.status === "completed / review required" && !readOnly && <form onSubmit={e => { e.preventDefault(); void act("Recording original-source inspection", async () => { await request("POST", route + "/visitor-review", { proposal_id: result.id, revision: state.revision, reviewed, note }); await refresh(); }); }}>
            <label className="check"><input type="checkbox" required checked={reviewed} disabled={!!busy || !current} onChange={e => setReviewed(e.target.checked)} /> I inspected these proposals and uncertainties against the original. This does not approve incident scope or inventory action.</label>
            <label>Review note<textarea required minLength={20} maxLength={2000} value={note} disabled={!!busy} onChange={e => setNote(e.target.value)} /></label>
            <button className="button" disabled={!!busy || !current || !reviewed}>Record source inspection</button>
          </form>}
          {result.review && <p>Source inspection recorded · {result.review.at}. Inventory context remains unresolved.</p>}
          <details><summary>Retained raw response and provenance</summary><pre className="visitor-raw">{JSON.stringify({ raw_output: result.raw_output, provenance: result.provenance, failure: result.failure_evidence }, null, 2)}</pre></details>
        </>}
      </article>
    </div>}
  </section>;
}
