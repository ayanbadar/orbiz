export const BILLING_QUERY_KEYS = {
  all: ["billing"] as const,
  status: () => [...BILLING_QUERY_KEYS.all, "status"] as const,
};
