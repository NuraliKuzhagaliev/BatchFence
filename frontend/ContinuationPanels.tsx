import { useEffect, useState } from "react";
import {
  ArrowRight,
  Camera,
  Clock3,
  Languages,
  ListChecks,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import type { Case, Document, Upload } from "./types";
import {
  request,
  fileUpload,
  native,
  copyDraft,
  setLiveDemoToken,
} from "./platform";
import {
  Details,
  ReviewForm,
  Section,
  noteField,
  reviewedField,
  useOperation,
  type RecordData,
} from "./ModuleUI";

type Props = {
  state: Case;
  part: "sources" | "requests" | "conditions" | "changes" | "handover";
  doc?: Document;
  readOnly: boolean;
  update: (s: Case) => void;
  openReview?: (s: Case) => void;
};
const uid = () => crypto.randomUUID();
function SourceQuote({ source }: { source: RecordData }) {
  return (
    <div className="assist-citation">
      <span>
        {source.document_id} · {source.block_id}
        {source.page ? " · page " + source.page : ""}
      </span>
      <blockquote>{source.quote}</blockquote>
    </div>
  );
}

function SourceCorrection({
  record,
  disabled,
  save,
}: {
  record: RecordData;
  disabled: boolean;
  save: (body: RecordData) => void;
}) {
  const [text, setText] = useState(
    JSON.stringify(record.raw_draft || record.raw_output || {}, null, 2),
  );
  const [note, setNote] = useState(""),
    [checked, setChecked] = useState(false),
    [error, setError] = useState("");
  return (
    <details className="source-mapping">
      <summary>Correct the rejected proposal against the original</summary>
      <p>
        The raw model failure remains recorded. Saving a correction does not
        approve incident scope or release inventory. Inspect each original quote
        and remove unsupported claims.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          try {
            const corrected = JSON.parse(text);
            setError("");
            save({
              proposal_id: record.id,
              corrected_draft: corrected,
              reviewed: checked,
              note,
            });
          } catch {
            setError("Enter one valid JSON review draft.");
          }
        }}
      >
        <label>
          Source-checked corrected proposal
          <textarea
            aria-label="Source-checked corrected proposal"
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={12}
            disabled={disabled}
          />
        </label>
        <label>
          Correction evidence and reason
          <textarea
            minLength={20}
            maxLength={2000}
            required
            value={note}
            onChange={(e) => setNote(e.target.value)}
            disabled={disabled}
          />
        </label>
        <label className="check">
          <input
            type="checkbox"
            required
            checked={checked}
            onChange={(e) => setChecked(e.target.checked)}
            disabled={disabled}
          />
          I checked the corrected claims against the retained original.
        </label>
        {error && <p role="alert">{error}</p>}
        <button
          className="button"
          disabled={disabled || !checked || note.trim().length < 20}
        >
          Save source-checked correction
        </button>
      </form>
    </details>
  );
}

