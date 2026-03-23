/* React-Query hooks wrapping the migration API. */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { MigrationCreateRequest } from "../api/types";

export function useHealth() {
  return useQuery({ queryKey: ["health"], queryFn: api.health, refetchInterval: 30_000 });
}

export function useMigrations() {
  return useQuery({ queryKey: ["migrations"], queryFn: api.listMigrations, refetchInterval: 5_000 });
}

export function useMigration(id: string) {
  return useQuery({
    queryKey: ["migration", id],
    queryFn: () => api.getMigration(id),
    refetchInterval: 3_000,
  });
}

export function useInventory(id: string) {
  return useQuery({
    queryKey: ["inventory", id],
    queryFn: () => api.getInventory(id),
  });
}

export function useCreateMigration() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: MigrationCreateRequest) => api.createMigration(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["migrations"] }),
  });
}

export function useCancelMigration() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.cancelMigration(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["migrations"] }),
  });
}
