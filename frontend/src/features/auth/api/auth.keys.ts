import type { AdminUserListParams } from "@/features/auth/types";

export const AUTH_QUERY_KEYS = {
  all: ["auth"] as const,
  session: () => [...AUTH_QUERY_KEYS.all, "session"] as const,
};

/**
 * Deliberately not under "auth": clearing a session keeps `auth` queries, but the
 * platform user list must be dropped on sign-out.
 */
export const ADMIN_USER_QUERY_KEYS = {
  all: ["admin-users"] as const,
  list: (params: AdminUserListParams) =>
    [...ADMIN_USER_QUERY_KEYS.all, params] as const,
};
