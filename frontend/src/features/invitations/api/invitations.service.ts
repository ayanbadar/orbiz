import type { AuthSession } from "@/features/auth/types";
import type {
  AcceptInvitationRequest,
  Invitation,
  InvitationPreview,
  InviteStaffRequest,
  InviteStoreAdminRequest,
} from "@/features/invitations/types";
import { api } from "@/lib/api";

const ROOT = "/api/v1/invitations";

export class InvitationService {
  // --- A store's own team ---
  static async listStaff(): Promise<Invitation[]> {
    const response = await api.get<Invitation[]>(`${ROOT}/`);
    return response.data;
  }

  static async inviteStaff(body: InviteStaffRequest): Promise<Invitation> {
    const response = await api.post<Invitation>(`${ROOT}/`, body);
    return response.data;
  }

  static async revokeStaff(id: number): Promise<void> {
    await api.delete(`${ROOT}/${id}/`);
  }

  // --- Platform admin: store admins ---
  static async listStoreAdmins(): Promise<Invitation[]> {
    const response = await api.get<Invitation[]>(`${ROOT}/store-admins/`);
    return response.data;
  }

  static async inviteStoreAdmin(
    body: InviteStoreAdminRequest,
  ): Promise<Invitation> {
    const response = await api.post<Invitation>(`${ROOT}/store-admins/`, body);
    return response.data;
  }

  static async revokeStoreAdmin(id: number): Promise<void> {
    await api.delete(`${ROOT}/store-admins/${id}/`);
  }

  // --- The invitee (public) ---
  static async preview(token: string): Promise<InvitationPreview> {
    const response = await api.get<InvitationPreview>(
      `${ROOT}/${encodeURIComponent(token)}/`,
    );
    return response.data;
  }

  static async accept(
    token: string,
    body: AcceptInvitationRequest,
  ): Promise<AuthSession> {
    const response = await api.post<AuthSession>(
      `${ROOT}/${encodeURIComponent(token)}/accept/`,
      body,
    );
    return response.data;
  }
}
