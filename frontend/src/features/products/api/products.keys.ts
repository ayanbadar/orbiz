import type { ProductListParams } from "@/features/products/types";

export const PRODUCT_QUERY_KEYS = {
  all: ["products"] as const,
  list: (params: ProductListParams) =>
    [...PRODUCT_QUERY_KEYS.all, "list", params] as const,
  detail: (id: number) => [...PRODUCT_QUERY_KEYS.all, "detail", id] as const,
  adjustments: (id: number) =>
    [...PRODUCT_QUERY_KEYS.all, "adjustments", id] as const,
};
