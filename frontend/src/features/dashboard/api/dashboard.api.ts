import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { DASHBOARD_QUERY_KEYS } from "@/features/dashboard/api/dashboard.keys";
import { DashboardService } from "@/features/dashboard/api/dashboard.service";
import type { DashboardRange } from "@/features/dashboard/types";

export function useStoreDashboard(range: DashboardRange) {
  return useQuery({
    queryKey: DASHBOARD_QUERY_KEYS.store(range),
    queryFn: () => DashboardService.store(range),
    placeholderData: keepPreviousData,
  });
}

export function usePlatformDashboard(range: DashboardRange) {
  return useQuery({
    queryKey: DASHBOARD_QUERY_KEYS.platform(range),
    queryFn: () => DashboardService.platform(range),
    placeholderData: keepPreviousData,
  });
}
