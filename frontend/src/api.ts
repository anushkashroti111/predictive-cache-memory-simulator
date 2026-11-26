export type Workload = "random" | "looping" | "zipfian";

export interface HashItem {
  item: string;
  frequency: number;
  last_accessed: number;
  heap_index: number;
}

export interface HashBucket {
  index: number;
  items: HashItem[];
}

export interface HashTable {
  bucket_count: number;
  unique_items: number;
  focus_bucket: number | null;
  stats: { unique_urls: number; buckets: number; avg_chain: number; max_chain: number; empty_buckets: number };
  buckets: HashBucket[];
}

export interface HeapNode {
  item: string;
  frequency: number;
  last_accessed: number;
  index: number;
  parent: number | null;
  left: number | null;
  right: number | null;
  is_root: boolean;
  is_updated: boolean;
}

export interface Snapshot {
  step: number;
  incoming: string;
  predicted: string | null;
  actual: string;
  correct: boolean | null;
  bucket: number;
  lookup: string;
  collision: boolean;
  updated_frequency?: number;
  updated_timestamp?: number;
  swapped_indices?: number[];
  hash_table: HashTable;
  heap: { nodes: HeapNode[]; root: string | null };
}

export interface TopItem {
  rank: number;
  item: string;
  frequency: number;
  last_accessed: number;
}

export interface SimulationResult {
  workload: Workload;
  seed: number;
  input_accesses: number;
  unique_urls: number;
  total_steps: number;
  evaluated_predictions: number;
  hits: number;
  misses: number;
  accuracy: number;
  latency_ms: number;
  top_k: TopItem[];
  top_3_pages: string[];
  hash_table: HashTable;
  heap: { nodes: HeapNode[]; root: string | null };
  snapshots: Snapshot[];
}

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function runSimulation(body: {
  workload: Workload;
  size: number;
  seed: number;
  top_k: number;
  snapshot_limit: number;
}) {
  const response = await fetch(`${API_BASE}/api/simulation/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error((await response.json()).detail || "Simulation failed");
  return response.json() as Promise<SimulationResult>;
}

export async function compareSimulation(body: { size: number; seed: number; top_k: number }) {
  const response = await fetch(`${API_BASE}/api/simulation/compare`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error("Comparison failed");
  return response.json() as Promise<Record<Workload, SimulationResult>>;
}
