import { MutationCache, QueryCache, QueryClient } from "@tanstack/react-query";

import { STORE_QUERY_KEYS } from "@/features/stores/api/stores.keys";
import { ApiError } from "@/lib/api";

/** API codes meaning "this store can't be used right now" (see backend permissions.py). */
const BLOCKED_CODES = new Set(["store_suspended", "payment_required"]);

/**
 * When any call reports a blocked store, refresh the store so the route gates
 * immediately show the right notice instead of a page full of errors.
 */
function onApiError(error: unknown) {
  if (
    error instanceof ApiError &&
    error.code &&
    BLOCKED_CODES.has(error.code)
  ) {
    void queryClient.invalidateQueries({ queryKey: STORE_QUERY_KEYS.me() });
  }
}

export const queryClient: QueryClient = new QueryClient({
  queryCache: new QueryCache({ onError: onApiError }),
  mutationCache: new MutationCache({ onError: onApiError }),
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      gcTime: 5 * 60_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 0,
    },
  },
});
