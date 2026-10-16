const { createHash } = require("node:crypto");
function canonical(v) {
  if (Array.isArray(v)) return "[" + v.map(canonical).join(",") + "]";
  if (v && typeof v === "object")
    return (
      "{" +
      Object.keys(v)
        .sort()
        .map((k) => JSON.stringify(k) + ":" + canonical(v[k]))
        .join(",") +
      "}"
    );
  return JSON.stringify(v);
}
function validatePacket(packet) {
  if (
    !packet ||
    packet.schema_version !== 1 ||
    typeof packet.integrity_hash !== "string" ||
    !packet.case ||
    typeof packet.case.name !== "string" ||
    JSON.stringify(packet).length > 6000000
  )
    throw Error("Invalid or oversized decision packet");
  const c = packet.case;
  for (const k of [
    "documents",
    "stocks",
    "edges",
    "allocations",
    "reviews",
    "runs",
    "receipts",
    "history",
  ]) {
    if (!Array.isArray(c[k]) || c[k].length > 2000)
      throw Error("Packet schema is incomplete");
  }
  if (
    !c.scope ||
    !Array.isArray(c.scope.lot_ids) ||
    !c.policy ||
    c.documents.some(
      (d) =>
        typeof d.filename !== "string" ||
        !Array.isArray(d.blocks) ||
        d.blocks.some(
          (b) => typeof b.text !== "string" || typeof b.id !== "string",
        ),
    ) ||
    c.stocks.some(
      (s) =>
        typeof s.id !== "string" ||
        !Number.isSafeInteger(s.units) ||
        s.units < 0 ||
        !Number.isSafeInteger(s.unit_cents) ||
        s.unit_cents < 0,
    ) ||
    (c.plan && (!c.plan.result || !Array.isArray(c.plan.result.rows)))
  )
    throw Error("Packet schema is invalid");
  const hash = createHash("sha256").update(canonical(c)).digest("hex");
  if (hash !== packet.integrity_hash)
    throw Error(
      "Packet changed: integrity hash does not match. Hashes do not authenticate the supplier.",
    );
  return packet;
}
module.exports = { validatePacket, canonical };
