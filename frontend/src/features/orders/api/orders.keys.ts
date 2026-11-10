import type { OrderListParams } from "@/features/orders/types";

export const ORDER_QUERY_KEYS = {
  all: ["orders"] as const,
  list: (params: OrderListParams) =>
    [...ORDER_QUERY_KEYS.all, "list", params] as const,
  detail: (id: number) => [...ORDER_QUERY_KEYS.all, "detail", id] as const,
};
