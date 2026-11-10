import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { QueryState } from "@/components/query-state";
import { ROUTES } from "@/constants/routes";
import { getErrorMessage } from "@/features/auth/utils/form-errors";
import { useCurrentStore } from "@/features/stores/api/stores.api";
import { ApiError } from "@/lib/api";

/**
 * Store-workspace guard for pages that list store-scoped records.
 *
 * `gate` is what the page renders instead of its content: a redirect to
 * onboarding when the seller has no store yet (404), or an error with retry.
 * Call it before other hooks' results are used, then `if (gate) return gate;`.
 */
export function useStoreGate() {
  const storeQuery = useCurrentStore();
  const store = storeQuery.data;

  let gate: ReactNode = null;
  if (storeQuery.isError) {
    const noStoreYet =
      storeQuery.error instanceof ApiError && storeQuery.error.status === 404;
    gate = noStoreYet ? (
      <Navigate to={ROUTES.stores.onboarding()} replace />
    ) : (
      <QueryState
        isLoading={false}
        isError
        errorMessage={getErrorMessage(
          storeQuery.error,
          "Failed to load your store workspace.",
        )}
        onRetry={() => {
          void storeQuery.refetch();
        }}
      >
        {null}
      </QueryState>
    );
  }

  return {
    store,
    storeReady: Boolean(store),
    isStoreLoading: storeQuery.isLoading && !store,
    gate,
  };
}
