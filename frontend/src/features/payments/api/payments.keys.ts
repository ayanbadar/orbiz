export const PAYMENT_QUERY_KEYS = {
  all: ["payments"] as const,
  checkout: (orderId: number) =>
    [...PAYMENT_QUERY_KEYS.all, "checkout", orderId] as const,
};
