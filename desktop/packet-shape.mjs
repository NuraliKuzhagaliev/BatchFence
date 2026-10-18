// Shared pure validation for the web renderer and native main process.
export function validateShape(p) {
  const object = (x) =>
    x !== null && typeof x === "object" && !Array.isArray(x);
  const str = (x) => typeof x === "string";
  const integer = (x) => Number.isSafeInteger(x) && x >= 0;
  const strings = (x) => Array.isArray(x) && x.every(str);
  const ref = (x) =>
    object(x) && str(x.document_id) && str(x.block_id) && str(x.quote);
  const stock = (x) =>
    object(x) &&
    str(x.id) &&
    integer(x.units) &&
    integer(x.unit_cents) &&
    ["available", "held", "shipped"].includes(x.status) &&
    typeof x.complete === "boolean";
  const row = (x) =>
    stock(x) &&
    ["documented", "uncertain", "outside"].includes(x.classification) &&
    str(x.reason) &&
    strings(x.path) &&
    Array.isArray(x.evidence) &&
    x.evidence.every(ref);
  const plan = (x) =>
    x === null ||
    (object(x) &&
      str(x.id) &&
      str(x.digest) &&
      ["proposed", "approved", "stale", "applied"].includes(x.status) &&
      Array.isArray(x.actions) &&
      x.actions.every(
        (a) => object(a) && a.type === "hold" && str(a.pool_id),
      ) &&
      object(x.result) &&
      Array.isArray(x.result.rows) &&
      x.result.rows.every(row) &&
      [
        "hold_units",
        "documented_units",
        "uncertain_units",
        "outside_units",
        "broad_units",
        "hold_cents",
        "broad_cents",
        "excluded_cents",
        "request_unique_units",
        "request_unique_cents",
      ].every((k) => integer(x.result[k])) &&
      Array.isArray(x.result.requests) &&
      x.result.requests.every(
        (r) =>
          object(r) &&
          str(r.id) &&
          str(r.missing) &&
          str(r.reason) &&
          str(r.draft) &&
          strings(r.pool_ids) &&
          integer(r.units) &&
          integer(r.value_cents),
      ) &&
      Array.isArray(x.result.orders) &&
      x.result.orders.every(
        (o) =>
          object(o) &&
          str(o.order_id) &&
          str(o.due_date) &&
          strings(o.pool_ids) &&
          integer(o.units) &&
          str(o.reason),
      ) &&
      strings(x.result.shipment_reviews));
  if (
    !object(p) ||
    p.schema_version !== 1 ||
    !str(p.exported_at) ||
    !str(p.label) ||
    !str(p.integrity_hash) ||
    !object(p.case)
  )
    throw Error("Invalid decision packet schema");
  const c = p.case;
  // Extension snapshots are read-only JSON evidence, never hydrated action authority.
  // Validate fields also used by the preserved incident view before rendering them.
  if ((c.enterprise_packet !== undefined && !object(c.enterprise_packet)) ||
      ['receiving_runs','hold_ledger','recovery_receipts','procedure_checks'].some(k =>
        c[k] !== undefined && (!Array.isArray(c[k]) || c[k].length > 2000 || !c[k].every(object))) ||
      (c.quantities !== undefined && (!object(c.quantities) ||
        !['applied_hold_units','recovery_pending_units','confirmed_recovery_units'].every(k => integer(c.quantities[k])))))
    throw Error('Invalid historical module evidence');
  const arrays = [
    "documents",
    "stocks",
    "edges",
    "allocations",
    "reviews",
    "runs",
    "receipts",
    "history",
    "plans",
  ];
  if (
    !arrays.every((k) => Array.isArray(c[k]) && c[k].length <= 2000) ||
    !str(c.id) ||
    !str(c.name) ||
    !str(c.incident) ||
    typeof c.synthetic !== "boolean" ||
    !integer(c.revision) ||
    !integer(c.inventory_version) ||
    !object(c.scope) ||
    !strings(c.scope.lot_ids) ||
    !object(c.policy) ||
    !str(c.policy.id) ||
    !str(c.policy.rule) ||
    !c.documents.every(
      (d) =>
        object(d) &&
        str(d.id) &&
        str(d.filename) &&
        integer(d.revision) &&
        str(d.media_type) &&
        typeof d.synthetic === "boolean" &&
        str(d.original_hash) &&
        str(d.text_hash) &&
        (d.ocr === undefined || (object(d.ocr) && str(d.ocr.engine) &&
          typeof d.ocr.critical_fields_confirmed === 'boolean' && Array.isArray(d.ocr.pages) &&
          d.ocr.pages.length <= 8 && d.ocr.pages.every(p => object(p) && integer(p.page) && p.page > 0 && str(p.image_hash)))) &&
        Array.isArray(d.blocks) &&
        d.blocks.length <= 5000 &&
        d.blocks.every((b) => object(b) && str(b.id) && str(b.text)),
    ) ||
    !c.stocks.every(stock) ||
    !c.edges.every(
      (e) =>
        object(e) &&
        str(e.source) &&
        str(e.target) &&
        ["confirmed", "possible"].includes(e.kind),
    ) ||
    !c.allocations.every(
      (a) =>
        object(a) &&
        str(a.order_id) &&
        str(a.pool_id) &&
        integer(a.units) &&
        str(a.row_id) &&
        str(a.due_date) &&
        str(a.status),
    ) ||
    !c.history.every(
      (h) =>
        object(h) &&
        str(h.at) &&
        str(h.type) &&
        str(h.message) &&
        (h.lot_ids === undefined || strings(h.lot_ids)) &&
        (h.previous_lots === undefined || strings(h.previous_lots)) &&
        (h.suggested_lots === undefined || strings(h.suggested_lots)),
    ) ||
    !c.reviews.every(
      (r) =>
        object(r) &&
        str(r.at) &&
        strings(r.accepted_lots) &&
        strings(r.suggested_lots) &&
        strings(r.previous_lots) &&
        str(r.note),
    ) ||
    !c.runs.every(
      (r) =>
        object(r) &&
        str(r.id) &&
        str(r.mode) &&
        str(r.status) &&
        // Evolus does not return a runtime model ID. Explicit unknown is valid
        // historical provenance, never model verification or action authority.
        (r.model_id === undefined || r.model_id === null || str(r.model_id)) &&
        (r.error === undefined || str(r.error)),
    ) ||
    !c.receipts.every(
      (r) =>
        object(r) &&
        str(r.transaction_id) &&
        str(r.plan_id) &&
        str(r.at) &&
        integer(r.evidence_revision) &&
        integer(r.prior_inventory_version) &&
        integer(r.current_inventory_version) &&
        Array.isArray(r.changes) &&
        r.changes.every(
          (x) =>
            object(x) &&
            str(x.pool_id) &&
            integer(x.units) &&
            str(x.before) &&
            x.after === "held",
        ),
    ) ||
    !plan(c.plan) ||
    !c.plans.every(plan)
  )
    throw Error("Invalid decision packet schema");
  if (
    c.stocks.length > 500 ||
    c.edges.length > 500 ||
    c.allocations.length > 500
  )
    throw Error("Invalid packet record limits");
  const ids = new Set(c.stocks.map((s) => s.id)),
    sources = new Set(c.edges.map((e) => e.source));
  if (
    ids.size !== c.stocks.length ||
    c.edges.some(
      (e) =>
        ids.has(e.source) || (!ids.has(e.target) && !sources.has(e.target)),
    )
  )
    throw Error("Invalid packet lineage references");
  const visited = new Set(),
    active = new Set();
  function visit(id) {
    if (active.has(id)) throw Error("Invalid packet lineage cycle");
    if (visited.has(id)) return;
    active.add(id);
    for (const e of c.edges.filter((e) => e.source === id)) visit(e.target);
    active.delete(id);
    visited.add(id);
  }
  for (const id of sources) visit(id);
}
