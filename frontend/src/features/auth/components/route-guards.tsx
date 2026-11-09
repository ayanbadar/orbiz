import type { ReactNode } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import { ROUTES } from "@/constants/routes";
import { AccessBlocked } from "@/features/auth/components/access-blocked";
import { AppShell } from "@/features/auth/components/app-shell";
import { AuthLoading } from "@/features/auth/components/auth-loading";
import { useAuth } from "@/features/auth/context/use-auth";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { getHomeRoute } from "@/features/auth/utils/home-route";
import { useCurrentStore } from "@/features/stores/api/stores.api";
import { ApiError } from "@/lib/api";

export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "loading") {
    return <AuthLoading />;
  }

  if (status === "anonymous") {
    return (
      <Navigate
        to={ROUTES.signIn()}
        replace
        state={{ from: location.pathname }}
      />
    );
  }

  return children;
}

export function GuestOnly({ children }: { children: ReactNode }) {
  const { status } = useAuth();

  if (status === "loading") {
    return <AuthLoading />;
  }

  if (status === "authenticated") {
    return <Navigate to={ROUTES.root()} replace />;
  }

  return children;
}

/** "/" — send people to the first place they can actually use. */
export function HomeRedirect() {
  const { status, user } = useAuth();
  const isPlatformAdmin = user?.is_superuser === true;
  const storeQuery = useCurrentStore({
    enabled: status === "authenticated" && !isPlatformAdmin,
  });

  if (status === "loading") {
    return <AuthLoading />;
  }
  if (status === "anonymous") {
    return <Navigate to={ROUTES.signIn()} replace />;
  }
  if (isPlatformAdmin) {
    return <Navigate to={getHomeRoute({ isPlatformAdmin: true })} replace />;
  }
  if (storeQuery.isLoading) {
    return <AuthLoading />;
  }
  const store = storeQuery.data;
  if (!store) {
    // No workspace (or the store call is blocked): the account page always works.
    const missing =
      storeQuery.error instanceof ApiError && storeQuery.error.status === 404;
    return (
      <Navigate
        to={missing ? ROUTES.stores.onboarding() : ROUTES.account()}
        replace
      />
    );
  }
  return <Navigate to={getHomeRoute({ store })} replace />;
}

/**
 * Signed-in layout: auth check + app shell. Every protected page renders in the <Outlet />.
 */
export function ProtectedLayout() {
  return (
    <RequireAuth>
      <AppShell>
        <Outlet />
      </AppShell>
    </RequireAuth>
  );
}

/**
 * Gate for pages that need a usable store: shows a notice when it is suspended,
 * and sends unpaid store admins to billing. Pass `allowUnpaid` for billing/onboarding.
 */
export function StoreGate({ allowUnpaid = false }: { allowUnpaid?: boolean }) {
  const { user } = useAuth();
  const storeQuery = useCurrentStore({
    enabled: user?.is_superuser !== true,
  });
  const location = useLocation();

  if (user?.is_superuser) {
    return <Navigate to={ROUTES.admin.stores()} replace />;
  }
  if (storeQuery.isLoading) {
    return (
      <p className="text-sm text-muted-foreground" role="status">
        Loading…
      </p>
    );
  }
  if (storeQuery.error instanceof ApiError && storeQuery.error.status === 404) {
    return location.pathname === ROUTES.stores.onboarding() ? (
      <Outlet />
    ) : (
      <Navigate to={ROUTES.stores.onboarding()} replace />
    );
  }
  const store = storeQuery.data;
  if (!store) {
    return <AccessBlocked kind="forbidden" />;
  }
  if (store.status === "suspended") {
    return <AccessBlocked kind="suspended" />;
  }
  if (store.status === "pending_payment" && !allowUnpaid) {
    return store.is_store_admin ? (
      <Navigate to={ROUTES.billing()} replace />
    ) : (
      <AccessBlocked kind="unpaid" />
    );
  }
  return <Outlet />;
}

/** Page-level permission check (the API enforces it too). */
export function RequirePermission({ permission }: { permission: string }) {
  const { can, isLoading } = usePermissions();
  if (isLoading) {
    return (
      <p className="text-sm text-muted-foreground" role="status">
        Loading…
      </p>
    );
  }
  return can(permission) ? <Outlet /> : <AccessBlocked kind="forbidden" />;
}

export function RequireStoreAdmin() {
  const { isStoreAdmin, isLoading } = usePermissions();
  if (isLoading) {
    return (
      <p className="text-sm text-muted-foreground" role="status">
        Loading…
      </p>
    );
  }
  return isStoreAdmin ? <Outlet /> : <AccessBlocked kind="forbidden" />;
}

export function RequirePlatformAdmin() {
  const { user } = useAuth();
  return user?.is_superuser ? (
    <Outlet />
  ) : (
    <AccessBlocked kind="forbidden" />
  );
}
