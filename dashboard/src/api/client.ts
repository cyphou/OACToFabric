/* HTTP client for the migration API.  All calls go through the Vite proxy (/api → backend). */

import type {
  Migration,
  MigrationCreateRequest,
  Inventory,
  Health,
} from "./types";

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<Health>("/health"),

  listMigrations: () => request<Migration[]>("/migrations"),

  getMigration: (id: string) => request<Migration>(`/migrations/${encodeURIComponent(id)}`),

  createMigration: (data: MigrationCreateRequest) =>
    request<Migration>("/migrations", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getInventory: (id: string) => request<Inventory>(`/migrations/${encodeURIComponent(id)}/inventory`),

  cancelMigration: (id: string) =>
    request<{ migration_id: string; cancelled: boolean; message: string }>(
      `/migrations/${encodeURIComponent(id)}/cancel`,
      { method: "POST" },
    ),
};
