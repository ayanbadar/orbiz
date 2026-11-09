import type { DashboardRange } from "@/features/dashboard/types";

export const DASHBOARD_QUERY_KEYS = {
  all: ["dashboard"] as const,
  store: (range: DashboardRange) =>
    [...DASHBOARD_QUERY_KEYS.all, "store", range] as const,
  platform: (range: DashboardRange) =>
    [...DASHBOARD_QUERY_KEYS.all, "platform", range] as const,
};
