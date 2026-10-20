export const STORE_QUERY_KEYS = {
  all: ["stores"] as const,
  list: () => [...STORE_QUERY_KEYS.all, "list"] as const,
  me: () => [...STORE_QUERY_KEYS.all, "me"] as const,
  detail: (id: number) => [...STORE_QUERY_KEYS.all, "detail", id] as const,
};
