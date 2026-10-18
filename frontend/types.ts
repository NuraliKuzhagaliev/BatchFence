export type Evidence = { document_id: string; block_id: string; quote: string };
export type Document = {
  evidence_language?: string;
  language_review_required?: boolean;
  ocr?: {
    engine: string;
    critical_fields_confirmed: boolean;
    pages: { page: number; image_hash: string }[];
  };
  request_id?: string;
  request_snapshot?: Question;
  id: string;
  filename: string;
  revision: number;
  media_type: string;
  synthetic: boolean;
  blocks: { id: string; text: string; page?: number }[];
  original_hash: string;
  text_hash: string;
};
export type Stock = {
  product_family?: string;
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
  node_states?: Record<string, "documented" | "uncertain" | "outside">;
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
  requests: Question[];
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
export type Hypothesis = {
  kind: "identity" | "boundary" | "inconclusive";
  pool_id?: string;
  supplier_lot_id?: string;
  complete?: boolean;
  lot_ids?: string[];
  uncertain_lot_ids?: string[];
};
export type Question = {
  id: string;
  pool_ids: string[];
  units: number;
  value_cents: number;
  missing: string;
  reason: string;
  draft: string;
  kind?: string;
  evidence?: Evidence[];
  suggested_role?: string;
  review_existing_first?: boolean;
  global?: boolean;
  hypotheses?: Hypothesis[];
  impact_note?: string;
  sort_reason?: string;
};
export type Simulation = {
  label: string;
  before: Result;
  after: Result;
  changed_units: number;
  changed_value_cents: number;
  changed_pool_ids: string[];
  new_order_reviews: string[];
  removed_order_reviews: string[];
  applied_hold_units: number;
  warning: string;
  remaining_blockers: Question[];
};
export type Run = {
  timestamp?: string;
  clock_source?: string;
  prompt_version?: string;
  schema_version?: number;
  usage?: Record<string, unknown>;
  request_id?: string;
  http_status?: number;
  input_hash?: string;
  id: string;
  mode: string;
  status: string;
  revision: number;
  document_id: string;
  provider?: string;
  model_id?: string;
  elapsed_ms?: number;
  error?: string;
  scope_concerns?: Evidence[];
  validated_proposals?: {
    facts: { lot_id: string; status: string }[];
    scope_status: string;
  };
  output?: {
    facts: {
      lot_id: string;
      affected: boolean;
      proposal_disposition?: string;
      proposal_incident_status?: string;
      evidence: Evidence[];
    }[];
    qualifiers: string[];
  };
};
export type Plan = {
  inputs?: {
    lineage: Case["edges"];
    stocks: Stock[];
    reviewed_scope: Case["scope"];
  };
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
  enterprise_packet?: Record<string, any>;
  enterprise_example?: boolean;
  procedure_checks?: Record<string, any>[];
  receiving_runs?: Record<string, any>[];
  hold_ledger?: Record<string, any>[];
  recovery_receipts?: Record<string, any>[];
  quantities?: {
    applied_hold_units: number;
    recovery_pending_units: number;
    confirmed_recovery_units: number;
  };
  id: string;
  name: string;
  incident: string;
  synthetic: boolean;
  revision: number;
  inventory_version: number;
  documents: Document[];
  stocks: Stock[];
  edges: { source: string; target: string; kind: string; evidence: Evidence }[];
  scope: {
    lot_ids: string[];
    revision: number;
    uncertain_lot_ids?: string[];
    excluded_lot_ids?: string[];
    incident_scope_status?: "unresolved" | "resolved";
  };
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
  openWebApp: () => Promise<void>;
  request: (
    method: "GET" | "POST",
    route: string,
    body?: unknown,
    accessToken?: string,
  ) => Promise<unknown>;
  chooseFiles: () => Promise<Upload[]>;
  chooseImages: () => Promise<Upload[]>;
  savePacket: (p: Packet) => Promise<boolean>;
  openPacket: () => Promise<Packet | null>;
  copyDraft: (draft: string) => Promise<void>;
};
declare global {
  interface Window {
    batchfence?: Bridge;
  }
}
