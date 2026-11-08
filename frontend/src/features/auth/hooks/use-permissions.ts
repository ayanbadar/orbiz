import { useCallback, useMemo } from "react";

import { useAuth } from "@/features/auth/context/use-auth";
import { useCurrentStore } from "@/features/stores/api/stores.api";

/**
 * What the signed-in user may do. The server is the source of truth and enforces
 * every rule; this only decides what to show.
 *
 * Platform admins have no store, so `can()` is false for them (they use /admin).
 */
export function usePermissions() {
  const { user } = useAuth();
  const storeQuery = useCurrentStore({
    enabled: user?.is_superuser !== true,
  });
  const store = storeQuery.data;

  const permissions = useMemo(
    () => new Set(store?.permissions ?? []),
    [store?.permissions],
  );

  const can = useCallback(
    (permission: string) =>
      store?.is_store_admin === true || permissions.has(permission),
    [permissions, store?.is_store_admin],
  );

  return {
    can,
    isPlatformAdmin: user?.is_superuser === true,
    isStoreAdmin: store?.is_store_admin === true,
    store,
    isLoading: storeQuery.isLoading,
  };
}
