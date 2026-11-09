import { parseAsStringLiteral, useQueryState } from "nuqs";

import type { DashboardRange } from "@/features/dashboard/types";

export const DASHBOARD_RANGES = [
  "7d",
  "30d",
  "90d",
] as const satisfies readonly DashboardRange[];

/** Period kept in the URL (?range=) so a dashboard view can be shared or reloaded. */
export function useDashboardRange() {
  return useQueryState(
    "range",
    parseAsStringLiteral(DASHBOARD_RANGES).withDefault("30d"),
  );
}
