import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { AuthLoading } from "@/features/auth/components/auth-loading";
import { useAuth } from "@/features/auth/context/use-auth";
import { ROUTES } from "@/constants/routes";

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
    return <Navigate to={ROUTES.products.root()} replace />;
  }

  return children;
}

export function HomeRedirect() {
  const { status } = useAuth();

  if (status === "loading") {
    return <AuthLoading />;
  }

  return (
    <Navigate
      to={status === "authenticated" ? ROUTES.products.root() : ROUTES.signIn()}
      replace
    />
  );
}
