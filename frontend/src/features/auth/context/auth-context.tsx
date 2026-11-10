import { useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, type ReactNode } from "react";

import { AUTH_QUERY_KEYS } from "@/features/auth/api/auth.keys";
import { AuthService } from "@/features/auth/api/auth.service";
import {
  AuthContext,
  type AuthContextValue,
  type AuthStatus,
} from "@/features/auth/context/auth-state";
import type { AuthSession, UserProfile } from "@/features/auth/types";
import { refreshAccessToken } from "@/lib/auth-session";
import {
  clearTokens,
  getRefreshToken,
  SESSION_EXPIRED_EVENT,
  setTokens,
} from "@/lib/auth-token";
import { queryClient } from "@/lib/query-client";

async function loadSession(): Promise<UserProfile | null> {
  if (!getRefreshToken()) {
    return null;
  }

  const access = await refreshAccessToken();
  if (!access) {
    return null;
  }

  try {
    return await AuthService.me();
  } catch {
    clearTokens();
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const session = useQuery({
    queryKey: AUTH_QUERY_KEYS.session(),
    queryFn: loadSession,
    staleTime: Infinity,
    retry: false,
  });

  const setSession = useCallback((next: AuthSession) => {
    setTokens(next.access, next.refresh);
    queryClient.setQueryData(AUTH_QUERY_KEYS.session(), next.user);
  }, []);

  const clearSession = useCallback(() => {
    clearTokens();
    queryClient.setQueryData(AUTH_QUERY_KEYS.session(), null);
    queryClient.removeQueries({
      predicate: (query) => query.queryKey[0] !== "auth",
    });
  }, []);

  useEffect(() => {
    const onExpired = () => {
      clearSession();
    };
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired);
  }, [clearSession]);

  const value = useMemo<AuthContextValue>(() => {
    const status: AuthStatus = session.isPending
      ? "loading"
      : session.data
        ? "authenticated"
        : "anonymous";

    return {
      user: session.data ?? null,
      status,
      setSession,
      clearSession,
    };
  }, [session.data, session.isPending, setSession, clearSession]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
