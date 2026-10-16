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
  native,
  savePacket,
  fileUpload,
  validatePacket,
} from "./platform";
import type { Case, Document, Evidence, Packet, Upload } from "./types";
import { Graph, labels } from "./Graph";
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
function App() {
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
    [checked, setChecked] = useState(false),
    [bounded, setBounded] = useState(true),
    [mode, setMode] = useState("fixture"),
    [technical, setTechnical] = useState(false);
  const [cases, setCases] = useState<
      { id: string; name: string; revision: number }[]
    >([]),
    input = useRef<HTMLInputElement>(null),
    packetInput = useRef<HTMLInputElement>(null);
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
        const health = await request<{inference_mode:string;amd_configured:boolean}>("GET", "/api/health");
        const all = await request<typeof cases>("GET", "/api/cases");
        if (!active) return;
        setCases(all);
        setMode(health.amd_configured && health.inference_mode === "live" ? "live" : "fixture");
        const id = localStorage.getItem("bf.case");
        if (id && all.some((c) => c.id === id)) {
          const c = await request<Case>("GET", "/api/cases/" + id);
          if (active) setData(c);
        }
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
    const t = setInterval(
      () =>
        request("GET", "/api/health")
          .then(async () => {
            if (!active) return;
            if (!connectionWasAvailable.current) {
              const all = await request<typeof cases>("GET", "/api/cases");
              const id = localStorage.getItem("bf.case");
              const current = id && all.some(c => c.id === id)
                ? await request<Case>("GET", "/api/cases/" + id) : null;
              if (!active) return;
              setCases(all);
              setData(current);
              setReview(false);
              setNotice("Backend reconnected. Current evidence and action state reloaded.");
            }
            connectionWasAvailable.current = true;
            setOnline(true);
          })
          .catch(() => {
            connectionWasAvailable.current = false;
            if (active) setOnline(false);
          }),
      15000,
    );
    return () => {
      active = false;
      clearInterval(t);
    };
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
        setLots(
          r
            .output!.facts.filter((f) => f.affected)
            .map((f) => f.lot_id)
            .join(", "),
        );
        setChecked(false);
        setBounded(s.bounded);
        setReview(true);
        setMobile("map");
      },
    );
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
          bounded_scope_reviewed: bounded,
          note: "Checked source context, lot IDs, exclusions and completeness in workbench.",
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
      setNotice("This exact plan is approved. Sandbox execution is available.");
    });
  }
  async function apply(test = false) {
    if (!state || !plan) return;
    await task(
      test ? "Testing uncertain-stock policy" : "Applying sandbox holds",
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
          "Sandbox transaction committed. Receipt and evidence are ready to export.",
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
        ? "Applied to sandbox"
        : plan?.status === "approved"
          ? "Exact plan approved"
          : plan
            ? "Review complete · awaiting approval"
            : "Critical scope review required";
  const diff = state?.history
    .filter((h) => h.type === "reviewed" && h.old_units != null)
    .at(-1);
  return (
    <div className="app-shell">
      <aside className="rail">
        <a href="/" className="rail-brand" aria-label="BatchFence home">
          <Mark />
        </a>
        <div className="rail-line" />
        {[
          [Network, "Incident", "map"],
          [Files, "Sources", "sources"],
          [History, "History", "timeline"],
        ].map(([Icon, title, key]) => {
          const I = Icon as typeof Network;
          return (
            <button
              className={"rail-item " + (tab === key ? "active" : "")}
              key={String(key)}
              title={String(title)}
              onClick={() => {
                setTab(String(key));
                setMobile(key === "sources" ? "sources" : "map");
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
            <span className="workspace-name">Containment desk</span>
          </div>
          <div className="top-actions">
            <span className={"connection " + (!online ? "offline" : "")}>
              <i />
              {online ? "Backend connected" : "Backend offline"}
            </span>
            <span className="environment">SANDBOX</span>
            <button
              className="icon-button"
              aria-label="Technical details"
              onClick={() => setTechnical(!technical)}
            >
              <CircleHelp size={18} />
            </button>
          </div>
        </header>
        <main>
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                QUALITY OPERATIONS <ChevronRight size={12} /> INCIDENT WORKBENCH
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
                Default quota: 12 attempts per session.
              </p>
            </section>
          )}
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
              <span>{error || busy || notice}</span>
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
          {!state ? (
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
                    Load synthetic incident <ArrowRight size={17} />
                  </button>
                  <button className="button" onClick={openPacket}>
                    <FolderOpen size={16} />
                    Review a packet
                  </button>
                </div>
                <p className="demo-note">
                  Fictional manufacturer · cosmetic coating issue
                  <br />
                  Fixture walkthrough is labeled. Live AMD requires
                  configuration.
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
                  Human review. Deterministic policy. Auditable action.
                </div>
              </div>
              <div className="distribution">
                <a href="/" className="distribution-link">
                  <ExternalLink size={16} />
                  Open web app<span>Local v0.1.0</span>
                </a>
                <div className="distribution-link muted">
                  <PackageCheck size={16} />
                  Windows app
                  <span>Unsigned installer · public download pending</span>
                </div>
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
                      ? run.status === "succeeded" ? "LIVE AMD" : "LIVE REQUEST FAILED"
                      : run?.mode === "recorded"
                        ? "RECORDED REPLAY"
                        : "SYNTHETIC FIXTURE"}
                </span>
                <span>Evidence r{state.revision}</span>
                <span>Stock v{state.inventory_version}</span>
                <span className="case-status">
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
                      value={mode}
                      disabled={readOnly || !!busy}
                      onChange={(e) => setMode(e.target.value)}
                    >
                      <option value="fixture">
                        Fixture · synthetic parser
                      </option>
                      <option value="live">Live · AMD endpoint</option>
                    </select>
                    <button
                      className="button primary full"
                      disabled={!canWrite || !doc}
                      onClick={analyze}
                    >
                      <Search size={15} />
                      Extract selected notice
                    </button>
                    <p className="caption">
                      {mode === "fixture"
                        ? "Synthetic walkthrough. No AI inference is claimed."
                        : "Fresh AMD request. Failures stay visible."}
                    </p>
                    {currentRun && !review && !packet && (
                      <button
                        className="text-button"
                        onClick={() => {
                          setLots(
                            run!
                              .output!.facts.filter((f) => f.affected)
                              .map((f) => f.lot_id)
                              .join(", "),
                          );
                          setChecked(false);
                          setReview(true);
                        }}
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
                        {tab === "timeline"
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
                  <div
                    className="tabs"
                    role="tablist"
                    aria-label="Incident views"
                  >
                    {[
                      ["map", "Exposure"],
                      ["requests", "Evidence requests"],
                      ["orders", "Order review"],
                      ["timeline", "Revisions"],
                      ["receipt", "Receipt"],
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
                  {result && (
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
                            : "Policy-required hold"}
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
                        Interpretation proposes facts. Your review determines
                        scope and supersession.
                      </p>
                      {run?.output?.facts.map((f, i) => (
                        <button
                          className="candidate"
                          key={i}
                          onClick={() => showEvidence(f.evidence[0])}
                        >
                          <code>{f.lot_id}</code>
                          <span>
                            {f.affected
                              ? "Affected candidate"
                              : "Mentioned only"}
                          </span>
                          <small>
                            Inspect quote <ChevronRight size={12} />
                          </small>
                        </button>
                      ))}
                      <label className="field-label" htmlFor="review-lots">
                        Accepted affected lots · comma separated
                      </label>
                      <input
                        id="review-lots"
                        value={lots}
                        onChange={(e) => setLots(e.target.value)}
                      />
                      <label className="checkbox">
                        <input
                          type="checkbox"
                          checked={bounded}
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
                        disabled={!checked || !canWrite}
                        onClick={confirm}
                      >
                        <Check size={16} />
                        Confirm scope & calculate
                      </button>
                    </section>
                  ) : tab === "timeline" ? (
                    <section className="timeline">
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
                              <p>Candidate lots: {h.suggested_lots.join(", ")}. Accepted lots: {h.lot_ids?.join(", ")}.</p>
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
                      <SourceText doc={doc} />
                    </section>
                  ) : tab === "requests" ? (
                    <section className="queue">
                      {result?.requests.length ? (
                        <>
                          <div className="queue-summary">
                            <CircleHelp size={22} />
                            <p>
                              <strong>
                                {num(result.request_unique_units)} units ·{" "}
                                {euro(result.request_unique_cents)}
                              </strong>
                              <br />
                              Maximum inventory value potentially clarified,
                              deduplicated. A record may confirm exposure.
                            </p>
                          </div>
                          {result.requests.map((r, i) => (
                            <article className="request-card" key={r.id}>
                              <b className="request-rank">0{i + 1}</b>
                              <div>
                                <h3>{r.missing}</h3>
                                <span className="pill uncertainty">
                                  {r.units} uncertain units ·{" "}
                                  {euro(r.value_cents)}
                                </span>
                                <p>{r.reason}</p>
                                <textarea
                                  readOnly
                                  aria-label={"Draft for " + r.id}
                                  value={r.draft}
                                />
                                <button
                                  className="button small"
                                  onClick={() =>
                                    task("Copying request draft", async () => {
                                      await navigator.clipboard.writeText(
                                        r.draft,
                                      );
                                      setNotice(
                                        "Draft copied. No message was sent.",
                                      );
                                    })
                                  }
                                >
                                  <ClipboardCopy size={14} />
                                  Copy request draft
                                </button>
                                <button
                                  className="text-button"
                                  onClick={() => selectStock(r.pool_ids[0])}
                                >
                                  Inspect gap <ArrowRight size={13} />
                                </button>
                              </div>
                            </article>
                          ))}
                        </>
                      ) : (
                        <Empty text="Review scope first, or all relevant ancestry is resolved." />
                      )}
                    </section>
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
                              SANDBOX EXECUTION RECEIPT
                            </span>
                            <h3>Holds applied. Evidence preserved.</h3>
                            <p>
                              A real local database transaction updated sandbox
                              inventory.
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
                              Sandbox only. No machinery, supplier communication
                              or external inventory system was involved.
                            </p>
                          </article>
                        ))
                      ) : (
                        <Empty text="A receipt exists only after an approved plan commits to the sandbox." />
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
                    <div className="map-empty">
                      <Network size={55} />
                      <h3>Your evidence is ready.</h3>
                      <p>
                        Extract the notice, check candidate lot IDs, then
                        calculate containment.
                      </p>
                      <button
                        className="button light"
                        disabled={!canWrite}
                        onClick={analyze}
                      >
                        Extract & review notice <ArrowRight size={16} />
                      </button>
                      <span className="caption">
                        No stock has been held. Human review comes first.
                      </span>
                    </div>
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
                          <dd>{row.status}</dd>
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
                      Apply sandbox holds
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
                  Synthetic data · bounded containment prototype
                </span>
                <button
                  className="text-button"
                  disabled={!!busy || !online}
                  onClick={demo}
                >
                  <RotateCcw size={12} />
                  New isolated incident
                </button>
                <span>
                  BatchFence 0.1.0 · {native ? "Windows desktop" : "Web app"}
                </span>
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
