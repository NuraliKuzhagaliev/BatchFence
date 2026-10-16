import type { Packet, Upload } from "./types";
import { validateShape } from "../desktop/packet-shape.mjs";
export const native = window.batchfence;
export async function copyDraft(text: string) {
  if (native) await native.copyDraft(text);
  else await navigator.clipboard.writeText(text);
}
export async function request<T>(
  method: "GET" | "POST",
  route: string,
  body?: unknown,
): Promise<T> {
  if (native) return (await native.request(method, route, body)) as T;
  const response = await fetch(route, {
    method,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  const json = await response.json();
  if (!response.ok)
    throw Error(
      json.detail?.message || json.detail?.[0]?.msg || "Request failed",
    );
  return json as T;
}
export async function savePacket(p: Packet) {
  if (native) return native.savePacket(p);
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(p, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = "BatchFence-decision.json";
  a.click();
  URL.revokeObjectURL(url);
  return true;
}
export async function fileUpload(f: File): Promise<Upload> {
  if (f.size > 2000000) throw Error("File limit is 2 MB");
  const bytes = new Uint8Array(await f.arrayBuffer());
  let binary = "";
  for (let i = 0; i < bytes.length; i += 8192)
    binary += String.fromCharCode(...bytes.subarray(i, i + 8192));
  return { filename: f.name, content_base64: btoa(binary) };
}
function canonical(v: unknown): string {
  if (Array.isArray(v)) return "[" + v.map(canonical).join(",") + "]";
  if (v && typeof v === "object")
    return (
      "{" +
      Object.keys(v)
        .sort()
        .map(
          (k) =>
            JSON.stringify(k) +
            ":" +
            canonical((v as Record<string, unknown>)[k]),
        )
        .join(",") +
      "}"
    );
  return JSON.stringify(v);
}
export async function validatePacket(v: unknown): Promise<Packet> {
  validateShape(v);
  const p = v as Packet;
  if (
    !p ||
    p.schema_version !== 1 ||
    !p.case ||
    typeof p.case.name !== "string" ||
    !p.case.scope ||
    !Array.isArray(p.case.scope.lot_ids) ||
    !p.case.policy ||
    JSON.stringify(p).length > 6000000 ||
    ![
      "documents",
      "stocks",
      "edges",
      "allocations",
      "reviews",
      "runs",
      "receipts",
      "history",
    ].every((k) =>
      Array.isArray((p.case as unknown as Record<string, unknown>)[k]),
    ) ||
    p.case.documents.some(
      (d) =>
        !Array.isArray(d.blocks) ||
        typeof d.filename !== "string" ||
        d.blocks.some((b) => typeof b.text !== "string"),
    ) ||
    p.case.stocks.some(
      (s) =>
        typeof s.id !== "string" ||
        !Number.isSafeInteger(s.units) ||
        s.units < 0 ||
        !Number.isSafeInteger(s.unit_cents) ||
        s.unit_cents < 0,
    ) ||
    (p.case.plan &&
      (!p.case.plan.result || !Array.isArray(p.case.plan.result.rows)))
  )
    throw Error("Invalid decision packet schema");
  const hash = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(canonical(p.case)),
  );
  if (
    Array.from(new Uint8Array(hash))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("") !== p.integrity_hash
  )
    throw Error("Packet content changed; integrity hash does not match");
  return p;
}
