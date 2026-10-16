import type { Case, Result } from "./types";
export const labels = {
  documented: "Documented exposure",
  uncertain: "Uncertain exposure",
  outside: "Outside current evidenced scope",
};
const shortId = (id: string) =>
  id.length > 17 ? id.slice(0, 8) + "…" + id.slice(-6) : id;
export function Graph({
  data,
  result,
  selected,
  onSelect,
}: {
  data: Case;
  result: Result;
  selected: string;
  onSelect: (id: string) => void;
}) {
  const terminalIds = new Set(result.rows.map((r) => r.id));
  if (data.edges.some((e) => !terminalIds.has(e.target))) {
    return (
      <EventGraph
        data={data}
        result={result}
        selected={selected}
        onSelect={onSelect}
      />
    );
  }
  const sources = Array.from(new Set(data.edges.map((e) => e.source))).sort(),
    height = Math.max(360, result.rows.length * 55 + 56);
  const sy = (id: string) =>
    48 +
    (sources.indexOf(id) * (height - 92)) / Math.max(1, sources.length - 1);
  const ty = (id: string) =>
    40 +
    (result.rows.findIndex((r) => r.id === id) * (height - 80)) /
      Math.max(1, result.rows.length - 1);
  return (
    <div className={"graph " + (data.pending_revision ? "graph-stale" : "")}>
      <div className="graph-topline">
        <span>SUPPLIER LOTS</span>
        <span>FINISHED STOCK · NORTH-01</span>
      </div>
      <svg
        viewBox={"0 0 740 " + height}
        role="img"
        aria-label="Stock lineage graph. Dashed lines show uncertain ancestry. Use stock buttons or lineage table to inspect results."
      >
        <defs>
          <pattern
            id="grid"
            width="20"
            height="20"
            patternUnits="userSpaceOnUse"
          >
            <circle cx="1" cy="1" r=".6" fill="#1d3048" />
          </pattern>
        </defs>
        <rect width="740" height={height} fill="url(#grid)" />
        {data.edges
          .filter((e) => result.rows.some((r) => r.id === e.target))
          .map((e, i) => {
            const r = result.rows.find((r) => r.id === e.target)!;
            return (
              <path
                key={i}
                d={
                  "M228 " +
                  (sy(e.source) + 13) +
                  " C355 " +
                  (sy(e.source) + 13) +
                  ",350 " +
                  (ty(e.target) + 12) +
                  ",476 " +
                  (ty(e.target) + 12)
                }
                className={
                  "graph-edge " +
                  r.classification +
                  (e.kind === "possible" ? " possible" : "") +
                  (selected === e.target ? " edge-selected" : "")
                }
              />
            );
          })}
        {sources.map((id) => (
          <g key={id} transform={"translate(36 " + sy(id) + ")"}>
            <title>{id}</title>
            <rect
              y="-10"
              width="192"
              height="46"
              rx="8"
              className={
                "supplier-node " +
                (data.scope.lot_ids.includes(id) ? "affected" : "")
              }
            />
            <circle
              cx="20"
              cy="13"
              r="4"
              fill={data.scope.lot_ids.includes(id) ? "#f3737d" : "#718399"}
            />
            <text x="35" y="18" className="node-id">
              {shortId(id)}
            </text>
            <text
              x="180"
              y="18"
              textAnchor="end"
              className={
                "supplier-state " +
                (data.scope.lot_ids.includes(id) ? "affected-text" : "")
              }
            >
              {data.scope.lot_ids.includes(id) ? "AFFECTED" : data.scope.uncertain_lot_ids?.includes(id) ? "UNRESOLVED" : "LOT"}
            </text>
          </g>
        ))}
        {result.rows.map((r) => (
          <g
            key={r.id}
            transform={"translate(476 " + ty(r.id) + ")"}
            className={
              "stock-node " +
              r.classification +
              (selected === r.id ? " node-selected" : "")
            }
            role="button"
            tabIndex={0}
            aria-label={
              r.id + ", " + r.units + " units, " + labels[r.classification]
            }
            onClick={() => onSelect(r.id)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onSelect(r.id);
              }
            }}
          >
            <title>{r.id}</title>
            <rect y="-12" width="226" height="49" rx="8" />
            <rect className="node-accent" width="3" height="27" y="-1" rx="1" />
            <text x="17" y="9" className="node-id">
              {shortId(r.id)}
            </text>
            <text x="17" y="26" className="node-sub">
              {r.status === "shipped"
                ? "Shipped · review required"
                : r.classification === "outside"
                  ? "Outside evidenced scope"
                  : r.classification === "uncertain"
                    ? "Uncertain · hold required"
                    : "Documented · hold required"}
            </text>
            <text x="210" y="12" textAnchor="end" className="node-quantity">
              {r.units.toLocaleString()}
            </text>
            <text x="210" y="27" textAnchor="end" className="node-sub">
              units
            </text>
          </g>
        ))}
      </svg>
      <div className="mobile-lineage">
        {result.rows.map((r) => (
          <button
            key={r.id}
            className={
              "mobile-stock " +
              r.classification +
              (selected === r.id ? " selected" : "")
            }
            onClick={() => onSelect(r.id)}
          >
            <span>
              <code>{r.id}</code>
              <strong>
                {r.units} <small>units</small>
              </strong>
            </span>
            <span>{labels[r.classification]}</span>
            <small>{r.path.join(" → ") || "Unknown ancestry"}</small>
          </button>
        ))}
      </div>
      <div className="graph-legend">
        <span>
          <i className="dot documented" />
          Documented
        </span>
        <span>
          <i className="dot uncertain" />
          Uncertain · dashed
        </span>
        <span>
          <i className="dot outside" />
          Outside scope
        </span>
        <span className="graph-policy">{data.policy.id}</span>
      </div>
      {data.pending_revision && (
        <div className="stale-overlay">
          Previous calculation · new evidence awaits review
        </div>
      )}
    </div>
  );
}

