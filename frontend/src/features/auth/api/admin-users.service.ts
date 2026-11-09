import type {
  AdminUserListParams,
  AdminUserUpdateRequest,
} from "@/features/auth/types";
import type { Member, Paginated } from "@/features/team/types";
import { api } from "@/lib/api";

const ROOT = "/api/v1/admin/users";

/** Platform admin: every user account across all stores. */
export class AdminUserService {
  static async list(params: AdminUserListParams): Promise<Paginated<Member>> {
    const response = await api.get<Paginated<Member>>(`${ROOT}/`, {
      params: {
        page: params.page,
        search: params.search || undefined,
        store: params.store,
        is_active: params.is_active,
      },
    });
    return response.data;
  }

  static async update(
    id: number,
    body: AdminUserUpdateRequest,
  ): Promise<Member> {
    const response = await api.patch<Member>(`${ROOT}/${id}/`, body);
    return response.data;
  }

  static async remove(id: number): Promise<void> {
    await api.delete(`${ROOT}/${id}/`);
  }
}
