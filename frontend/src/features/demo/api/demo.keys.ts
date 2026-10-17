import type { GetDemoParams } from "@/features/demo/types";

export const DEMO_QUERY_KEYS = {
  all: ["demo"] as const,

  list: (params: GetDemoParams) =>
    [...DEMO_QUERY_KEYS.all, "list", params] as const,
};
