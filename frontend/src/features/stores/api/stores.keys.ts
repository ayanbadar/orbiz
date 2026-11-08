import type { AdminStoreListParams } from "@/features/stores/types";

export const STORE_QUERY_KEYS = {
  all: ["stores"] as const,
  list: () => [...STORE_QUERY_KEYS.all, "list"] as const,
  me: () => [...STORE_QUERY_KEYS.all, "me"] as const,
  admin: (params: AdminStoreListParams) =>
    [...STORE_QUERY_KEYS.all, "admin", params] as const,
  detail: (id: number) => [...STORE_QUERY_KEYS.all, "detail", id] as const,
};
