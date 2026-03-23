/* API type definitions matching the FastAPI backend models. */

export type MigrationMode = "full" | "incremental";

export type MigrationStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

export interface AgentStatus {
  agent_id: string;
  state: string;
  items_processed: number;
  items_failed: number;
  started_at: string | null;
  completed_at: string | null;
}

export interface Migration {
  id: string;
  name: string;
  status: MigrationStatus;
  mode: string;
  source_type: string;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  progress_pct: number;
  agents: AgentStatus[];
  total_items: number;
  succeeded_items: number;
  failed_items: number;
  error: string | null;
}

export interface MigrationCreateRequest {
  name: string;
  source_type: string;
  config: Record<string, unknown>;
  mode: MigrationMode;
  wave?: number | null;
  dry_run: boolean;
}

export interface InventoryItem {
  id: string;
  asset_type: string;
  name: string;
  source_path: string;
  complexity: string;
  migration_status: string;
}

export interface Inventory {
  migration_id: string;
  total: number;
  items: InventoryItem[];
}

export interface LogEntry {
  timestamp: string;
  level: string;
  agent_id: string;
  message: string;
}

export interface Health {
  status: string;
  version: string;
  uptime_seconds: number;
  migrations_active: number;
}

export interface WsEvent {
  type: string;
  [key: string]: unknown;
}
