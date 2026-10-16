export type Evidence = { document_id: string; block_id: string; quote: string };
export type Document = {
  id: string;
  filename: string;
  revision: number;
  media_type: string;
  synthetic: boolean;
  blocks: { id: string; text: string }[];
  original_hash: string;
  text_hash: string;
};
export type Stock = {
  id: string;
  units: number;
  unit_cents: number;
  status: string;
  complete: boolean;
  row_id: string;
  site: string;
};
export type Row = Stock & {
  classification: "documented" | "uncertain" | "outside";
  reason: string;
  path: string[];
  evidence: Evidence[];
};
export type Action = { type: "hold"; pool_id: string };
export type Result = {
  rows: Row[];
  documented_units: number;
  uncertain_units: number;
  hold_units: number;
  outside_units: number;
  broad_units: number;
  hold_cents: number;
  broad_cents: number;
  excluded_cents: number;
  reduction_percent: number;
  actions: Action[];
  requests: {
    id: string;
    pool_ids: string[];
    units: number;
    value_cents: number;
    missing: string;
    reason: string;
    draft: string;
  }[];
  request_unique_units: number;
  request_unique_cents: number;
  orders: {
    order_id: string;
    due_date: string;
    pool_ids: string[];
    units: number;
    reason: string;
    source_rows: string[];
  }[];
  shipment_reviews: string[];
  narrowing_available: boolean;
};
export type Run = {
  id: string;
  mode: string;
  status: string;
  revision: number;
  document_id: string;
  provider?: string;
  model_id?: string;
  elapsed_ms?: number;
  error?: string;
  output?: {
    facts: { lot_id: string; affected: boolean; evidence: Evidence[] }[];
    qualifiers: string[];
  };
};
export type Plan = {
  id: string;
  digest: string;
  status: string;
  revision: number;
  actions: Action[];
  result: Result;
};
export type Receipt = {
  transaction_id: string;
  at: string;
  plan_id: string;
  evidence_revision: number;
  prior_inventory_version: number;
  current_inventory_version: number;
  changes: { pool_id: string; units: number; before: string; after: string }[];
};
export type Case = {
  id: string;
  name: string;
  incident: string;
  synthetic: boolean;
  revision: number;
  inventory_version: number;
  documents: Document[];
  stocks: Stock[];
  edges: { source: string; target: string; kind: string; evidence: Evidence }[];
  scope: { lot_ids: string[]; revision: number };
  bounded: boolean;
  policy: { id: string; rule: string };
  runs: Run[];
  reviews: {
    at: string;
    suggested_lots: string[];
    accepted_lots: string[];
    previous_lots: string[];
    note: string;
  }[];
  plan: Plan | null;
  plans: Plan[];
  pending_revision: boolean;
  pending_data: unknown;
  receipts: Receipt[];
  history: {
    at: string;
    type: string;
    message: string;
    revision: number;
    previous_lots?: string[];
    suggested_lots?: string[];
    lot_ids?: string[];
    old_units?: number;
    new_units?: number;
  }[];
};
export type Packet = {
  schema_version: 1;
  exported_at: string;
  label: string;
  case: Case;
  integrity_hash: string;
};
export type Upload = {
  filename: string;
  content_base64: string;
  synthetic?: boolean;
};
export type Bridge = {
  platform: string;
  request: (
    method: "GET" | "POST",
    route: string,
    body?: unknown,
  ) => Promise<unknown>;
  chooseFiles: () => Promise<Upload[]>;
  savePacket: (p: Packet) => Promise<boolean>;
  openPacket: () => Promise<Packet | null>;
};
declare global {
  interface Window {
    batchfence?: Bridge;
  }
}
