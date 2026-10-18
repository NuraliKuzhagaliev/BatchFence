const assert = require("node:assert/strict"),
  fs = require("node:fs");
const { validatePacket, canonical } = require("../desktop/packet.cjs");
const { createHash } = require("node:crypto");
const packet = JSON.parse(
  fs.readFileSync("docs/verified-decision-packet.json", "utf8"),
);
validatePacket(packet);
const unknownModel=structuredClone(packet);
unknownModel.case.runs[0].model_id=null;
unknownModel.integrity_hash=createHash('sha256').update(canonical(unknownModel.case)).digest('hex');
validatePacket(unknownModel);
unknownModel.case.runs[0].model_id={unverified:'not a model ID'};
unknownModel.integrity_hash=createHash('sha256').update(canonical(unknownModel.case)).digest('hex');
assert.throws(()=>validatePacket(unknownModel),/Invalid/);
for (const mutate of [
  (p) => {
    p.case.edges[0].kind = "release";
  },
  (p) => {
    p.case.stocks[0].complete = "false";
  },
  (p) => {
    p.case.documents[0].blocks[0].text = { html: "unsafe" };
  },
  (p) => {
    p.case.plan.result.rows[0].reason = { html: "unsafe" };
  },
  (p) => {
    p.case.edges.push(
      { source: "E1", target: "E2", kind: "confirmed" },
      { source: "E2", target: "E1", kind: "confirmed" },
    );
  },
]) {
  const copy = structuredClone(packet);
  mutate(copy);
  copy.integrity_hash = createHash("sha256")
    .update(canonical(copy.case))
    .digest("hex");
  assert.throws(() => validatePacket(copy), /Invalid/);
}
console.log(
  "Shared packet validation: valid historical packet accepted; 5 malformed/cyclic cases rejected even with recomputed hash.",
);
