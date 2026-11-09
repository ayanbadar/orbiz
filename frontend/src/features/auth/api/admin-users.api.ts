import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { AdminUserService } from "@/features/auth/api/admin-users.service";
import { ADMIN_USER_QUERY_KEYS } from "@/features/auth/api/auth.keys";
import type {
  AdminUserListParams,
  AdminUserUpdateRequest,
} from "@/features/auth/types";
import { STORE_QUERY_KEYS } from "@/features/stores/api/stores.keys";

export function useAdminUsers(params: AdminUserListParams) {
  return useQuery({
    queryKey: ADMIN_USER_QUERY_KEYS.list(params),
    queryFn: () => AdminUserService.list(params),
    placeholderData: keepPreviousData,
  });
}

/** Deactivating a store admin suspends their store, so refresh the store list too. */
function useInvalidateAfterAdminUserChange() {
  const queryClient = useQueryClient();
  return async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ADMIN_USER_QUERY_KEYS.all }),
      queryClient.invalidateQueries({ queryKey: STORE_QUERY_KEYS.all }),
    ]);
  };
}

export function useUpdateAdminUser() {
  const invalidate = useInvalidateAfterAdminUserChange();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: AdminUserUpdateRequest }) =>
      AdminUserService.update(id, body),
    onSuccess: invalidate,
  });
}

export function useDeleteAdminUser() {
  const invalidate = useInvalidateAfterAdminUserChange();
  return useMutation({
    mutationFn: (id: number) => AdminUserService.remove(id),
    onSuccess: invalidate,
  });
}