export function ContinuationPanel({
  state,
  part,
  doc,
  readOnly,
  update,
  openReview,
}: Props) {
  const [data, setData] = useState<RecordData>({}),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true),
    [compare, setCompare] = useState(""),
    [language, setLanguage] = useState("en"),
    [last, setLast] = useState<RecordData | null>(null),
    op = useOperation();
  const route = "/api/cases/" + state.id;
  useEffect(() => {
    setLanguage(
      ["en", "ru", "it"].includes(doc?.evidence_language || "")
        ? doc!.evidence_language!
        : "en",
    );
  }, [doc?.id, doc?.evidence_language]);
  async function refresh() {
    if (readOnly) {
      setData(state.enterprise_packet || {});
      return;
    }
    setData(await request<RecordData>("GET", route + "/assisted"));
    setError("");
  }
  useEffect(() => {
    let active = true;
    setLoading(true);
    if (readOnly) {
      setData(state.enterprise_packet || {});
      setLoading(false);
      return;
    }
    request<RecordData>("GET", route + "/assisted").then(
      (d) => {
        if (active) {
          setData(d);
          setLoading(false);
          setError("");
        }
      },
      (e) => {
        if (active) {
          setError(String(e));
          setLoading(false);
        }
      },
    );
    return () => {
      active = false;
    };
  }, [route, state.revision, state.inventory_version, readOnly]);
  async function mutate(endpoint: string, body: unknown) {
    const result = await request<RecordData>(
      "POST",
      endpoint.startsWith("/api/") ? endpoint : route + "/" + endpoint,
      body,
    );
    setLast(result);
    await refresh();
    update(await request<Case>("GET", route));
    return result;
  }
  async function generate(kind: string, extra: RecordData = {}) {
    return mutate("assist-generate", {
      kind,
      revision: state.revision,
      idempotency_key: uid(),
      ...extra,
    });
  }
  if (loading)
    return (
      <div className="assist-loading" role="status">
        <RefreshCw size={18} /> Reading current evidence and review records…
      </div>
    );
  if (error)
    return (
      <p role="alert" className="inline-error">
        {error}
      </p>
    );
  const disabled = readOnly || op.busy,
    provider = data.provider || {},
    currentDoc = doc || state.documents.at(-1),
    docs = state.documents.map((d) => ({ value: d.id, label: d.filename })),
    q = data.next_evidence;
  const live = (
    <details className="assist-provider">
      <summary>
        Connected assistance ·{" "}
        {readOnly
          ? "RECORDED"
          : provider.gemma_state?.startsWith("CONFIGURED")
            ? "Configured · acceptance separate"
            : "UNAVAILABLE"}
      </summary>
      <p>
        Live requests use the configured server endpoint and finite owner
        allowance. Cloud requests require a connection. No automatic retry or
        fixture substitution.
      </p>
      <label>
        Workspace live-access token
        <input
          type="password"
          autoComplete="off"
          placeholder="Only when required by the owner"
          onChange={(e) => setLiveDemoToken(e.target.value)}
        />
      </label>
      <Details
        title="Provider availability and verification limits"
        value={provider}
      />
    </details>
  );
  return (
    <div className={"assist-workspace assist-" + part}>
      {readOnly && (
        <div className="offline-banner">
          <strong>RECORDED · exported snapshot</strong>
          <p>
            As-of evidence only. Connection and current authorization are
            required for review or actions.
          </p>
        </div>
      )}
      {part === "sources" && (
        <>
          <Section
            eyebrow="EVIDENCE INTERPRETATION"
            title="Read the source. Review the proposal."
          >
            <p>
              Use the original beside typed candidates, paired changes and
              explicit gaps. A model response never updates reviewed scope or
              applied holds.
            </p>
            {live}
            <div className="assist-input-row">
              <label>
                Comparison source
                <select
                  aria-label="Comparison source"
                  value={compare}
                  disabled={disabled}
                  onChange={(e) => setCompare(e.target.value)}
                >
                  <option value="">Current source only</option>
                  {docs
                    .filter((d) => d.value !== currentDoc?.id)
                    .map((d) => (
                      <option key={d.value} value={d.value}>
                        {d.label}
                      </option>
                    ))}
                </select>
              </label>
              <div className="button-row">
                <button
                  className="button primary"
                  disabled={disabled || !currentDoc}
                  onClick={() =>
                    void op.act(async () => {
                      await generate("document", {
                        document_ids: [
                          currentDoc!.id,
                          ...(compare ? [compare] : []),
                        ],
                      });
                    })
                  }
                >
                  Interpret with live Gemma
                </button>
                <button
                  className="button"
                  disabled={disabled || !currentDoc}
                  onClick={() =>
                    void op.act(async () => {
                      await mutate("assist-run", {
                        document_ids: [
                          currentDoc!.id,
                          ...(compare ? [compare] : []),
                        ],
                        revision: state.revision,
                        idempotency_key: uid(),
                        mode: "live",
                      });
                    })
                  }
                >
                  Run Evolus document workflow
                </button>
              </div>
            </div>
            {(data.assist || [])
              .filter((r: RecordData) => !r.kind || r.kind === "document")
              .map((r: RecordData) => (
                <article className="assist-proposal module-card" key={r.id}>
                  <div className="assist-card-heading">
                    <h3>Source interpretation</h3>
                    <span className="assist-status">
                      {r.mode === "live" ? "LIVE" : "SYNTHETIC"} · {r.status}
                    </span>
                  </div>
                  <p>{r.error || r.authority}</p>
                  {r.stale && <p className="caption">Historical proposal · evidence or reviewed facts changed. Start a current interpretation before revising this decision.</p>}
                  {r.correction && (
                    <p className="assist-uncertain">
                      Manually corrected after {r.raw_quality_status}. The
                      original model response and failure remain in provenance.
                    </p>
                  )}
                  {r.status === "failed validation" && !r.stale && (
                    <SourceCorrection
                      record={r}
                      disabled={disabled}
                      save={(body) =>
                        void op.act(async () => {
                          await mutate("assist-review", body);
                        })
                      }
                    />
                  )}
                  {r.status === "running" && (
                    <button
                      className="button"
                      disabled={disabled}
                      onClick={() =>
                        void op.act(async () => {
                          await mutate("assist-poll", { job_id: r.id });
                        })
                      }
                    >
                      Fetch authenticated execution status
                    </button>
                  )}
                  {(r.draft?.candidates || []).map(
                    (c: RecordData, i: number) => (
                      <div className="assist-claim" key={i}>
                        <div>
                          <span className="eyebrow">
                            {c.kind.replaceAll("_", " ")}
                          </span>
                          <strong>{c.value}</strong>
                          <span className="assist-status">{c.disposition}</span>
                          {c.incident_status && (
                            <span className="assist-status">
                              Incident proposal:{" "}
                              {c.incident_status.replaceAll("_", " ")}
                            </span>
                          )}
                        </div>
                        <SourceQuote source={c.source} />
                      </div>
                    ),
                  )}
                  {(r.draft?.changes || []).map((c: RecordData, i: number) => (
                    <div className="assist-diff" key={"d" + i}>
                      <SourceQuote source={c.before} />
                      <ArrowRight size={18} />
                      <SourceQuote source={c.after} />
                    </div>
                  ))}
                  {(r.draft?.contradictions || []).map(
                    (c: RecordData, i: number) => (
                      <div className="assist-conflict" key={"c" + i}>
                        <strong>Contradiction · review both passages</strong>
                        <SourceQuote source={c.before} />
                        <SourceQuote source={c.after} />
                      </div>
                    ),
                  )}
                  {!!r.draft?.unresolved?.length && (
                    <div className="assist-uncertain">
                      <strong>Still unresolved</strong>
                      <ul>
                        {r.draft.unresolved.map((s: string, i: number) => (
                          <li key={i}>{s}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {r.draft?.candidates?.some(
                    (c: RecordData) => c.kind === "supplier_lot",
                  ) && (
                    <button
                      className="button primary"
                      disabled={disabled || !!r.stale}
                      onClick={() =>
                        void op.act(async () => {
                          const s = await request<Case>(
                            "POST",
                            route + "/assist-intake",
                            {
                              proposal_id: r.id,
                              document_id: currentDoc?.id,
                              revision: state.revision,
                            },
                          );
                          update(s);
                          openReview?.(s);
                        })
                      }
                    >
                      Open critical-fact review
                    </button>
                  )}
                  <Details
                    title="Raw proposal, job and execution provenance"
                    value={r}
                  />
                </article>
              ))}
          </Section>
          <Section
            eyebrow="ORIGINAL-LINKED LANGUAGE REVIEW"
            title="Keep the original authoritative"
          >
            <div className="assist-input-row">
              <label>
                Original evidence language
                <select
                  aria-label="Original evidence language"
                  value={language}
                  disabled={disabled}
                  onChange={(e) => setLanguage(e.target.value)}
                >
                  <option value="en">English</option>
                  <option value="ru">Russian</option>
                  <option value="it">Italian</option>
                </select>
              </label>
              <button
                className="button"
                disabled={disabled || !currentDoc}
                onClick={() =>
                  void op.act(async () => {
                    await generate("translation", {
                      document_ids: [currentDoc!.id],
                      language,
                    });
                  })
                }
              >
                <Languages size={17} /> Translate with live Gemma
              </button>
            </div>
            <p>
              IDs and original values stay visible. Critical interpretation
              requires a reviewer able to verify the original. Other languages
              require qualified assistance.
            </p>
            {currentDoc && (
              <details>
                <summary>Supply an explicit derived translation</summary>
                <ReviewForm
                  key={currentDoc.id}
                  title="Manual translation · no model claim"
                  disabled={disabled}
                  fields={[
                    {
                      key: "quote",
                      label: "Exact original passage",
                      type: "area",
                      required: true,
                    },
                    {
                      key: "translation",
                      label: "Derived English translation",
                      type: "area",
                      required: true,
                    },
                    {
                      key: "provenance_reference",
                      label:
                        "Translation tool or qualified assistance reference",
                      required: true,
                    },
                  ]}
                  submit="Save derived version"
                  onSubmit={async (b) => {
                    const block = currentDoc.blocks.find((x) =>
                      x.text.includes(b.quote),
                    );
                    if (!block)
                      throw Error("Quote must occur in the selected original.");
                    await mutate("translation", {
                      document_id: currentDoc.id,
                      language,
                      segments: [
                        {
                          source: {
                            document_id: currentDoc.id,
                            block_id: block.id,
                            quote: b.quote,
                          },
                          translation: b.translation,
                        },
                      ],
                      provenance_reference: b.provenance_reference,
                      idempotency_key: uid(),
                    });
                  }}
                />
              </details>
            )}
            {(data.translation || []).map((t: RecordData) => (
              <article className="module-card" key={t.id}>
                <div className="assist-card-heading">
                  <h3>{t.source_language.toUpperCase()} → EN</h3>
                  <span className="assist-status">{t.status}</span>
                </div>
                {t.segments.map((s: RecordData, i: number) => (
                  <div className="translation-pair" key={i}>
                    <div>
                      <span className="eyebrow">ORIGINAL</span>
                      <SourceQuote source={s.source} />
                    </div>
                    <div>
                      <span className="eyebrow">DERIVED TRANSLATION</span>
                      <p>{s.translation}</p>
                      <small>
                        Original values:{" "}
                        {s.protected_original_values?.join(" · ") ||
                          "None detected; manual review still required"}
                      </small>
                    </div>
                  </div>
                ))}
                {!!t.flags.length && (
                  <div className="assist-uncertain">
                    <strong>Consequential interpretation blocked</strong>
                    {t.flags.map((f: string) => (
                      <p key={f}>{f}</p>
                    ))}
                  </div>
                )}
                {!t.review && (
                  <ReviewForm
                    title="Verify original-language critical fields"
                    disabled={disabled || !!t.flags.length}
                    fields={[
                      {
                        key: "can_verify_original",
                        label:
                          "I can verify the original language, with qualified assistance where needed",
                        type: "check",
                        required: true,
                      },
                      {
                        key: "qualified_reference",
                        label: "Reviewer qualification / assistance reference",
                        required: true,
                      },
                      {
                        key: "critical_fields_confirmed",
                        label:
                          "I checked IDs, quantities, units, dates, negation, modality and completeness against the original",
                        type: "check",
                        required: true,
                      },
                      noteField,
                    ]}
                    submit="Record qualified review"
                    onSubmit={async (b) => {
                      await mutate("translation-review", {
                        ...b,
                        translation_id: t.id,
                      });
                    }}
                  />
                )}
                <Details
                  title="Translation provenance and recorded review"
                  value={t}
                />
              </article>
            ))}
            <LanguageImport
              state={state}
              disabled={disabled}
              done={async () => {
                await refresh();
                update(await request<Case>("GET", route));
              }}
            />
          </Section>
          <LabelPanel
            state={state}
            data={data}
            disabled={disabled}
            readOnly={readOnly}
            mutate={mutate}
            generate={generate}
          />
        </>
      )}
      {part === "requests" && (
        <Section
          eyebrow="NEXT USEFUL EVIDENCE"
          title="Ask for the fact that changes the decision"
        >
          <div className="assist-summary">
            <ListChecks />
            <div>
              <strong>
                {q?.unique_units ?? "—"} distinct units linked to open gaps
              </strong>
              <p>
                Conditional scenarios overlap. Do not add their individual
                effects or treat them as released stock.
              </p>
            </div>
          </div>
          {live}
          <details>
            <summary>Transparent request-ranking rules</summary>
            <ReviewForm
              key={JSON.stringify(q?.ranking)}
              title="Configure display precedence"
              disabled={disabled}
              fields={[
                {
                  key: "policy_first",
                  label: "Prioritize incident-scope and policy prerequisites",
                  type: "check",
                  value: q?.ranking?.policy_first ?? true,
                },
                {
                  key: "deadline_first",
                  label:
                    "Prioritize known committed deadlines, then distinct affected units",
                  type: "check",
                  value: q?.ranking?.deadline_first ?? true,
                },
              ]}
              submit="Save ranking rules"
              onSubmit={async (b) => {
                await mutate("evidence-ranking", b);
              }}
            />
            <p className="caption">
              Supplier response time and probability remain unknown. Ranking
              never changes calculation or approval.
            </p>
          </details>
          {!q?.requests?.length && (
            <p>No unresolved evidence requests are present in this snapshot.</p>
          )}
          {(q?.requests || []).map((r: RecordData) => (
            <article className="module-card" key={r.id}>
              <div className="assist-card-heading">
                <h3>{r.missing}</h3>
                <span className="assist-status">
                  {r.units} units · {r.pool_ids.join(", ")}
                </span>
              </div>
              <p>{r.reason}</p>
              <ul className="assist-reasons">
                {r.priority_reason?.map((v: string) => (
                  <li key={v}>{v}</li>
                ))}
              </ul>
              <p>
                Orders: {r.order_ids?.join(", ") || "None linked"} · Due:{" "}
                {r.due_date || "Unknown"} · Conditional proposal change:{" "}
                {r.conditional ?? "Unknown"} units
              </p>
              <details>
                <summary>Source passages and closure criteria</summary>
                {r.evidence?.map((s: RecordData, i: number) => (
                  <SourceQuote source={s} key={i} />
                ))}
                <p>{r.closure_criteria}</p>
                <Details
                  title="Immutable deterministic request basis"
                  value={r}
                />
              </details>
              <button
                className="button"
                disabled={disabled}
                onClick={() =>
                  void op.act(async () => {
                    await generate("request", { cause_id: r.id });
                  })
                }
              >
                Draft specific request · live Gemma
              </button>
              <ReviewForm
                title="Save request draft"
                disabled={disabled}
                fields={[
                  {
                    key: "role",
                    label: "Responsible role",
                    value: r.responsible_role || "",
                  },
                  {
                    key: "due_date",
                    label: "Known due date (leave unknown if absent)",
                    type: "date",
                    value: r.due_date || "",
                  },
                  {
                    key: "request_draft",
                    label: "Reviewable request · sending disabled",
                    type: "area",
                    value: r.draft,
                    required: true,
                  },
                ]}
                submit="Save assigned evidence request"
                onSubmit={async (b) => {
                  await mutate("evidence-task", {
                    ...b,
                    cause_id: r.id,
                    revision: state.revision,
                    idempotency_key: uid(),
                  });
                }}
              />
            </article>
          ))}
          {(data["evidence-task"] || []).map((t: RecordData) => (
            <article className="module-card" key={t.id}>
              <div className="assist-card-heading">
                <h3>{t.responsible_role || "Owner not assigned"}</h3>
                <span className="assist-status">
                  {t.stale ? "STALE · " : ""}
                  {t.status}
                </span>
              </div>
              <p>{t.draft}</p>
              <p>
                Due: {t.due_date || "Unknown"} · Upload responses against
                request {t.cause_id}.
              </p>
              <button
                className="button"
                onClick={() => void op.act(async () => copyDraft(t.draft))}
              >
                Copy saved draft
              </button>
              <ReviewForm
                title="Review a linked supplier response"
                disabled={disabled}
                fields={[
                  {
                    key: "document_id",
                    label: "Uploaded response document",
                    type: "select",
                    options: docs,
                    required: true,
                  },
                  {
                    key: "quote",
                    label: "Exact original response passage",
                    type: "area",
                    required: true,
                  },
                  {
                    key: "outcome",
                    label: "Response outcome",
                    type: "select",
                    options: ["conflicting", "inconclusive", "resolved"].map(
                      (value) => ({ value, label: value }),
                    ),
                    value: "inconclusive",
                    required: true,
                  },
                  reviewedField,
                  noteField,
                ]}
                submit="Record response review"
                onSubmit={async (b) => {
                  await mutate("response-review", { ...b, task_id: t.id });
                }}
              />
              <Details title="Versioned request and responses" value={t} />
            </article>
          ))}
        </Section>
      )}
      {part === "conditions" && (
        <Section
          eyebrow="RELEASE CONDITIONS"
          title="A checklist, with separate authority"
        >
          <div className="assist-summary">
            <ShieldCheck />
            <div>
              <strong>
                {data.release_conditions?.stage ||
                  "Current release conditions unavailable"}
              </strong>
              <p>
                No readiness percentage. Unknown required conditions block
                progression. Use Controlled Recovery for the exact independent
                approval and acknowledgement.
              </p>
            </div>
          </div>
          <div className="condition-grid">
            {data.release_conditions?.conditions?.map((c: RecordData) => (
              <article
                className={"condition-card condition-" + c.status}
                key={c.id}
              >
                <span className="assist-status">{c.status}</span>
                <h3>{c.id.replaceAll("_", " ")}</h3>
                <p>{c.reason}</p>
                <small>
                  Policy: {c.policy_clause} · version{" "}
                  {c.version ?? "unreviewed"}
                </small>
                <Details
                  title="Source, verifier and timestamp"
                  value={{
                    evidence: c.evidence,
                    verifier: c.verifier,
                    verified_at: c.verified_at,
                  }}
                />
              </article>
            ))}
          </div>
          <Details
            title="Actual recovery-engine conditions and quantities"
            value={data.release_conditions}
          />
        </Section>
      )}
      {part === "changes" && (
        <Section
          eyebrow="RELATED CASES & SOURCE VERSIONS"
          title="Changed evidence needs a new assessment"
        >
          <p>
            A typed dependency graph identifies uses of an earlier source.
            Effective changes queue re-review; completed receipts and applied
            restrictions remain historical facts.
          </p>
          <details>
            <summary>
              Register a reviewed revision, replacement or withdrawal
            </summary>
            <ReviewForm
              title="Source-change assessment"
              disabled={disabled}
              fields={[
                {
                  key: "source_kind",
                  label: "Source type",
                  type: "select",
                  options: [
                    { value: "document", label: "Incident document" },
                    { value: "procedure", label: "Approved procedure" },
                  ],
                  value: "document",
                  required: true,
                },
                {
                  key: "source_id",
                  label: "Stable document / procedure identity",
                  required: true,
                },
                {
                  key: "old_version",
                  label: "Old document revision / procedure version",
                  required: true,
                },
                {
                  key: "new_version",
                  label: "New document ID / procedure version",
                  required: true,
                },
                {
                  key: "classification",
                  label: "Reviewed significance",
                  type: "select",
                  value: "uncertain",
                  options: [
                    "uncertain",
                    "wording_only",
                    "factual",
                    "withdrawal",
                    "applicability",
                  ].map((value) => ({
                    value,
                    label: value.replaceAll("_", " "),
                  })),
                  required: true,
                },
                {
                  key: "effective_at",
                  label: "Effective timestamp (ISO with timezone)",
                  value: new Date().toISOString(),
                  required: true,
                },
                {
                  key: "old_quote",
                  label: "Exact old passage",
                  type: "area",
                  required: true,
                },
                {
                  key: "new_quote",
                  label: "Exact new passage",
                  type: "area",
                  required: true,
                },
                noteField,
              ]}
              submit="Calculate affected cases & queue review"
              onSubmit={async (b) => {
                await mutate("/api/assist/source-change", {
                  ...b,
                  event_key: uid(),
                });
              }}
            />
          </details>
          {(data.rereview || []).map((r: RecordData) => (
            <article className="module-card" key={r.id}>
              <div className="assist-card-heading">
                <h3>{r.reason.replaceAll("_", " ")}</h3>
                <span className="assist-status">{r.status}</span>
              </div>
              <p>
                Owner: {r.responsible_role || "Quality reviewer"} · effective{" "}
                {r.effective_at}
              </p>
              <div className="assist-diff">
                <blockquote>{r.old_quote}</blockquote>
                <ArrowRight />
                <blockquote>{r.new_quote}</blockquote>
              </div>
              {!r.review && (
                <ReviewForm
                  title="Record a current reassessment"
                  disabled={disabled}
                  fields={[reviewedField, noteField]}
                  submit="Record source-change reassessment"
                  onSubmit={async (b) => {
                    await mutate("rereview-review", {
                      ...b,
                      task_id: r.id,
                      revision: state.revision,
                      old_quote: r.old_quote,
                      new_quote: r.new_quote,
                    });
                  }}
                />
              )}
              <Details
                title="Affected objects and immutable version references"
                value={r}
              />
            </article>
          ))}
          {!data.rereview?.length && (
            <p>No source-change reassessments are queued in this incident.</p>
          )}
          <Details
            title="Typed version dependencies"
            value={data["source-link"] || []}
          />
        </Section>
      )}
      {part === "handover" && (
        <Section
          eyebrow="SHIFT HANDOVER"
          title="The next shift starts with the facts"
        >
          <p>
            Versioned quantities, outstanding evidence, owners and next
            permitted action. Acknowledging this brief never approves recovery.
          </p>
          {live}
          <ReviewForm
            title="Create a current shift brief"
            disabled={disabled}
            fields={[
              {
                key: "previous_id",
                label: "Changes since handover",
                type: "select",
                options: (data.handover || []).map((h: RecordData) => ({
                  value: h.id,
                  label: h.as_of,
                })),
              },
            ]}
            submit="Generate deterministic snapshot brief"
            onSubmit={async (b) => {
              await mutate("handover", {
                previous_id: b.previous_id || null,
                idempotency_key: uid(),
              });
            }}
          />
          <button
            className="button"
            disabled={disabled}
            onClick={() =>
              void op.act(async () => {
                await generate("handover", {
                  previous_id: data.handover?.at(-1)?.id || null,
                });
              })
            }
          >
            Prepare brief with live Gemma
          </button>
          {[...(data.handover || [])].reverse().map((h: RecordData) => (
            <article className="handover-card" key={h.id}>
              <div className="assist-card-heading">
                <h3>
                  <Clock3 size={20} /> As of{" "}
                  {new Date(h.as_of).toLocaleString()}
                </h3>
                <span className="assist-status">
                  {readOnly
                    ? "RECORDED"
                    : h.stale
                      ? "STALE"
                      : h.review
                        ? "Reviewed snapshot"
                        : "Awaiting brief review"}
                </span>
              </div>
              <p className="caption">
                {h.provenance?.provider}
                {h.fallback
                  ? " · Deterministic fallback: model output failed fact validation."
                  : ""}
              </p>
              <ul className="handover-facts">
                {h.statements.map((f: RecordData, i: number) => (
                  <li key={i}>
                    <span>{f.text}</span>
                    <small>Reference: {f.fact_id || f.id}</small>
                  </li>
                ))}
              </ul>
              {!!h.snapshot.task_owners_missing?.length && (
                <p className="assist-uncertain">
                  Missing owners: {h.snapshot.task_owners_missing.join(", ")}
                </p>
              )}
              <button
                className="button"
                onClick={() =>
                  void op.act(async () =>
                    copyDraft(
                      (
                        "As of " +
                        h.as_of +
                        "\n" +
                        h.statements.map((f: RecordData) => f.text).join("\n")
                      ).slice(0, 4000),
                    ),
                  )
                }
              >
                Copy brief
              </button>
              {!h.review && (
                <ReviewForm
                  title="Acknowledge snapshot review"
                  disabled={disabled || h.stale}
                  fields={[reviewedField, noteField]}
                  submit="Record brief acknowledgement"
                  onSubmit={async (b) => {
                    await mutate("handover-review", {
                      ...b,
                      handover_id: h.id,
                    });
                  }}
                />
              )}
              <Details
                title="Snapshot facts, event references and provenance"
                value={h}
              />
            </article>
          ))}
          {!data.handover?.length && (
            <p>
              No brief has been created. Export the incident packet after
              generating a brief for historical Windows access.
            </p>
          )}
        </Section>
      )}
      {last && (
        <details className="assist-last">
          <summary>Last operation · {last.status || "saved"}</summary>
          <pre>{JSON.stringify(last, null, 2)}</pre>
        </details>
      )}
      {op.error && (
        <p className="inline-error" role="alert">
          {op.error}
        </p>
      )}
    </div>
  );
}

function LanguageImport({
  state,
  disabled,
  done,
}: {
  state: Case;
  disabled: boolean;
  done: () => Promise<void>;
}) {
  const [language, setLanguage] = useState("en"),
    [requestId, setRequestId] = useState(""),
    op = useOperation();
  async function importFiles(files: Upload[]) {
    for (const f of files)
      await request("POST", "/api/cases/" + state.id + "/documents", {
        ...f,
        synthetic: state.synthetic,
        evidence_language: language,
        ...(requestId ? { request_id: requestId } : {}),
      });
    await done();
  }
  return (
    <details>
      <summary>Import an original with its declared language</summary>
      <div className="assist-input-row">
        <label>
          Original language
          <select
            aria-label="Original language"
            value={language}
            disabled={disabled}
            onChange={(e) => setLanguage(e.target.value)}
          >
            {[
              ["en", "English"],
              ["ru", "Russian"],
              ["it", "Italian"],
              ["unsupported", "Other · qualified support required"],
            ].map(([v, t]) => (
              <option value={v} key={v}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <label>
          Linked evidence-request ID (if a response)
          <input
            value={requestId}
            disabled={disabled}
            onChange={(e) => setRequestId(e.target.value)}
          />
        </label>
        {native ? (
          <button
            className="button"
            disabled={disabled || op.busy}
            onClick={() =>
              void op.act(async () => importFiles(await native!.chooseFiles()))
            }
          >
            Choose original evidence
          </button>
        ) : (
          <label className="button file-button">
            Choose original evidence
            <input
              type="file"
              accept=".txt,.pdf,.csv"
              disabled={disabled || op.busy}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file)
                  void op.act(async () =>
                    importFiles([await fileUpload(file)]),
                  );
                e.target.value = "";
              }}
            />
          </label>
        )}
      </div>
      <p className="caption">
        Original bytes remain unchanged. Non-English evidence requires qualified
        original-language review before consequential use.
      </p>
      {op.error && <p role="alert">{op.error}</p>}
    </details>
  );
}

function LabelPanel({
  state,
  data,
  disabled,
  readOnly,
  mutate,
  generate,
}: {
  state: Case;
  data: RecordData;
  disabled: boolean;
  readOnly: boolean;
  mutate: (e: string, b: unknown) => Promise<RecordData>;
  generate: (k: string, b: RecordData) => Promise<RecordData>;
}) {
  const [pending, setPending] = useState<Upload | null>(null),
    [crop, setCrop] = useState(""),
    [preview, setPreview] = useState<RecordData | null>(null),
    op = useOperation();
  const docs = state.documents.map((d) => ({ value: d.id, label: d.filename }));
  return (
    <Section
      eyebrow="LABEL PHOTO VERIFICATION"
      title="Read identity. Confirm the relationship."
    >
      <p>
        Preserve the original; transmit a metadata-stripped derived PNG. Machine
        reading, document match and source relationship are separate review
        steps. No authenticity or surface-quality claim.
      </p>
      <div className="label-import">
        <Camera size={24} />
        <div>
          <strong>{pending?.filename || "Choose one label photo"}</strong>
          <p>
            PNG, JPEG or WebP · 2 MB · 8 million decoded pixels · single frame.
          </p>
        </div>
        {native ? (
          <button
            className="button"
            disabled={disabled}
            onClick={() =>
              void op.act(async () =>
                setPending((await native!.chooseImages())[0] || null),
              )
            }
          >
            Choose label photo
          </button>
        ) : (
          <label className="button file-button">
            Choose label photo
            <input
              type="file"
              accept=".png,.jpg,.jpeg,.webp"
              disabled={disabled}
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) void op.act(async () => setPending(await fileUpload(f)));
                e.target.value = "";
              }}
            />
          </label>
        )}
      </div>
      {pending && (
        <div className="label-stage">
          <img
            alt="Original label selected for import"
            src={
              "data:image/" +
              (pending.filename.toLowerCase().endsWith(".png")
                ? "png"
                : pending.filename.toLowerCase().endsWith(".webp")
                  ? "webp"
                  : "jpeg") +
              ";base64," +
              pending.content_base64
            }
          />
          <label>
            Operator-selected crop: x, y, width, height
            <input
              placeholder="Leave empty to use the whole image"
              value={crop}
              onChange={(e) => setCrop(e.target.value)}
            />
          </label>
          <p className="caption">
            Coordinates refer to the EXIF-oriented original. No
            machine-localized region is claimed.
          </p>
          <button
            className="button primary"
            disabled={disabled || op.busy}
            onClick={() =>
              void op.act(async () => {
                const values = crop.trim() ? crop.split(",").map(Number) : [];
                if (
                  values.length &&
                  (values.length !== 4 ||
                    values.some((v) => !Number.isInteger(v)))
                )
                  throw Error("Use four integer crop coordinates.");
                await mutate("label-image", { ...pending, crop_xywh: values });
                setPending(null);
              })
            }
          >
            Import original & derived region
          </button>
        </div>
      )}
      {(data.label || []).map((l: RecordData) => (
        <article className="module-card" key={l.id}>
          <div className="assist-card-heading">
            <h3>{l.filename}</h3>
            <span className="assist-status">{l.status}</span>
          </div>
          {!readOnly && (
            <button
              className="button"
              disabled={op.busy}
              onClick={() =>
                void op.act(async () =>
                  setPreview(
                    await request(
                      "GET",
                      "/api/cases/" + state.id + "/label-images/" + l.id,
                    ),
                  ),
                )
              }
            >
              Inspect retained image region
            </button>
          )}
          {preview?.label.id === l.id && (
            <div className="label-stage">
              <img
                alt={"Retained derived region: " + l.filename}
                src={preview!.data_url}
              />
              <p>
                Original {l.original_hash.slice(0, 12)} · derived{" "}
                {l.derived_hash.slice(0, 12)} · {JSON.stringify(l.transform)}
              </p>
            </div>
          )}
          {!l.reading && (
            <>
              <button
                className="button"
                disabled={disabled || op.busy}
                onClick={() =>
                  void op.act(async () => {
                    await generate("label", { label_id: l.id });
                  })
                }
              >
                Read with live AMD vision
              </button>
              <p className="caption">Label model: {data.provider?.vision_model_id || 'Unavailable'} · original-image review remains required.</p>
              <details>
                <summary>
                  Manual operator transcription · explicit alternative
                </summary>
                <ReviewForm
                  title="Manual reading · no vision execution claim"
                  disabled={disabled}
                  fields={[
                    {
                      key: "candidates",
                      label: "Visible candidate IDs (comma separated)",
                      type: "list",
                    },
                    {
                      key: "unresolved_characters",
                      label:
                        "Unresolved characters / O/0, B/8, S/5 ambiguities (comma separated)",
                      type: "list",
                    },
                    {
                      key: "unreadable",
                      label: "Image unreadable · abstain",
                      type: "check",
                    },
                    {
                      key: "reference",
                      label: "Transcription and region inspection reference",
                      required: true,
                    },
                  ]}
                  submit="Save immutable reading proposal"
                  onSubmit={async (b) => {
                    await mutate("label-reading", {
                      label_id: l.id,
                      reading: {
                        candidates: b.candidates,
                        unresolved_characters: b.unresolved_characters,
                        unreadable: b.unreadable,
                      },
                      reference: b.reference,
                    });
                  }}
                />
              </details>
            </>
          )}
          {l.reading && (
            <div className="label-comparison">
              <div>
                <span className="eyebrow">PROPOSED READING</span>
                <strong>
                  {l.reading.candidates.join(" / ") || "Abstained"}
                </strong>
                <p>
                  {l.reading.unresolved_characters.join(" · ") ||
                    "No characters marked unresolved; operator verification still required."}
                </p>
              </div>
              <div>
                <span className="eyebrow">ASSOCIATION</span>
                <strong>
                  {l.review ? "Reviewed relationship" : "Unverified"}
                </strong>
                <p>{l.reading_provenance?.provider || "See provenance"}</p>
              </div>
            </div>
          )}
          {l.reading && !l.review && (
            <ReviewForm
              title="Compare with the original document"
              disabled={disabled}
              fields={[
                {
                  key: "document_id",
                  label: "Original evidence document",
                  type: "select",
                  options: docs,
                  required: true,
                },
                {
                  key: "quote",
                  label:
                    "Exact original passage containing the document lot ID",
                  type: "area",
                  required: true,
                },
                {
                  key: "selected_id",
                  label:
                    "Exact confirmed ID · preserve spelling and leading zeros",
                  required: true,
                },
                {
                  key: "identity_confirmed",
                  label:
                    "I inspected the image and confirmed this exact identity",
                  type: "check",
                  required: true,
                },
                {
                  key: "relationship_verified",
                  label:
                    "I verified the source relationship beyond a catalog/string match",
                  type: "check",
                  required: true,
                },
                {
                  key: "unresolved",
                  label: "Ambiguity remains · association must stay blocked",
                  type: "check",
                },
                noteField,
              ]}
              submit="Record identity & relationship review"
              onSubmit={async (b) => {
                await mutate("label-review", { ...b, label_id: l.id });
              }}
            />
          )}
          <Details
            title="Original hash, crop, raw reading and review provenance"
            value={l}
          />
        </article>
      ))}
      {op.error && (
        <p className="inline-error" role="alert">
          {op.error}
        </p>
      )}
    </Section>
  );
}
