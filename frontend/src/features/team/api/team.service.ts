import type {
  Member,
  MemberListParams,
  Paginated,
  PermissionCatalog,
  Role,
  RoleRequest,
  UpdateMemberRequest,
} from "@/features/team/types";
import { api } from "@/lib/api";

const ROOT = "/api/v1/team";

export class TeamService {
  static async listUsers(params: MemberListParams): Promise<Paginated<Member>> {
    const response = await api.get<Paginated<Member>>(`${ROOT}/users/`, {
      params: {
        page: params.page,
        search: params.search || undefined,
        is_active: params.is_active,
      },
    });
    return response.data;
  }

  static async updateUser(
    id: number,
    body: UpdateMemberRequest,
  ): Promise<Member> {
    const response = await api.patch<Member>(`${ROOT}/users/${id}/`, body);
    return response.data;
  }

  static async deleteUser(id: number): Promise<void> {
    await api.delete(`${ROOT}/users/${id}/`);
  }

  static async listRoles(): Promise<Role[]> {
    const response = await api.get<Role[]>(`${ROOT}/roles/`);
    return response.data;
  }

  static async createRole(body: RoleRequest): Promise<Role> {
    const response = await api.post<Role>(`${ROOT}/roles/`, body);
    return response.data;
  }

  static async updateRole(
    id: number,
    body: Partial<RoleRequest>,
  ): Promise<Role> {
    const response = await api.patch<Role>(`${ROOT}/roles/${id}/`, body);
    return response.data;
  }

  static async deleteRole(id: number): Promise<void> {
    await api.delete(`${ROOT}/roles/${id}/`);
  }

  static async permissionCatalog(): Promise<PermissionCatalog> {
    const response = await api.get<PermissionCatalog>(`${ROOT}/permissions/`);
    return response.data;
  }
}
