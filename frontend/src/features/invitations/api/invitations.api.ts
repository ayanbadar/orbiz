import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/features/auth/context/use-auth";
import { INVITATION_QUERY_KEYS } from "@/features/invitations/api/invitations.keys";
import { InvitationService } from "@/features/invitations/api/invitations.service";
import type {
  AcceptInvitationRequest,
  InviteStaffRequest,
  InviteStoreAdminRequest,
} from "@/features/invitations/types";

export function useStaffInvitations(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: INVITATION_QUERY_KEYS.staff(),
    queryFn: () => InvitationService.listStaff(),
    enabled: options?.enabled ?? true,
  });
}

export function useStoreAdminInvitations() {
  return useQuery({
    queryKey: INVITATION_QUERY_KEYS.storeAdmins(),
    queryFn: () => InvitationService.listStoreAdmins(),
  });
}

function useInvalidateInvitations() {
  const queryClient = useQueryClient();
  return () =>
    queryClient.invalidateQueries({ queryKey: INVITATION_QUERY_KEYS.all });
}

export function useInviteStaff() {
  const invalidate = useInvalidateInvitations();
  return useMutation({
    mutationFn: (body: InviteStaffRequest) =>
      InvitationService.inviteStaff(body),
    onSuccess: invalidate,
  });
}

export function useRevokeStaffInvitation() {
  const invalidate = useInvalidateInvitations();
  return useMutation({
    mutationFn: (id: number) => InvitationService.revokeStaff(id),
    onSuccess: invalidate,
  });
}

export function useInviteStoreAdmin() {
  const invalidate = useInvalidateInvitations();
  return useMutation({
    mutationFn: (body: InviteStoreAdminRequest) =>
      InvitationService.inviteStoreAdmin(body),
    onSuccess: invalidate,
  });
}

export function useRevokeStoreAdminInvitation() {
  const invalidate = useInvalidateInvitations();
  return useMutation({
    mutationFn: (id: number) => InvitationService.revokeStoreAdmin(id),
    onSuccess: invalidate,
  });
}

export function useInvitationPreview(token: string | null) {
  return useQuery({
    queryKey: INVITATION_QUERY_KEYS.preview(token),
    queryFn: () => InvitationService.preview(token as string),
    enabled: Boolean(token),
    retry: false,
  });
}

export function useAcceptInvitation(token: string) {
  const { setSession } = useAuth();
  return useMutation({
    mutationFn: (body: AcceptInvitationRequest) =>
      InvitationService.accept(token, body),
    onSuccess: (session) => setSession(session),
  });
}
