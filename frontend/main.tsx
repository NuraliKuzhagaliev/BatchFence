import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ShieldCheck,
  Network,
  Files,
  History,
  FileDown,
  Upload as UploadIcon,
  ChevronRight,
  ArrowRight,
  Check,
  AlertTriangle,
  CircleHelp,
  Search,
  X,
  LockKeyhole,
  List,
  PackageCheck,
  RotateCcw,
  ClipboardCopy,
  FolderOpen,
  ExternalLink,
} from "lucide-react";
import {
  request,
  setLiveDemoToken,
  native,
  savePacket,
  fileUpload,
  validatePacket,
  copyDraft,
} from "./platform";
import type { Case, Document, Evidence, Packet, Upload, Run } from "./types";
import { Graph, GenealogyPreview, labels } from "./Graph";
import { EvidencePlanner, RevisionComparison, VerificationPanel, Elapsed } from "./UpgradePanels";
import {PilotLogin,QuantityStrip,IntakePanel,OcrReview} from "./FoundationPanels";
import {EnterprisePanels} from './EnterprisePanels';
import {RecoveryPanel} from './RecoveryPanel';
import "./style.css";
const euro = (n: number) =>
  new Intl.NumberFormat("en-IE", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(n / 100);
const num = (n: number) => n.toLocaleString("en-GB");
function Mark() {
  return (
    <span className="brand-mark">
      <ShieldCheck size={25} />
    </span>
  );
}
function Empty({ text }: { text: string }) {
  return (
    <div className="empty-state">
      <CircleHelp size={30} />
      <p>{text}</p>
    </div>
  );
}
function SourceText({
  doc,
  evidence,
}: {
  doc?: Document;
  evidence?: Evidence | null;
}) {
  return (
    <div className="source-text">
      {doc?.blocks.map((b) => (
        <div
          key={b.id}
          className={
            "source-block " + (evidence?.block_id === b.id ? "highlight" : "")
          }
        >
          <span>{b.id}</span>
          <p>{b.text}</p>
        </div>
      ))}
    </div>
  );
}
const RELEASE_URL = "https://github.com/NuraliKuzhagaliev/BatchFence/releases/tag/v0.3.0";
const WINDOWS_DOWNLOAD = "https://github.com/NuraliKuzhagaliev/BatchFence/releases/download/v0.3.0/BatchFence-0.3.0-win-x64-setup.exe";
function PlatformLinks({ openWeb }: { openWeb: () => void }) {
  return native ? (
    <button className="button" onClick={openWeb}><ExternalLink size={16} />Open web app</button>
  ) : (
    <>
      <a className="button primary" href={WINDOWS_DOWNLOAD}><FileDown size={16} />Download for Windows</a>
      <a className="text-button" href={RELEASE_URL} target="_blank" rel="noopener noreferrer">Release notes <ExternalLink size={14} /></a>
    </>
  );
}
function App() {
  const [section,setSection]=useState('incidents');
  const [data, setData] = useState<Case | null>(null),
    [packet, setPacket] = useState<Packet | null>(null),
    [busy, setBusy] = useState(""),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [online, setOnline] = useState(true),
    [ready, setReady] = useState(false);
  const [source, setSource] = useState(""),
    [selected, setSelected] = useState(""),
    [evidence, setEvidence] = useState<Evidence | null>(null),
    [inspector, setInspector] = useState(false),
    [tab, setTab] = useState("map"),
    [table, setTable] = useState(false),
    [mobile, setMobile] = useState("map");
  const [review, setReview] = useState(false),
    [lots, setLots] = useState(""),
    [uncertainLots, setUncertainLots] = useState(""),
    [excludedLots, setExcludedLots] = useState(""),
    [corrections, setCorrections] = useState<Record<string,string>>({}),
    [scopeResolved, setScopeResolved] = useState(false),
    [resolutionQuote, setResolutionQuote] = useState(""),
    [reviewNote, setReviewNote] = useState(""),
    [checked, setChecked] = useState(false),
    [bounded, setBounded] = useState(false),
    [mode, setMode] = useState("fixture"),
    [technical, setTechnical] = useState(false);
  const [cases, setCases] = useState<
      { id: string; name: string; revision: number }[]
    >([]),
    input = useRef<HTMLInputElement>(null),
    packetInput = useRef<HTMLInputElement>(null);
  const [requiresSignIn,setRequiresSignIn]=useState(false);
  const [pilotIdentity,setPilotIdentity]=useState<string>('');
  const [liveProtected, setLiveProtected] = useState(false);
  const [replayAvailable, setReplayAvailable] = useState(false);
  const [temporaryStorage, setTemporaryStorage] = useState(false);
  const connectionWasAvailable = useRef(true);
  const state = packet?.case || data,
    plan = state?.plan,
    result = plan?.result,
    run = state?.runs.at(-1);
  const doc =
    state?.documents.find((d) => d.id === source) ||
    state?.documents.find((d) => d.filename.includes("supplier")) ||
    state?.documents[0];
  const row = result?.rows.find((r) => r.id === selected),
    inspectorDoc =
      state?.documents.find((d) => d.id === evidence?.document_id) || doc;
  const readOnly = !!packet || !online,
    canWrite = !!state && !readOnly && !busy,
    currentRun =
      run?.status === "succeeded" && run.revision === state?.revision;
  async function task(label: string, fn: () => Promise<void>) {
    setBusy(label);
    setError("");
    setNotice("");
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Operation failed");
    } finally {
      setBusy("");
    }
  }
  function accept(s: Case) {
    setData(s);
    setOnline(true);
    localStorage.setItem("bf.case", s.id);
    setCases((c) => [
      { id: s.id, name: s.name, revision: s.revision },
      ...c.filter((x) => x.id !== s.id),
    ]);
  }
  useEffect(() => {
    let active = true;
    async function boot() {
      try {
        const health = await request<{
          profile?: string;
          inference_mode: string;
          amd_configured: boolean;
          live_protected: boolean;
          public_demo: boolean;
          storage_mode: string;
          replay_available: boolean;
        }>("GET", "/api/health");
        if(health.profile==='pilot'){
          try {const me=await request<{actor:{username:string}}>('GET','/api/auth/me');if(active)setPilotIdentity(me.actor.username);}
          catch {if(active){setRequiresSignIn(true);setOnline(true);}return;}
        }
        const all = await request<typeof cases>("GET", "/api/cases");
        if (!active) return;
        setCases(all);
        setLiveProtected(health.live_protected);
        setTemporaryStorage(health.storage_mode === "ephemeral");
        setReplayAvailable(health.replay_available);
        setMode(
          health.amd_configured && health.inference_mode === "live" && !health.live_protected
            ? "live"
            : "fixture",
        );
        const id = localStorage.getItem("bf.case");
        if (id && all.some((c) => c.id === id)) {
          const c = await request<Case>("GET", "/api/cases/" + id);
          if (active) setData(c);
        }
        if(!connectionWasAvailable.current)setNotice('Backend reconnected. Current evidence and action state reloaded.');
        setOnline(true);
        connectionWasAvailable.current = true;
      } catch {
        connectionWasAvailable.current = false;
        if (active) setOnline(false);
      } finally {
        if (active) setReady(true);
      }
    }
    void boot();
    // User activity checks connectivity without keeping a free host awake.
    const focus = () => { if(document.visibilityState==='visible') void boot(); };
    const offline=()=>{connectionWasAvailable.current=false;setOnline(false);};
    window.addEventListener('focus',focus);
    window.addEventListener('online',focus);
    window.addEventListener('offline',offline);
    return () => {active=false;window.removeEventListener('focus',focus);window.removeEventListener('online',focus);window.removeEventListener('offline',offline);};
  }, []);
  useEffect(() => {
    if (state)
      setSelected((s) =>
        result?.rows.some((r) => r.id === s)
          ? s
          : result?.rows.find((r) => r.classification === "uncertain")?.id ||
            result?.rows[0]?.id ||
            "",
      );
  }, [state?.id, plan?.id]);
  async function demo() {
    await task("Loading synthetic evidence", async () => {
      const s = await request<Case>("POST", "/api/cases/demo", {});
      setPacket(null);
      accept(s);
      setSource(s.documents.find((d) => d.filename.includes("supplier"))!.id);
      setTab("map");
      setReview(false);
      setNotice(
        "Synthetic evidence loaded. Extract and review the supplier notice to calculate a plan.",
      );
    });
  }
  async function replayDemo() {
    await task("Opening historical AMD evidence", async () => {
      const p = await validatePacket(await request<Packet>("GET", "/api/replay"));
      setPacket(p); setReview(false); setSource(""); setEvidence(null); setTab("map");
      setNotice("Replay · historical live AMD response on synthetic records. Agent-operated review; no new inference or independent human validation.");
    });
  }
  async function analyze() {
    if (!state || !doc) return;
    await task(
      mode === "live"
        ? "Waiting for AMD interpretation"
        : "Reading synthetic fixture",
      async () => {
        const s = await request<Case>(
          "POST",
          "/api/cases/" + state.id + "/analyze",
          { document_id: doc.id, mode },
        );
        accept(s);
        const r = s.runs.at(-1);
        if (r?.status !== "succeeded")
          throw Error(r?.error || "Interpretation failed");
        if (doc.request_id) { setReview(false); setTab("requests"); } else beginReview(r);
        setMobile("map");
      },
    );
  }
  function beginReview(r: Run) {
    setCorrections({});
    setLots("");
    setUncertainLots([...new Set(r.output!.facts.map(f => f.lot_id))].join(", "));
    setExcludedLots("");
    setChecked(false);
    setBounded(false);
    setScopeResolved(false);
    setResolutionQuote("");
    setReviewNote("");
    setReview(true);
  }
  async function confirm() {
    if (!state || !run) return;
    await task("Calculating reviewed scope", async () => {
      accept(
        await request<Case>("POST", "/api/cases/" + state.id + "/reviews", {
          run_id: run.id,
          revision: state.revision,
          lot_ids: lots
            .split(",")
            .map((l) => l.trim())
            .filter(Boolean),
          accept_scope: checked,
          lot_corrections: corrections,
          uncertain_lot_ids: uncertainLots.split(",").map(l => l.trim()).filter(Boolean),
          excluded_lot_ids: excludedLots.split(",").map(l => l.trim()).filter(Boolean),
          incident_scope_status: scopeResolved ? "resolved" : "unresolved",
          resolution_quote: resolutionQuote,
          bounded_scope_reviewed: bounded,
          note: reviewNote,
        }),
      );
      setReview(false);
      setTab("map");
      setMobile("map");
      setNotice(
        "Reviewed scope calculated. Inspect the exact plan before approval.",
      );
    });
  }
  async function revision() {
    if (!state) return;
    await task("Adding supplier correction", async () => {
      const s = await request<Case>(
        "POST",
        "/api/cases/" + state.id + "/revision",
        {},
      );
      accept(s);
      setSource(s.documents.at(-1)!.id);
      setEvidence(null);
      setReview(false);
      setTab("timeline");
      setNotice(
        "Supplier correction invalidated the previous approval. Extract and review the new notice.",
      );
    });
  }
  async function approve() {
    if (!state || !plan) return;
    await task("Binding exact approval", async () => {
      accept(
        await request<Case>("POST", "/api/cases/" + state.id + "/approve", {
          plan_id: plan.id,
          digest: plan.digest,
        }),
      );
      setNotice("This exact plan is approved. Workspace holds can now be applied.");
    });
  }
  async function apply(test = false) {
    if (!state || !plan) return;
    await task(
      test ? "Testing uncertain-stock policy" : "Applying workspace holds",
      async () => {
        const actions = test
          ? plan.actions.filter(
              (a) =>
                result?.rows.find((r) => r.id === a.pool_id)?.classification !==
                "uncertain",
            )
          : plan.actions;
        accept(
          await request<Case>("POST", "/api/cases/" + state.id + "/apply", {
            plan_id: plan.id,
            digest: plan.digest,
            actions,
            idempotency_key: crypto.randomUUID(),
          }),
        );
        setTab("receipt");
        setNotice(
          "Workspace inventory updated. Receipt and evidence are ready to export.",
        );
      },
    );
  }
  async function stale() {
    if (!state || !plan) return;
    await task("Checking stale approval", async () => {
      await request("POST", "/api/cases/" + state.id + "/apply", {
        plan_id: plan.id,
        digest: plan.digest,
        actions: plan.actions,
        idempotency_key: crypto.randomUUID(),
      });
    });
  }
  async function uploadAll(files: Upload[]) {
    if (!state) return;
    let s = state;
    for (const f of files)
      s = await request<Case>("POST", "/api/cases/" + s.id + "/documents", {
        ...f,
        synthetic: false,
      });
    accept(s);
    setSource(s.documents.at(-1)!.id);
    setEvidence(null);
    setReview(false);
    setTab("sources");
    setNotice(
      "New evidence added. Re-extract the current notice and review. CSV replacements await review.",
    );
  }
  async function intake() {
    if (native)
      await task("Importing evidence", async () =>
        uploadAll(await native!.chooseFiles()),
      );
    else input.current?.click();
  }
  async function exportPacket() {
    if (!state) return;
    await task("Exporting decision packet", async () => {
      const p =
        packet ||
        (await request<Packet>("GET", "/api/cases/" + state.id + "/export"));
      if (await savePacket(p))
        setNotice(
          "Decision packet saved with source extracts, review history and receipts.",
        );
    });
  }
  async function openPacket() {
    if (native)
      await task("Opening offline packet", async () => {
        const p = await native!.openPacket();
        if (p) {
          setPacket(await validatePacket(p));
          setReview(false);
          setTab("map");
          setNotice(
            "Historical packet opened read-only. No approval can authorize new actions.",
          );
        }
      });
    else packetInput.current?.click();
  }
  function showEvidence(e: Evidence) {
    setEvidence(e);
    setInspector(true);
  }
  function selectStock(id: string) {
    setSelected(id);
    setEvidence(null);
    setInspector(true);
  }
  const status = packet
    ? "Historical packet · read-only"
    : state?.pending_revision
      ? "Evidence changed · approval stale"
      : plan?.status === "applied"
        ? "Holds applied"
        : plan?.status === "approved"
          ? "Exact plan approved"
          : plan
            ? "Review complete · awaiting approval"
            : "Critical scope review required";
  const diff = state?.history
    .filter((h) => h.type === "reviewed" && h.old_units != null)
    .at(-1);
  if(requiresSignIn&&!packet)return <PilotLogin onSuccess={()=>location.reload()} onPacket={openPacket}/>;
  return (
    <div className="app-shell">
      <aside className="rail">
        <a href="/" className="rail-brand" aria-label="BatchFence home">
          <Mark />
        </a>
        <div className="rail-line" />
        {[
          [List, "Overview", "overview"],
          [Network, "Signals", "signals"],
          [Files, "Incidents", "incidents"],
          [Search, "Knowledge", "knowledge"],
          [PackageCheck, "Actions", "actions"],
          [ShieldCheck, "Verification", "verification"],
        ].map(([Icon, title, key]) => {
          const I = Icon as typeof Network;
          return (
            <button
              className={"rail-item " + (section === key ? "active" : "")}
              key={String(key)}
              title={String(title)}
              onClick={() => {
                setSection(String(key));
              }}
            >
              <I size={21} />
              <span>{String(title)}</span>
            </button>
          );
        })}
        <div className="rail-bottom">
          <button
            className="rail-item"
            title="Open packet"
            onClick={openPacket}
          >
            <FolderOpen size={20} />
            <span>Packets</span>
          </button>
          <span className="avatar">N</span>
        </div>
      </aside>
      <div className="app-body">
        <header className="topbar">
          <div className="wordmark">
            BatchFence<span className="separator">/</span>
            <span className="workspace-name">Quality operations</span>
          </div>
          <div className="top-actions">
            {pilotIdentity&&<><span className="caption">{pilotIdentity}</span><button className="text-button" onClick={async()=>{await request('POST','/api/auth/logout',{});location.reload();}}>Sign out</button></>}
            {!online&&<button className="text-button" onClick={()=>location.reload()}>Retry connection</button>}
            <span className={"connection " + (!online ? "offline" : "")}>
              <i />
              {online ? "Backend connected" : "Backend offline"}
            </span>
            <button
              className="icon-button"
              aria-label="Technical details"
              onClick={() => setTechnical(!technical)}
            >
              <CircleHelp size={18} />
            </button>
          </div>
        </header>
        <nav className="module-mobile-nav" aria-label="Quality workspaces">
          {['overview','signals','incidents','knowledge','actions','verification'].map(key=><button key={key} className={section===key?'active':''} onClick={()=>setSection(key)}>{key[0].toUpperCase()+key.slice(1)}</button>)}
        </nav>
        <main>
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                QUALITY OPERATIONS <ChevronRight size={12} /> {section.toUpperCase()}
              </div>
              <h1>{state ? state.name : "Evidence to action."}</h1>
              <p>
                {state
                  ? state.incident
                  : "Contain the right stock. Keep every decision tied to its evidence."}
              </p>
            </div>
            <div className="heading-actions">
              <button className="button subtle" onClick={openPacket}>
                <FolderOpen size={16} />
                Open packet
              </button>
              {state && (
                <button
                  className="button"
                  disabled={!!busy || (!online && !packet)}
                  onClick={exportPacket}
                >
                  <FileDown size={16} />
                  Export packet
                </button>
              )}
            </div>
          </div>
          {technical && (
            <section className="technical">
              <strong>Execution provenance</strong>
              <p>
                {run?.model_id || "No model run"} · {run?.mode || mode} ·{" "}
                {run?.elapsed_ms !== undefined
                  ? run.elapsed_ms + " ms"
                  : "Latency not measured"}{" "}
                · {run?.status || "Not started"}
              </p>
              <p>
                Live AMD verification:{" "}
                {run?.mode === "live" && run.status === "succeeded"
                  ? "successful run in this case"
                  : "incomplete"}
                . Fixture mode is a synthetic deterministic parser. CPU code
                calculates quantities.{" "}
                {native
                  ? "Windows native shell with fixed-origin transport."
                  : "Web with same-origin backend."}{" "}
                Request limits apply; exhausted limits are reported before another request is made.
              </p>
            </section>
          )}
          {temporaryStorage && <div className="feedback info" role="note"><History size={17} /><span>Temporary storage. Export your decision packet: server data can be lost on sleep, restart or redeployment.</span></div>}
          {(error || notice || busy) && (
            <div
              className={
                "feedback " + (error ? "error" : busy ? "loading" : "info")
              }
              role={error ? "alert" : "status"}
            >
              {error ? (
                <AlertTriangle size={17} />
              ) : busy ? (
                <span className="loader" />
              ) : (
                <Check size={17} />
              )}
              <span>{error || (busy ? <Elapsed label={busy}/> : notice)}</span>
              {!busy && (
                <button
                  className="icon-button"
                  aria-label="Dismiss message"
                  onClick={() => {
                    setError("");
                    setNotice("");
                  }}
                >
                  <X size={16} />
                </button>
              )}
            </div>
          )}
          {state && section!=='incidents' ? <EnterprisePanels key={state.id+section} section={section} state={state} readOnly={readOnly} mode={mode} setMode={setMode} update={accept} navigate={setSection} openCase={async id=>{accept(await request<Case>('GET','/api/cases/'+id));setSection('incidents');setReview(false);setTab('map');}}/> : !state ? (
            <section className="welcome">
              <div className="welcome-copy">
                <span className="pill navy">
                  <ShieldCheck size={14} /> EVIDENCE-BACKED CONTAINMENT
                </span>
                <h2>
                  One notice.
                  <br />A defensible next step.
                </h2>
                <p>
                  Trace supplier evidence through current stock, surface missing
                  records, and approve the exact plan you reviewed.
                </p>
                <div className="welcome-buttons">
                  <button
                    className="button primary"
                    onClick={demo}
                    disabled={!!busy || !online || !ready}
                  >
                    Open example incident <ArrowRight size={17} />
                  </button>
                  <button className="button" onClick={openPacket}>
                    <FolderOpen size={16} />
                    Review a packet
                  </button>
                </div>
                {replayAvailable && <button className="text-button" onClick={replayDemo} disabled={!!busy || !online}>
                  Open recorded AMD packet <History size={15} />
                </button>}
                <p className="source-note">
                  Example records are fictional. Recorded packets preserve their original provenance.
                  {liveProtected && <><br />Live inference requires a private access key. Use synthetic records on this shared service.</>}
                </p>
              </div>
              <div className="welcome-visual">
                <div className="welcome-label">THE DECISION CHAIN</div>
                {[
                  ["01", "Read the evidence", "Inspect exact source passages"],
                  ["02", "Review the scope", "Keep uncertainty visible"],
                  [
                    "03",
                    "Approve this version",
                    "Changed evidence invalidates approval",
                  ],
                ].map(([n, t, s]) => (
                  <div className="welcome-step" key={n}>
                    <b>{n}</b>
                    <div>
                      <strong>{t}</strong>
                      <span>{s}</span>
                    </div>
                    <ChevronRight size={18} />
                  </div>
                ))}
                <div className="welcome-foot">
                  <LockKeyhole size={18} />
                  Every decision stays tied to its evidence.
                </div>
              </div>
              <div className="distribution">
                <PlatformLinks openWeb={() => void task("Opening web app", async () => { await native?.openWebApp(); })} />
              </div>
              {cases.length > 0 && (
                <div className="resume">
                  <h3>Your session cases</h3>
                  {cases.map((c) => (
                    <button
                      key={c.id}
                      className="button"
                      onClick={() =>
                        task("Restoring case", async () =>
                          accept(
                            await request<Case>("GET", "/api/cases/" + c.id),
                          ),
                        )
                      }
                    >
                      {c.name} · r{c.revision}
                    </button>
                  ))}
                </div>
              )}
            </section>
          ) : (
            <>
              <div className="case-meta">
                <code>INC-{state.id.slice(0, 6).toUpperCase()}</code>
                <span className="pill fixture">
                  {packet
                    ? "HISTORICAL PACKET"
                    : run?.mode === "live"
                      ? run.status === "succeeded"
                        ? "LIVE AMD"
                        : "LIVE REQUEST FAILED"
                      : run?.mode === "recorded"
                        ? "RECORDED REPLAY"
                        : "SYNTHETIC FIXTURE"}
                </span>
                <span>Evidence r{state.revision}</span>
                <span>Stock v{state.inventory_version}</span>
                <span className={"case-status " + (plan?.status==='applied' && !state.pending_revision ? 'status-applied' : 'status-review')}>
                  <i />
                  {status}
                </span>
              </div>
              {packet && (
                <div className="offline-banner">
                  <LockKeyhole size={20} />
                  <div>
                    <strong>
                      Offline evidence review · historical snapshot
                    </strong>
                    <p>
                      Saved {new Date(packet.exported_at).toLocaleString()}.
                      Actions disabled. Hashes detect changes; they do not
                      authenticate the supplier.
                    </p>
                  </div>
                  <button
                    className="button"
                    disabled={!online || !!busy}
                    onClick={() =>
                      task("Fetching current backend state", async () => {
                        if (data)
                          accept(
                            await request<Case>("GET", "/api/cases/" + data.id),
                          );
                        setPacket(null);
                      })
                    }
                  >
                    Return to live desk
                  </button>
                  <button
                    className="button"
                    disabled={!online || !!busy}
                    onClick={() =>
                      task("Creating a new draft", async () => {
                        accept(
                          await request<Case>(
                            "POST",
                            "/api/cases/import",
                            packet,
                          ),
                        );
                        setPacket(null);
                        setNotice(
                          "New draft created. Historical approval does not transfer.",
                        );
                      })
                    }
                  >
                    Promote to new draft
                  </button>
                </div>
              )}
              <nav className="mobile-switch" aria-label="Workbench sections">
                {["sources", "map", "decision"].map((t) => (
                  <button
                    key={t}
                    className={mobile === t ? "active" : ""}
                    onClick={() => setMobile(t)}
                  >
                    {t === "sources"
                      ? "Sources"
                      : t === "map"
                        ? "Exposure"
                        : "Decision"}
                  </button>
                ))}
              </nav>
              <div className={"workbench mobile-" + mobile}>
                <aside className="source-panel panel">
                  <div className="panel-heading">
                    <h2>
                      <Files size={17} />
                      Evidence
                    </h2>
                    <span className="small-count">
                      {state.documents.length}
                    </span>
                  </div>
                  <div className="source-list">
                    {state.documents.map((d) => (
                      <button
                        key={d.id}
                        className={
                          "source-item " + (doc?.id === d.id ? "selected" : "")
                        }
                        onClick={() => {
                          setSource(d.id);
                          setEvidence(null);
                          setReview(false);
                        }}
                      >
                        <span className="file-icon">
                          {d.media_type === "text/csv"
                            ? "CSV"
                            : d.media_type === "application/pdf"
                              ? "PDF"
                              : "TXT"}
                        </span>
                        <span>
                          <strong title={d.filename}>
                            {d.filename.replaceAll("_", " ")}
                          </strong>
                          <small>
                            {d.synthetic ? "Synthetic" : "Uploaded"} · r
                            {d.revision}
                          </small>
                        </span>
                        {doc?.id === d.id && <ChevronRight size={14} />}
                      </button>
                    ))}
                  </div>
                  <div className="intake-actions">
                    <button
                      className="button full"
                      disabled={!canWrite}
                      onClick={intake}
                    >
                      <UploadIcon size={15} />
                      Add evidence
                    </button>
                    <span className="caption">
                      TXT, CSV, text PDF · 2 MB/file
                    </span>
                  </div>
                  <div className="extract-box">
                    <div className="eyebrow">NARRATIVE INTERPRETATION</div>
                    <label className="field-label" htmlFor="inference-mode">
                      Run mode
                    </label>
                    <select
                      id="inference-mode"
                      value={packet ? run?.mode || "fixture" : mode}
                      disabled={readOnly || !!busy}
                      onChange={(e) => setMode(e.target.value)}
                    >
                      <option value="fixture">
                        Fixture · synthetic parser
                      </option>
                      <option value="live">Live · AMD endpoint</option>
                    </select>
                    {liveProtected && mode === "live" && !packet && <>
                      <label className="field-label" htmlFor="live-demo-access">Live access key</label>
                      <input id="live-demo-access" type="password" autoComplete="off" maxLength={200}
                        onChange={(e) => setLiveDemoToken(e.target.value)} disabled={!canWrite} />
                      <p className="caption">Provided privately by the workspace owner. Kept only in this page's memory.</p>
                    </>}
                    <button
                      className="button primary full"
                      disabled={!canWrite || !doc}
                      onClick={analyze}
                    >
                      <Search size={15} />
                      Extract selected notice
                    </button>
                    <p className="caption">
                      {packet
                        ? "Historical model run · no new inference."
                        : mode === "fixture"
                        ? "Synthetic walkthrough. No AI inference is claimed."
                        : "Fresh AMD request. Failures stay visible."}
                    </p>
                    {run?.status === "failed" && (
                      <div className="feedback error" role="alert">
                        <AlertTriangle size={17} />
                        <span>
                          Extraction failed: {run.error || "Invalid provider response"}.
                          No candidate facts were accepted from this run.
                        </span>
                      </div>
                    )}
                    {currentRun && !review && !packet && (
                      <button
                        className="text-button"
                        onClick={() => beginReview(run!)}
                      >
                        Review candidate facts <ArrowRight size={13} />
                      </button>
                    )}
                  </div>
                </aside>
                <section className="center-panel">
                  <div className="map-heading">
                    <div>
                      <h2>
                        {tab === "recovery" ? "Controlled recovery" : tab === "timeline"
                          ? "Evidence revision timeline"
                          : tab === "sources"
                            ? "Source records"
                            : "Exposure map"}
                      </h2>
                      <span className="caption">
                        Select stock to inspect the decision and supporting
                        evidence.
                      </span>
                    </div>
                    {tab === "map" && (
                      <button
                        className="button small"
                        onClick={() => setTable(!table)}
                      >
                        <List size={14} />
                        {table ? "Graph view" : "Lineage table"}
                      </button>
                    )}
                  </div>
                  <nav className="guided-steps" aria-label="Incident guide">
                    <button onClick={()=>setTab('sources')}>1 · Notice</button>
                    <button onClick={()=>{setTab('map');if(currentRun && !doc?.request_id && run)beginReview(run);}}>2 · Review exposure</button>
                    <button onClick={()=>setTab('requests')}>3 · Resolve a question</button>
                    <button onClick={()=>setTab('timeline')}>4 · Revision consequences</button>
                    <button onClick={()=>setTab('verify')}>5 · Verify & export</button>
                  </nav>
                  <div
                    className="tabs"
                    role="tablist"
                    aria-label="Incident views"
                  >
                    {[
                      ["map", "Exposure"],
                      ["sources", "Sources & intake"],
                      ["requests", "Evidence requests"],
                      ["orders", "Order review"],
                      ["timeline", "Revisions"],
                      ["receipt", "Receipt"],
                      ["recovery", "Recovery"],
                      ["verify", "Verification"],
                    ].map(([k, t]) => (
                      <button
                        role="tab"
                        aria-selected={tab === k}
                        className={tab === k ? "active" : ""}
                        key={k}
                        onClick={() => setTab(k)}
                      >
                        {t}
                        {k === "requests" && result ? (
                          <span>{result.requests.length}</span>
                        ) : k === "orders" && result ? (
                          <span>{result.orders.length}</span>
                        ) : null}
                      </button>
                    ))}
                  </div>
                  <QuantityStrip state={state}/>
                  {result && tab!=="recovery" && (
                    <div
                      className={
                        "comparison " +
                        (state.pending_revision ? "is-stale" : "")
                      }
                    >
                      <div>
                        <span>Blanket hold</span>
                        <strong>
                          {num(result.broad_units)} <small>units</small>
                        </strong>
                        <p>{euro(result.broad_cents)} inventory value</p>
                      </div>
                      <div className="compare-arrow">
                        <ArrowRight size={21} />
                      </div>
                      <div className="required">
                        <span>
                          {state.pending_revision
                            ? "Previous plan · stale"
                            : "Proposed hold"}
                        </span>
                        <strong>
                          {num(result.hold_units)} <small>units</small>
                        </strong>
                        <p>{euro(result.hold_cents)} inventory value</p>
                      </div>
                      <div className="excluded">
                        <span>Outside evidenced scope</span>
                        <strong>
                          {num(result.outside_units)} <small>units</small>
                        </strong>
                        <p>
                          {euro(result.excluded_cents)} · value, not savings
                        </p>
                      </div>
                    </div>
                  )}
                  {review && !packet ? (
                    <section className="review-card">
                      <span className="pill uncertainty">
                        <AlertTriangle size={13} />
                        CRITICAL FACT REVIEW
                      </span>
                      <h3>Confirm the affected supplier lots.</h3>
                      <p>
                        Model proposals start unresolved. Move each lot into one
                        reviewed group after inspecting its source. Negative proposals
                        do not establish exclusions.
                      </p>
                      {Array.from(new Set(run?.output?.facts.map(f=>f.lot_id))).map((id) => {
                        const f=run!.output!.facts.find(f=>f.lot_id===id)!;
                        const reviewedId=corrections[id]||id;
                        const disposition=lots.split(',').map(x=>x.trim()).includes(reviewedId)?'affected':excludedLots.split(',').map(x=>x.trim()).includes(reviewedId)?'excluded':'unresolved';
                        function choose(value:string,newId=reviewedId){
                          const clean=(text:string)=>text.split(',').map(x=>x.trim()).filter(x=>x&&x!==reviewedId&&x!==id&&x!==newId);
                          setLots([...clean(lots),...(value==='affected'?[newId]:[])].join(', '));
                          setUncertainLots([...clean(uncertainLots),...(value==='unresolved'?[newId]:[])].join(', '));
                          setExcludedLots([...clean(excludedLots),...(value==='excluded'?[newId]:[])].join(', '));
                        }
                        return <article className="lot-review-card" key={id}>
                          <button className="candidate" onClick={()=>showEvidence(f.evidence[0])}><code>{id}</code><span>{f.affected?'Affected candidate':'Negative proposal'}</span><small>Inspect quote <ChevronRight size={12}/></small></button>
                          <blockquote>{f.evidence[0]?.quote}</blockquote>
                          <label className="field-label" htmlFor={'disposition-'+id}>Disposition of {id}</label>
                          <select id={'disposition-'+id} value={disposition} onChange={e=>choose(e.target.value)}><option value="unresolved">Unresolved</option><option value="affected">Affected</option><option value="excluded">Explicitly excluded</option></select>
                          <details><summary>Correct source identifier</summary><p>Use an exact ID from this source. The original proposal remains in the audit trail; explain the correction below.</p><label>Source-backed identifier<input aria-label={'Correct identifier '+id} value={corrections[id]??id} onChange={e=>{setCorrections({...corrections,[id]:e.target.value});choose('unresolved',e.target.value);}}/></label></details>
                        </article>;
                      })}
                      {run?.scope_concerns?.length ? <p className="review-qualifier" role="status">
                        This notice explicitly leaves scope unresolved. Keep implicated lots uncertain.
                        Clarifying evidence is required before narrowing.
                      </p> : null}
                      <label className="field-label" htmlFor="review-scope-status">Incident scope certainty</label>
                      <select id="review-scope-status" value={scopeResolved ? "resolved" : "unresolved"}
                        onChange={e => { setScopeResolved(e.target.value === "resolved"); setBounded(false); }}>
                        <option value="unresolved">Unresolved · no narrowed exclusions</option>
                        <option value="resolved" disabled={!!run?.scope_concerns?.length}>Resolved · complete boundary reviewed</option>
                      </select>
                      {scopeResolved && <>
                        <label className="field-label" htmlFor="review-basis">Scope resolution basis · exact source quote</label>
                        <textarea id="review-basis" value={resolutionQuote} onChange={e => setResolutionQuote(e.target.value)} />
                      </>}
                      <label className="field-label" htmlFor="review-note">Review explanation · scope and exclusions</label>
                      <textarea id="review-note" value={reviewNote} onChange={e => setReviewNote(e.target.value)}
                        placeholder="Explain the source-backed boundary and any excluded lots. Leave unresolved claims uncertain." />
                      <label className="checkbox">
                        <input
                          type="checkbox"
                          checked={bounded}
                          disabled={!scopeResolved}
                          onChange={(e) => setBounded(e.target.checked)}
                        />
                        I reviewed inventory, lineage and the bounded
                        completeness manifest. Uncheck to decline narrowing.
                      </label>
                      <label className="checkbox">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={(e) => setChecked(e.target.checked)}
                        />
                        I checked lot IDs, exclusions, qualifiers and whether
                        this notice supersedes prior scope.
                      </label>
                      {run?.output?.qualifiers.map((q, i) => (
                        <p className="review-qualifier" key={i}>
                          {q}
                        </p>
                      ))}
                      {state.pending_data != null && (
                        <p className="review-qualifier">
                          CSV replacements are pending and will be validated
                          with this review.
                        </p>
                      )}
                      <button
                        className="button primary"
                        disabled={!checked || !canWrite || (scopeResolved && (resolutionQuote.trim().length < 8 || reviewNote.trim().length < 20))}
                        onClick={confirm}
                      >
                        <Check size={16} />
                        Confirm scope & calculate
                      </button>
                    </section>
                  ) : tab === "recovery" ? (
                    <RecoveryPanel key={state.id} state={state} readOnly={readOnly} update={accept}/>
                  ) : tab === "verify" ? (
                    <VerificationPanel state={state} replay={!!packet} readOnly={readOnly}/>
                  ) : tab === "timeline" ? (
                    <section className="timeline">
                      <RevisionComparison state={state} readOnly={readOnly} onEvidence={showEvidence}/>
                      {state.history.length ? (
                        state.history.map((h, i) => (
                          <div
                            className={
                              "timeline-event " +
                              (h.type === "evidence_changed" ? "changed" : "")
                            }
                            key={i}
                          >
                            <i />
                            <small>
                              {new Date(h.at).toLocaleTimeString()} · evidence r
                              {h.revision}
                            </small>
                            <h3>{h.type.replaceAll("_", " ")}</h3>
                            <p>{h.message}</p>
                            {h.type === "reviewed" && h.suggested_lots && (
                              <p>
                                Candidate lots: {h.suggested_lots.join(", ")}.
                                Accepted lots: {h.lot_ids?.join(", ")}.
                              </p>
                            )}
                            {h.lot_ids && (
                              <div className="revision-diff">
                                <code>
                                  {h.previous_lots?.join(", ") || "Unreviewed"}
                                </code>
                                <ArrowRight size={16} />
                                <code>{h.lot_ids.join(", ")}</code>
                              </div>
                            )}
                            {h.old_units != null && (
                              <div className="revision-units">
                                {h.old_units} <ArrowRight size={18} />{" "}
                                {h.new_units}{" "}
                                <small>units proposed for hold</small>
                              </div>
                            )}
                          </div>
                        ))
                      ) : (
                        <Empty text="No revisions yet. Extract and review the supplier notice." />
                      )}
                    </section>
                  ) : tab === "sources" ? (
                    <section className="source-page">
                      <h3>{doc?.filename}</h3>
                      {doc&&<OcrReview key={doc.id} state={state} doc={doc} readOnly={readOnly} onUpdate={accept}/>}
                      <SourceText doc={doc} />
                      <IntakePanel key={state.id} state={state} readOnly={readOnly} onUpdate={accept}/>
                    </section>
                  ) : tab === "requests" ? (
                    <EvidencePlanner state={state} readOnly={readOnly||!!busy} mode={mode} onUpdate={s=>{accept(s);setNotice('');setError('');}} onEvidence={showEvidence}/>
                  ) : tab === "orders" ? (
                    <section>
                      {result ? (
                        <>
                          <div className="queue-summary">
                            <PackageCheck size={22} />
                            <p>
                              <strong>
                                {result.orders.length} open orders need review
                              </strong>
                              <br />
                              Explicit allocations. Due dates are shown; no
                              delay prediction is made.
                            </p>
                          </div>
                          <div className="table-wrap">
                            <table>
                              <thead>
                                <tr>
                                  <th>Order</th>
                                  <th>Allocated stock</th>
                                  <th>Units</th>
                                  <th>Due</th>
                                  <th>State</th>
                                </tr>
                              </thead>
                              <tbody>
                                {result.orders.map((o) => (
                                  <tr key={o.order_id}>
                                    <td>
                                      <code>{o.order_id}</code>
                                    </td>
                                    <td>
                                      {o.pool_ids.map((id) => (
                                        <button
                                          key={id}
                                          className="text-button mono"
                                          onClick={() => selectStock(id)}
                                        >
                                          {id}
                                        </button>
                                      ))}
                                    </td>
                                    <td>{o.units}</td>
                                    <td>{o.due_date}</td>
                                    <td>
                                      <span className="pill uncertainty">
                                        Needs review
                                      </span>
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                          <p className="caption pad">
                            Order quantities refer to existing inventory and are
                            not added to exposure totals.
                          </p>
                          {result.shipment_reviews.length > 0 && (
                            <div className="queue-summary">
                              <AlertTriangle size={20} />
                              <p>
                                <strong>
                                  Shipped stock needs shipment review
                                </strong>
                                <br />
                                Warehouse holds cannot apply to shipped goods:{" "}
                                {result.shipment_reviews.join(", ")}.
                              </p>
                            </div>
                          )}
                        </>
                      ) : (
                        <Empty text="Review scope to identify allocated open orders." />
                      )}
                    </section>
                  ) : tab === "receipt" ? (
                    <section className="receipt-view">
                      {state.receipts.length ? (
                        state.receipts.map((r) => (
                          <article
                            className="receipt-card"
                            key={r.transaction_id}
                          >
                            <span className="receipt-check">
                              <Check size={25} />
                            </span>
                            <span className="eyebrow">
                              EXECUTION RECEIPT
                            </span>
                            <h3>Holds applied. Evidence preserved.</h3>
                            <p>
                              The approved transaction updated this workspace’s inventory.
                            </p>
                            <dl>
                              <dt>Transaction</dt>
                              <dd>
                                <code>{r.transaction_id}</code>
                              </dd>
                              <dt>Evidence / inventory</dt>
                              <dd>
                                r{r.evidence_revision} · v
                                {r.prior_inventory_version} → v
                                {r.current_inventory_version}
                              </dd>
                              <dt>Committed</dt>
                              <dd>{new Date(r.at).toLocaleString()}</dd>
                              <dt>Plan</dt>
                              <dd>
                                <code>{r.plan_id}</code>
                              </dd>
                            </dl>
                            <div className="receipt-changes">
                              {r.changes.map((c) => (
                                <div key={c.pool_id}>
                                  <code>{c.pool_id}</code>
                                  <span>{c.units} units</span>
                                  <span>
                                    {c.before} → {c.after}
                                  </span>
                                </div>
                              ))}
                            </div>
                            <p className="caption">
                              Changes apply to this workspace only. No external inventory system or machinery is connected, and no supplier message was sent.
                            </p>
                          </article>
                        ))
                      ) : (
                        <Empty text="A receipt is created when an approved plan updates workspace inventory." />
                      )}
                    </section>
                  ) : result ? (
                    table ? (
                      <div className="table-wrap lineage-table">
                        <table>
                          <thead>
                            <tr>
                              <th>Stock / units</th>
                              <th>Classification</th>
                              <th>Evidence path</th>
                              <th>Reason</th>
                            </tr>
                          </thead>
                          <tbody>
                            {result.rows.map((r) => (
                              <tr key={r.id}>
                                <td>
                                  <button
                                    className="text-button mono"
                                    onClick={() => selectStock(r.id)}
                                  >
                                    {r.id}
                                  </button>
                                  <small>{r.units} units</small>
                                </td>
                                <td>
                                  <span
                                    className={
                                      "table-status " + r.classification
                                    }
                                  >
                                    {labels[r.classification]}
                                  </span>
                                </td>
                                <td>
                                  <code>
                                    {r.path.join(" → ") || "Unknown ancestry"}
                                  </code>
                                </td>
                                <td>{r.reason}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <Graph
                        data={state}
                        result={result}
                        selected={selected}
                        onSelect={selectStock}
                      />
                    )
                  ) : (
                    <div><GenealogyPreview data={state}/><div className="preview-action"><button className="button primary" disabled={!canWrite} onClick={analyze}>Extract & review notice <ArrowRight size={16}/></button><p>No stock has been held. Review the evidence before approving.</p></div></div>
                  )}
                </section>
                <aside
                  className={"inspector panel " + (inspector ? "is-open" : "")}
                >
                  <div className="panel-heading">
                    <h2>
                      <Search size={16} />
                      Source inspector
                    </h2>
                    <button
                      className="icon-button inspector-close"
                      aria-label="Close inspector"
                      onClick={() => setInspector(false)}
                    >
                      <X size={16} />
                    </button>
                  </div>
                  {row && !evidence ? (
                    <>
                      <div className="inspector-stock">
                        <div className="eyebrow">CURRENT FINISHED STOCK</div>
                        <h3>
                          {row.id}
                          <span>{row.units} units</span>
                        </h3>
                        <span className={"pill " + row.classification}>
                          {labels[row.classification]}
                        </span>
                        <p>{row.reason}</p>
                        <div className="path-box">
                          {row.path.length
                            ? row.path.map((n, i) => (
                                <React.Fragment key={i}>
                                  {i > 0 && <ArrowRight size={12} />}
                                  <code>{n}</code>
                                </React.Fragment>
                              ))
                            : "Ancestry unresolved"}
                        </div>
                        <dl>
                          <dt>Carrying value</dt>
                          <dd>{euro(row.units * row.unit_cents)}</dd>
                          <dt>Inventory row</dt>
                          <dd>
                            <code>{row.row_id}</code>
                          </dd>
                          <dt>Current state</dt>
                          <dd>{state.stocks.find(stock=>stock.id===row.id)?.status??row.status}</dd>
                        </dl>
                      </div>
                      <div className="inspector-sources">
                        <div className="eyebrow">SUPPORTING EVIDENCE</div>
                        {row.evidence.map((ref, i) => (
                          <button
                            className="evidence-link"
                            key={i}
                            onClick={() => showEvidence(ref)}
                          >
                            <Files size={15} />
                            <span>
                              {
                                state.documents.find(
                                  (d) => d.id === ref.document_id,
                                )?.filename
                              }
                              <small>{ref.block_id}</small>
                            </span>
                            <ChevronRight size={14} />
                          </button>
                        ))}
                        {(row.classification === "uncertain" ||
                          row.classification === "outside") && (
                          <button
                            className="evidence-link"
                            onClick={() => {
                              const d = state.documents.find((d) =>
                                d.filename.includes(
                                  row.classification === "uncertain"
                                    ? "ambiguous"
                                    : "completeness",
                                ),
                              );
                              if (d)
                                showEvidence({
                                  document_id: d.id,
                                  block_id: d.blocks.at(-1)!.id,
                                  quote: d.blocks.at(-1)!.text,
                                });
                            }}
                          >
                            <AlertTriangle size={15} />
                            <span>
                              {row.classification === "uncertain"
                                ? "Missing receiving identity"
                                : "Bounded completeness"}
                              <small>Inspect the review assumption</small>
                            </span>
                            <ChevronRight size={14} />
                          </button>
                        )}
                      </div>
                      <div className="inspector-note">
                        <LockKeyhole size={16} />
                        <p>
                          Outside scope applies to current evidence. It does not
                          certify stock as safe.
                        </p>
                      </div>
                    </>
                  ) : (
                    <div className="source-extract">
                      <div className="eyebrow">
                        {evidence
                          ? "EXACT SOURCE PASSAGE"
                          : "SELECTED DOCUMENT"}
                      </div>
                      <h3>{inspectorDoc?.filename}</h3>
                      <SourceText doc={inspectorDoc} evidence={evidence} />
                      {evidence && (
                        <button
                          className="text-button"
                          onClick={() => setEvidence(null)}
                        >
                          Back to stock reason
                        </button>
                      )}
                    </div>
                  )}
                </aside>
              </div>
              <section
                className={
                  "decision-bar " +
                  (state.pending_revision ? "stale" : "") +
                  " mobile-decision-" +
                  mobile
                }
              >
                <div className="decision-main">
                  <span className="decision-icon">
                    {packet ? (
                      <LockKeyhole size={22} />
                    ) : state.pending_revision ? (
                      <AlertTriangle size={22} />
                    ) : (
                      <ShieldCheck size={22} />
                    )}
                  </span>
                  <div>
                    <div className="eyebrow">DECISION CONTROL</div>
                    <strong>{status}</strong>
                    <p>
                      {packet
                        ? "Historical review only. Fetch current state before action."
                        : state.pending_revision
                          ? "Changed facts require fresh review and approval. Previous actions are blocked."
                          : result
                            ? num(result.hold_units) +
                              " units proposed · including " +
                              num(result.uncertain_units) +
                              " uncertain · " +
                              state.scope.lot_ids.join(", ")
                            : "Review the notice to create the first plan."}
                    </p>
                    {!packet && <p className="execution-scope">Holds update this workspace’s inventory. No external inventory system is connected.</p>}
                  </div>
                </div>
                <div className="decision-actions">
                  {!packet &&
                    plan?.status === "approved" &&
                    !state.pending_revision &&
                    (result?.uncertain_units || 0) > 0 && (
                      <button
                        className="button subtle policy-test"
                        disabled={!canWrite}
                        onClick={() => apply(true)}
                      >
                        Test excluding uncertain stock
                      </button>
                    )}
                  {state.synthetic &&
                    !packet &&
                    plan &&
                    !state.documents.some(
                      (d) => d.filename === "supplier_notice_v2.txt",
                    ) && (
                      <button
                        className="button"
                        disabled={!canWrite}
                        onClick={revision}
                      >
                        <History size={15} />
                        Add supplier v2
                      </button>
                    )}
                  {state.pending_revision && plan && !packet && (
                    <button
                      className="button"
                      disabled={!canWrite}
                      onClick={stale}
                    >
                      Test stale approval
                    </button>
                  )}
                  {!packet && (!plan || state.pending_revision) ? (
                    <button
                      className="button primary"
                      disabled={!canWrite}
                      onClick={analyze}
                    >
                      Review current evidence <ArrowRight size={15} />
                    </button>
                  ) : plan?.status === "proposed" && !packet ? (
                    <button
                      className="button primary"
                      disabled={!canWrite}
                      onClick={approve}
                    >
                      <LockKeyhole size={15} />
                      Approve exact plan
                    </button>
                  ) : plan?.status === "approved" && !packet ? (
                    <button
                      className="button danger"
                      disabled={!canWrite}
                      onClick={() => apply()}
                    >
                      <PackageCheck size={16} />
                      Apply holds
                    </button>
                  ) : (
                    <button
                      className="button primary"
                      disabled={!!busy || (!online && !packet)}
                      onClick={exportPacket}
                    >
                      <FileDown size={16} />
                      Save decision packet
                    </button>
                  )}
                </div>
              </section>
              {diff && (
                <div className="revision-summary">
                  <History size={14} />
                  Reviewed revision: {diff.previous_lots?.join(", ")} →{" "}
                  {diff.lot_ids?.join(", ")} · {diff.old_units} →{" "}
                  {diff.new_units} proposed units. Prior approval does not
                  transfer.
                </div>
              )}
              <footer className="page-footer">
                <span>
                  <ShieldCheck size={13} />
                  {state.synthetic ? "Synthetic records" : "Imported evidence"}
                </span>
                <button
                  className="text-button"
                  disabled={!!busy || !online}
                  onClick={demo}
                >
                  <RotateCcw size={12} />
                  New isolated incident
                </button>
                <div className="platform-actions"><PlatformLinks openWeb={() => void task("Opening web app", async () => { await native?.openWebApp(); })} /></div>
              </footer>
            </>
          )}
        </main>
      </div>
      <input
        ref={input}
        hidden
        type="file"
        accept=".txt,.csv,.pdf"
        multiple
        onChange={(e) => {
          const files = Array.from(e.target.files || []);
          void task("Importing evidence", async () => {
            if (files.length > 8) throw Error("Choose at most 8 files");
            await uploadAll(await Promise.all(files.map(fileUpload)));
          });
          e.target.value = "";
        }}
      />
      <input
        ref={packetInput}
        hidden
        type="file"
        accept=".json"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f)
            void task("Opening offline packet", async () => {
              if (f.size > 6000000) throw Error("Packet limit is 6 MB");
              setPacket(await validatePacket(JSON.parse(await f.text())));
              setReview(false);
              setTab("map");
              setNotice("Historical decision packet opened read-only.");
            });
          e.target.value = "";
        }}
      />
    </div>
  );
}
class Boundary extends React.Component<
  { children: React.ReactNode },
  { error: boolean }
> {
  state = { error: false };
  static getDerivedStateFromError() {
    return { error: true };
  }
  render() {
    return this.state.error ? (
      <main>
        <h1>Packet or view could not be displayed.</h1>
        <p>Reload and select a valid decision packet.</p>
        <button onClick={() => location.reload()}>Reload desk</button>
      </main>
    ) : (
      this.props.children
    );
  }
}
createRoot(document.getElementById("root")!).render(
  <Boundary>
    <App />
  </Boundary>,
);
