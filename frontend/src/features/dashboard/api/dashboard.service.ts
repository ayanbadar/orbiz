import type {
  DashboardRange,
  PlatformDashboard,
  StoreDashboard,
} from "@/features/dashboard/types";
import { api } from "@/lib/api";

export class DashboardService {
  static async store(range: DashboardRange): Promise<StoreDashboard> {
    const response = await api.get<StoreDashboard>(
      "/api/v1/dashboard/summary/",
      { params: { range } },
    );
    return response.data;
  }

  static async platform(range: DashboardRange): Promise<PlatformDashboard> {
    const response = await api.get<PlatformDashboard>(
      "/api/v1/admin/dashboard/summary/",
      { params: { range } },
    );
    return response.data;
  }
}
