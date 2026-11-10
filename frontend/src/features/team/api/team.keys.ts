import type { MemberListParams } from "@/features/team/types";

export const TEAM_QUERY_KEYS = {
  all: ["team"] as const,
  users: (params: MemberListParams) =>
    [...TEAM_QUERY_KEYS.all, "users", params] as const,
  roles: () => [...TEAM_QUERY_KEYS.all, "roles"] as const,
  permissions: () => [...TEAM_QUERY_KEYS.all, "permissions"] as const,
};
