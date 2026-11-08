import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { STORE_QUERY_KEYS } from "@/features/stores/api/stores.keys";
import { StoreService } from "@/features/stores/api/stores.service";
import { ADMIN_USER_QUERY_KEYS } from "@/features/auth/api/auth.keys";
import type {
  AdminStoreListParams,
  AdminStoreUpdateRequest,
  StoreCreateRequest,
  StoreUpdateRequest,
} from "@/features/stores/types";
import { ApiError } from "@/lib/api";

export function useStores() {
  return useQuery({
    queryKey: STORE_QUERY_KEYS.list(),
    queryFn: () => StoreService.list(),
  });
}

export function useCurrentStore(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: STORE_QUERY_KEYS.me(),
    queryFn: () => StoreService.me(),
    enabled: options?.enabled ?? true,
    // A 404 means "no store yet" — a valid, settled answer. Without this, every
    // observer that mounts re-fetches the errored query (see StoreGate loop).
    retryOnMount: false,
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.status === 404) {
        return false;
      }
      return failureCount < 2;
    },
  });
}

export function useCreateStore() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: StoreCreateRequest) => StoreService.create(body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: STORE_QUERY_KEYS.all });
    },
  });
}

export function useUpdateStore(storeId: number | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: StoreUpdateRequest) => {
      if (storeId == null) {
        throw new Error("Store id is required.");
      }
      return StoreService.update(storeId, body);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: STORE_QUERY_KEYS.all });
    },
  });
}

export function useAdminStores(params: AdminStoreListParams) {
  return useQuery({
    queryKey: STORE_QUERY_KEYS.admin(params),
    queryFn: () => StoreService.listAdmin(params),
    placeholderData: keepPreviousData,
  });
}

/** Changing a store's state also changes how its users appear in the platform user list. */
function useInvalidateAfterAdminStoreChange() {
  const queryClient = useQueryClient();
  return async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: STORE_QUERY_KEYS.all }),
      queryClient.invalidateQueries({ queryKey: ADMIN_USER_QUERY_KEYS.all }),
    ]);
  };
}

export function useUpdateAdminStore() {
  const invalidate = useInvalidateAfterAdminStoreChange();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: AdminStoreUpdateRequest }) =>
      StoreService.updateAdmin(id, body),
    onSuccess: invalidate,
  });
}

export function useDeleteAdminStore() {
  const invalidate = useInvalidateAfterAdminStoreChange();
  return useMutation({
    mutationFn: (id: number) => StoreService.deleteAdmin(id),
    onSuccess: invalidate,
  });
}