// Imported split/rework records retain their versioned event nodes in the map.
function EventGraph({
  data,
  result,
  selected,
  onSelect,
}: {
  data: Case;
  result: Result;
  selected: string;
  onSelect: (id: string) => void;
}) {
  const all = Array.from(
    new Set([
      ...data.edges.flatMap((e) => [e.source, e.target]),
      ...result.rows.map((r) => r.id),
    ]),
  ).sort();
  const levels = new Map<string, number>(),
    active = new Set<string>();
  const level = (id: string): number => {
    if (levels.has(id)) return levels.get(id)!;
    if (active.has(id)) throw Error("Packet contains a lineage cycle");
    active.add(id);
    const parents = data.edges
      .filter((e) => e.target === id)
      .map((e) => e.source);
    const depth = parents.length ? 1 + Math.max(...parents.map(level)) : 0;
    active.delete(id);
    levels.set(id, depth);
    return depth;
  };
  all.forEach(level);
  const max = Math.max(1, ...levels.values()),
    width = (max + 1) * 250 + 24;
  result.rows.forEach((r) => levels.set(r.id, max));
  const layers = Array.from({ length: max + 1 }, (_, i) =>
    all.filter((id) => levels.get(id) === i),
  );
  const height = Math.max(360, ...layers.map((x) => x.length * 70 + 40));
  const pos = (id: string) => ({
    x: 24 + (levels.get(id) || 0) * 250,
    y:
      40 +
      (layers[levels.get(id) || 0].indexOf(id) * (height - 80)) /
        Math.max(1, layers[levels.get(id) || 0].length - 1),
  });
  // Server annotations include unresolved seeds and possible paths. Historical
  // packets without annotations keep intermediates uncertain rather than outside.
  const status = (id: string) => result.rows.find((r) => r.id === id)?.classification || result.node_states?.[id] || "uncertain";
  const path = result.rows.find((r) => r.id === selected)?.path || [];
  return (
    <div className="graph event-graph">
      <div className="graph-topline">
        <span>LOT & VERSIONED EVENT LINEAGE</span>
        <span>CURRENT FINISHED STOCK</span>
      </div>
      <div className="event-graph-scroll">
        <svg
          viewBox={"0 0 " + width + " " + height}
          style={{ minWidth: Math.min(width, 1100) }}
          role="img"
          aria-label="Lot and event genealogy. Each versioned event is preserved. Use the lineage table for full source details."
        >
          {data.edges.map((e, i) => {
            const a = pos(e.source),
              b = pos(e.target);
            return (
              <path
                key={i}
                d={
                  "M" +
                  (a.x + 190) +
                  " " +
                  (a.y + 12) +
                  " C" +
                  (a.x + 220) +
                  " " +
                  (a.y + 12) +
                  "," +
                  (b.x - 30) +
                  " " +
                  (b.y + 12) +
                  "," +
                  b.x +
                  " " +
                  (b.y + 12)
                }
                className={
                  "graph-edge " +
                  status(e.target) +
                  (e.kind === "possible" ? " possible" : "") +
                  (path.includes(e.source) && path.includes(e.target)
                    ? " edge-selected"
                    : "")
                }
              />
            );
          })}
          {all.map((id) => {
            const p = pos(id),
              r = result.rows.find((r) => r.id === id);
            return (
              <g
                key={id}
                transform={"translate(" + p.x + " " + p.y + ")"}
                className={
                  "stock-node " +
                  status(id) +
                  (selected === id ? " node-selected" : "")
                }
                role={r ? "button" : undefined}
                tabIndex={r ? 0 : undefined}
                aria-label={
                  r
                    ? id +
                      ", " +
                      r.units +
                      " units, " +
                      labels[r.classification]
                    : undefined
                }
                onClick={() => {
                  if (r) onSelect(id);
                }}
                onKeyDown={(e) => {
                  if (r && (e.key === "Enter" || e.key === " ")) {
                    e.preventDefault();
                    onSelect(id);
                  }
                }}
              >
                <rect y="-12" width="190" height="49" rx="8" />
                <text x="12" y="9" className="node-id">
                  {id}
                </text>
                <text x="12" y="26" className="node-sub">
                  {r
                    ? labels[r.classification]
                    : data.scope.lot_ids.includes(id)
                      ? "Reviewed affected lot"
                      : "Lot / versioned event"}
                </text>
                {r && (
                  <text
                    x="176"
                    y="10"
                    className="node-quantity"
                    textAnchor="end"
                  >
                    {r.units}
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      </div>
      <div className="mobile-lineage">
        {result.rows.map((r) => (
          <button
            key={r.id}
            className={"mobile-stock " + r.classification}
            onClick={() => onSelect(r.id)}
          >
            <span>
              <code>{r.id}</code>
              <strong>{r.units}</strong>
            </span>
            <span>{labels[r.classification]}</span>
            <small>{r.path.join(" → ")}</small>
          </button>
        ))}
      </div>
      <div className="graph-legend">
        <span>
          <i className="dot documented" />
          Documented
        </span>
        <span>
          <i className="dot uncertain" />
          Uncertain · dashed
        </span>
        <span>
          <i className="dot outside" />
          Outside scope
        </span>
      </div>
    </div>
  );
}

export function GenealogyPreview({data}: {data: Case}) {
  return <section className="genealogy-preview" aria-label="Genealogy not yet evaluated">
    <div className="graph-topline"><span>GENEALOGY PREVIEW</span><span>NOT YET EVALUATED</span></div>
    <p>Existing source records only. No exposure classification or hold decision yet.</p>
    {data.stocks.map(s => <div className="preview-path" key={s.id}>
      <span>{data.edges.filter(e=>e.target===s.id).map(e=>e.source+(e.kind==='possible'?' (?)':'')).join(' / ') || 'Unknown ancestry'}</span>
      <span aria-hidden="true">→</span><strong>{s.id}</strong><span>{s.units} units</span>
    </div>)}
  </section>;
}
