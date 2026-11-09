import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { TEAM_QUERY_KEYS } from "@/features/team/api/team.keys";
import { TeamService } from "@/features/team/api/team.service";
import type {
  MemberListParams,
  RoleRequest,
  UpdateMemberRequest,
} from "@/features/team/types";

export function useTeamUsers(params: MemberListParams) {
  return useQuery({
    queryKey: TEAM_QUERY_KEYS.users(params),
    queryFn: () => TeamService.listUsers(params),
    placeholderData: keepPreviousData,
  });
}

export function useRoles(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: TEAM_QUERY_KEYS.roles(),
    queryFn: () => TeamService.listRoles(),
    enabled: options?.enabled ?? true,
  });
}

export function usePermissionCatalog() {
  return useQuery({
    queryKey: TEAM_QUERY_KEYS.permissions(),
    queryFn: () => TeamService.permissionCatalog(),
    staleTime: Infinity,
  });
}

/** Every team mutation can change users and role member counts. */
function useInvalidateTeam() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: TEAM_QUERY_KEYS.all });
}

export function useUpdateMember() {
  const invalidate = useInvalidateTeam();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: UpdateMemberRequest }) =>
      TeamService.updateUser(id, body),
    onSuccess: invalidate,
  });
}

export function useDeleteMember() {
  const invalidate = useInvalidateTeam();
  return useMutation({
    mutationFn: (id: number) => TeamService.deleteUser(id),
    onSuccess: invalidate,
  });
}

export function useSaveRole() {
  const invalidate = useInvalidateTeam();
  return useMutation({
    mutationFn: ({ id, body }: { id?: number; body: RoleRequest }) =>
      id == null
        ? TeamService.createRole(body)
        : TeamService.updateRole(id, body),
    onSuccess: invalidate,
  });
}

export function useDeleteRole() {
  const invalidate = useInvalidateTeam();
  return useMutation({
    mutationFn: (id: number) => TeamService.deleteRole(id),
    onSuccess: invalidate,
  });
}
