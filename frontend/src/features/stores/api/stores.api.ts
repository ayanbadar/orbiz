import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { STORE_QUERY_KEYS } from "@/features/stores/api/stores.keys";
import { StoreService } from "@/features/stores/api/stores.service";
import type { StoreCreateRequest } from "@/features/stores/types";
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
