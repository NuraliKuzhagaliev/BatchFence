import { useState } from "react";
import type { Case } from "./types";
import { request, contentHash } from "./platform";
import {
  Details,
  ReviewForm,
  Section,
  noteField,
  reviewedField,
  sourceFields,
  useOperation,
  type ModuleData,
  type RecordData,
} from "./ModuleUI";
const pct = (p: number) => `${(p * 100).toFixed(2)}%`;
function ControlChart({ chart }: { chart: RecordData }) {
  const points = chart.points.filter((p: RecordData) => p.upper !== undefined),
    max =
      Math.max(
        0.01,
        ...points.map((p: RecordData) => Math.max(p.rate, p.upper)),
      ) * 1.15;
  const x = (i: number) => 48 + (i * 680) / Math.max(1, points.length - 1),
    y = (v: number) => 200 - (v / max) * 170;
  const path = (key: string) =>
    points.map((p: RecordData, i: number) => `${x(i)},${y(p[key])}`).join(" ");
  return (
    <figure className="control-chart">
      <svg
        viewBox="0 0 760 240"
        role="img"
        aria-label="Nonconforming-unit proportions against varying three-sigma control limits"
      >
        <line x1="48" x2="728" y1="200" y2="200" stroke="#a2acb8" />
        <line
          x1="48"
          x2="728"
          y1={y(chart.p_bar)}
          y2={y(chart.p_bar)}
          stroke="#7c8797"
          strokeDasharray="4 4"
        />
        <polyline
          points={path("upper")}
          fill="none"
          stroke="#a4650a"
          strokeDasharray="5 3"
        />
        <polyline
          points={path("lower")}
          fill="none"
          stroke="#a4650a"
          strokeDasharray="5 3"
        />
        <polyline
          points={path("rate")}
          fill="none"
          stroke="#147d73"
          strokeWidth="2"
        />
        {points.map((p: RecordData, i: number) => (
          <circle
            key={p.observation_id}
            cx={x(i)}
            cy={y(p.rate)}
            r={p.status === "signal" ? 5 : 3}
            fill={p.status === "signal" ? "#c3384b" : "#147d73"}
          >
            <title>
              {p.observation_id}: {pct(p.rate)}; n={p.inspected}; {p.status}
            </title>
          </circle>
        ))}
        <text x="0" y="34">
          {pct(max)}
        </text>
        <text x="18" y="204">
          0%
        </text>
        <text x="48" y="229">
          Earlier observations
        </text>
        <text x="630" y="229">
          Latest
        </text>
      </svg>
      <figcaption>
        Solid: observed rate · amber: limits by sample size · grey: frozen
        pooled baseline. Red points require investigation.
      </figcaption>
    </figure>
  );
}
export function SignalsPanel({
  state,
  data,
  readOnly,
  mode,
  refresh,
  openCase,
}: {
  state: Case;
  data: ModuleData;
  readOnly: boolean;
  mode: string;
  refresh: () => Promise<void>;
  openCase: (id: string) => Promise<void>;
}) {
  const op = useOperation(),
    [explanation, setExplanation] = useState<RecordData | null>(null),
    obs = data.inspections?.[0];
  const shown =
    explanation ||
    [...(data["signal-explanation"] || [])]
      .sort((a: RecordData, b: RecordData) =>
        String(a.timestamp || "").localeCompare(String(b.timestamp || "")),
      )
      .at(-1);
  const current =
    shown &&
    (data.signals || []).some(
      (s: RecordData) =>
        s.baseline.id === shown.baseline_id &&
        s.chart_digest === shown.chart_digest &&
        s.chart.status === "ready",
    );
  return (
    <Section
      eyebrow="QUALITY SIGNALS"
      title="Variation needs investigation, not an automatic hold."
    >
      <p>
        Compare like-for-like inspections against a reviewed, frozen baseline.
        Control limits describe variation; they are not product acceptance
        limits.
      </p>
      {!obs?.rows?.length ? (
        <p className="module-empty">
          No inspection observations. Import a mapped inspection CSV in the
          incident’s Sources tab, or load the disclosed synthetic training
          records from Overview.
        </p>
      ) : (
        <>
          <details className="module-card">
            <summary>
              Review and freeze a baseline · {obs.rows.length} observations
              available
            </summary>
            <Details
              title="Inspect observation IDs, denominators and source rows"
              value={obs.rows}
            />
            <ReviewForm
              title="Freeze selected baseline observations"
              fields={[
                {
                  key: "observation_ids",
                  label: "Observation IDs, separated by commas",
                  type: "list",
                  required: true,
                },
                {
                  key: "stable_reviewed",
                  label:
                    "I reviewed completeness, comparability and stability of this interval",
                  type: "check",
                  required: true,
                },
                noteField,
              ]}
              submit="Freeze baseline"
              disabled={readOnly}
              onSubmit={async (b) => {
                await request("POST", "/api/signals/baseline-review", {
                  ...b,
                  inspection_revision: obs.revision,
                });
                await refresh();
              }}
            />
          </details>
          {(data.signals || []).map((s: RecordData) => (
            <article className="module-card" key={s.baseline.id}>
              <div className="card-top">
                <h3>
                  {s.baseline.group.product} · {s.baseline.group.process}
                </h3>
                <span
                  className={
                    "pill " +
                    (s.chart.status === "ready" ? "navy" : "uncertainty")
                  }
                >
                  {s.chart.status}
                </span>
              </div>
              <p className="caption">
                Frozen {s.baseline.start} – {s.baseline.end} ·{" "}
                {s.baseline.rows.length} observations ·{" "}
                {s.baseline.group.method} / {s.baseline.group.regime}
              </p>
              {s.chart.status === "ready" ? (
                <>
                  <div className="module-metrics">
                    <div>
                      <strong>{pct(s.chart.p_bar)}</strong>
                      <span>Baseline nonconforming rate</span>
                    </div>
                    <div>
                      <strong>{s.chart.alerts.length}</strong>
                      <span>Statistical signals</span>
                    </div>
                    <div>
                      <strong>
                        {s.chart.baseline_inspected.toLocaleString()}
                      </strong>
                      <span>Baseline units inspected</span>
                    </div>
                  </div>
                  <ControlChart chart={s.chart} />
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Observation</th>
                          <th>Nonconforming / inspected</th>
                          <th>Rate</th>
                          <th>Limits</th>
                          <th>Result</th>
                          <th>Next action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {s.chart.points.map((p: RecordData) => (
                          <tr key={p.observation_id}>
                            <td>{p.observation_id}</td>
                            <td>
                              {p.nonconforming ?? "—"} / {p.inspected}
                            </td>
                            <td>{pct(p.rate)}</td>
                            <td>
                              {p.lower === undefined
                                ? "Insufficient"
                                : `${pct(p.lower)} – ${pct(p.upper)}`}
                            </td>
                            <td>{p.status.replaceAll("_", " ")}</td>
                            <td>
                              {p.status === "signal" && (
                                <button
                                  className="button small"
                                  disabled={readOnly || op.busy}
                                  onClick={() =>
                                    void op.act(async () => {
                                      const r = await request<{
                                        case_id: string;
                                      }>("POST", "/api/signals/investigation", {
                                        baseline_id: s.baseline.id,
                                        observation_id: p.observation_id,
                                        chart_digest: s.chart_digest,
                                        source_case_id: state.id,
                                      });
                                      await openCase(r.case_id);
                                    })
                                  }
                                >
                                  Investigate
                                </button>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <button
                    className="button"
                    disabled={readOnly || op.busy}
                    onClick={() =>
                      void op.act(async () => {
                        setExplanation(
                          await request("POST", "/api/signals/explain", {
                            baseline_id: s.baseline.id,
                            chart_digest: s.chart_digest,
                            mode: mode === "live" ? "live" : "fixture",
                          }),
                        );
                        await refresh();
                      })
                    }
                  >
                    Explain chart · {mode === "live" ? "Live AMD" : "Synthetic"}
                  </button>
                </>
              ) : (
                <p className="inline-error">{s.chart.reason}</p>
              )}
              <Details
                title="Frozen policy, assumptions and source-backed calculation"
                value={s}
              />
            </article>
          ))}
          {!data.signals?.length && (
            <p className="module-empty">
              No reviewed baseline yet. Select a complete stable interval;
              unsupported data stays insufficient.
            </p>
          )}
        </>
      )}
      {shown && (
        <article className="module-card">
          <h3>
            Unreviewed explanation · {shown.mode} · {shown.status}
          </h3>
          <p className="caption">
            Saved response · {shown.timestamp} ·{" "}
            {current
              ? "Matches the current frozen chart"
              : "Historical explanation; evidence changed or chart unavailable. No current authority."}
          </p>
          {shown.output?.comments.map((c: RecordData) => (
            <p key={c.observation_id}>
              <strong>{c.observation_id}</strong> — {c.explanation}
            </p>
          ))}
          <p>{shown.output?.limitations || shown.error}</p>
          <Details
            title="Actual inference provenance and raw output"
            value={shown}
          />
        </article>
      )}
      {op.error && (
        <p className="inline-error" role="alert">
          {op.error}
        </p>
      )}
    </Section>
  );
}
export function KnowledgePanel({
  state,
  data,
  readOnly,
  mode,
  refresh,
  update,
}: {
  state: Case;
  data: ModuleData;
  readOnly: boolean;
  mode: string;
  refresh: () => Promise<void>;
  update: (s: Case) => void;
}) {
  const [answer, setAnswer] = useState<RecordData | null>(null),
    [claim, setClaim] = useState(0),
    [libraryMode, setLibraryMode] = useState(false);
  const shown = answer || (data.answer || []).at(-1),
    docs = data.procedure || [];
  return (
    <Section
      eyebrow="APPROVED KNOWLEDGE"
      title="An answer is only as strong as its source."
    >
      <p>
        Only current, applicable approved revisions enter retrieval. Exact
        passages remain proposals until an explicit, evidence-backed check is
        recorded.
      </p>
      <div className="module-columns">
        <div>
          {mode === "live" && (
            <label className="field-label">
              Live evidence route
              <select
                aria-label="Live knowledge evidence route"
                value={libraryMode ? "evolus" : "amd"}
                disabled={readOnly}
                onChange={(e) => setLibraryMode(e.target.value === "evolus")}
              >
                <option value="amd">AMD · approved local catalog</option>
                <option value="evolus">Gemma · isolated Evolus library</option>
              </select>
            </label>
          )}
          <ReviewForm
            title="Ask the approved procedures"
            disabled={readOnly}
            submit={`Find supported passages · ${mode === "live" ? "Live AMD" : "Synthetic"}`}
            fields={[
              {
                key: "question",
                label: "Question",
                type: "area",
                required: true,
              },
              {
                key: "product",
                label: "Product",
                value: state.stocks[0]?.product_family || "",
                required: true,
              },
              { key: "process", label: "Process", required: true },
            ]}
            onSubmit={async (b) => {
              if (mode === "live" && libraryMode) {
                const r = await request<RecordData>(
                  "POST",
                  "/api/cases/" + state.id + "/assist-generate",
                  {
                    ...b,
                    kind: "knowledge",
                    revision: state.revision,
                    idempotency_key: crypto.randomUUID(),
                  },
                );
                setAnswer(r.linked_answer || { ...r, output: r.draft });
              } else
                setAnswer(
                  await request("POST", "/api/knowledge/answer", {
                    ...b,
                    case_id: state.id,
                    mode: mode === "live" ? "live" : "fixture",
                  }),
                );
              setClaim(0);
              await refresh();
            }}
          />
          {shown && (
            <article className="module-card">
              <span className="pill uncertainty">
                {shown.mode} · {shown.status}
              </span>
              <h3>
                {shown.output?.insufficient_evidence
                  ? "Insufficient evidence"
                  : "Source-backed proposals"}
              </h3>
              {shown.error && <p role="alert">{shown.error}</p>}
              {shown.output?.claims?.map((c: RecordData, i: number) => (
                <blockquote key={i}>
                  <p>{c.quote}</p>
                  <cite>
                    {c.document_id} · revision {c.version} · {c.passage_id}
                  </cite>
                </blockquote>
              ))}
              {shown.output?.missing_information?.map(
                (s: string, i: number) => (
                  <p key={i}>{s}</p>
                ),
              )}
              <Details
                title="Retrieval, actual response and validation"
                value={shown}
              />
              {shown.status === "succeeded" &&
                shown.output?.claims?.length > 0 && (
                  <>
                    <label className="field-label">
                      Procedure passage to check
                      <select
                        value={claim}
                        onChange={(e) => setClaim(Number(e.target.value))}
                      >
                        {shown.output.claims.map((c: RecordData, i: number) => (
                          <option key={i} value={i}>
                            {c.document_id} / {c.passage_id}
                          </option>
                        ))}
                      </select>
                    </label>
                    <ReviewForm
                      key={shown.id + claim}
                      title="Record evidence that this check is complete"
                      help="Source occurrence does not prove authenticity or compliance. Your review and exact supporting evidence remain recorded."
                      fields={[
                        ...sourceFields(state, "evidence_"),
                        reviewedField,
                        noteField,
                      ]}
                      disabled={readOnly}
                      submit="Record reviewed check"
                      onSubmit={async (b) => {
                        update(
                          await request<Case>(
                            "POST",
                            "/api/cases/" + state.id + "/knowledge-check",
                            { ...b, answer_id: shown.id, claim_index: claim },
                          ),
                        );
                        await refresh();
                      }}
                    />
                  </>
                )}
            </article>
          )}
        </div>
        <aside>
          <details className="module-card">
            <summary>Set up an isolated Evolus library · administrator</summary>
            <p>
              Use a dedicated empty read-only Blob library from the configured
              Evolus application. Organization, site, product, process and
              approved revisions are bound before retrieval. Existing libraries
              cannot be silently reused.
            </p>
            <ReviewForm
              title="Bind this approved source set"
              fields={[
                {
                  key: "library_id",
                  label: "Dedicated empty Evolus library ID",
                  required: true,
                },
                { key: "product", label: "Applicable product", required: true },
                { key: "process", label: "Applicable process", required: true },
                {
                  key: "synthetic",
                  label: "Fictional synthetic training sources",
                  type: "check",
                },
                reviewedField,
                noteField,
              ]}
              submit="Index reviewed sources"
              disabled={readOnly}
              onSubmit={async (b) => {
                await request("POST", "/api/assist/knowledge-index", b);
                await refresh();
              }}
            />
          </details>
          <h3>Procedure revisions</h3>
          {!docs.length && (
            <p className="module-empty">
              No procedures loaded. A qualified reviewer must approve applicable
              source passages before answers are available.
            </p>
          )}
          {docs.map((d: RecordData) => (
            <article className="module-card" key={d.id + "@" + d.version}>
              <span className="pill navy">{d.status}</span>
              <h3>{d.id}</h3>
              <p>
                {d.id} · revision {d.version} ·{" "}
                {d.synthetic
                  ? "Fictional training procedure"
                  : "Uploaded procedure"}
              </p>
              <p className="caption">
                Owner: {d.owner} · {d.products.join(", ")} /{" "}
                {d.processes.join(", ")}
              </p>
              <Details
                title="Original approved passages and applicability"
                value={d}
              />
            </article>
          ))}
          <details className="module-card">
            <summary>Review a plain-text procedure revision</summary>
            <ReviewForm
              title="Record a source passage and its applicability"
              help="Paste the exact approved source text. A new revision is required for changed content. This records your approval; it does not authenticate the external document."
              fields={[
                { key: "id", label: "Procedure identifier", required: true },
                {
                  key: "version",
                  label: "Revision number",
                  type: "number",
                  required: true,
                },
                { key: "owner", label: "Procedure owner", required: true },
                {
                  key: "products",
                  label: "Applicable products (comma separated)",
                  type: "list",
                  required: true,
                },
                {
                  key: "processes",
                  label: "Applicable processes (comma separated)",
                  type: "list",
                  required: true,
                },
                {
                  key: "valid_from",
                  label: "Effective from (ISO timestamp with timezone)",
                  required: true,
                },
                {
                  key: "valid_to",
                  label: "Effective until (optional ISO timestamp)",
                },
                {
                  key: "text",
                  label: "Exact source passage (maximum 2,000 characters)",
                  type: "area",
                  required: true,
                },
                {
                  key: "page",
                  label: "Source page number",
                  type: "number",
                  required: true,
                },
                {
                  key: "synthetic",
                  label: "Fictional synthetic training procedure",
                  type: "check",
                },
                reviewedField,
                noteField,
              ]}
              submit="Approve this procedure revision"
              disabled={readOnly}
              onSubmit={async (b) => {
                const passages = [{ id: "P1", page: b.page, text: b.text }];
                await request("POST", "/api/knowledge/procedure-review", {
                  document: {
                    id: b.id,
                    version: b.version,
                    owner: b.owner,
                    products: b.products,
                    processes: b.processes,
                    valid_from: b.valid_from,
                    valid_to: b.valid_to || null,
                    status: "approved",
                    synthetic: b.synthetic,
                    passages,
                    source_hash: await contentHash(passages),
                  },
                  reviewed: b.reviewed,
                  note: b.note,
                });
                await refresh();
              }}
            />
          </details>
          <details className="module-card">
            <summary>Add or change an approved procedure revision</summary>
            <ReviewForm
              title="Review a procedure record"
              help="Supply the documented procedure JSON contract. Existing version contents are immutable; changed content needs a new version. This action records reviewer approval."
              fields={[
                {
                  key: "document",
                  label:
                    "Procedure JSON (id, version, status, products, processes, owner, valid_from, valid_to, synthetic, source_hash, passages)",
                  type: "area",
                  required: true,
                },
                reviewedField,
                noteField,
              ]}
              submit="Record procedure review"
              disabled={readOnly}
              onSubmit={async (b) => {
                await request("POST", "/api/knowledge/procedure-review", {
                  ...b,
                  document: JSON.parse(b.document),
                });
                await refresh();
              }}
            />
          </details>
        </aside>
      </div>
      <Details
        title="Completed incident checks"
        value={state.procedure_checks || []}
      />
    </Section>
  );
}
