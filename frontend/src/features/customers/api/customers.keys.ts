import type { CustomerListParams } from "@/features/customers/types";

export const CUSTOMER_QUERY_KEYS = {
  all: ["customers"] as const,
  list: (params: CustomerListParams) =>
    [...CUSTOMER_QUERY_KEYS.all, "list", params] as const,
  detail: (id: number) => [...CUSTOMER_QUERY_KEYS.all, "detail", id] as const,
};
