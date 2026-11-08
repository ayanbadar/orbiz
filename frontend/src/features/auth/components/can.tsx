import type { ReactNode } from "react";

import { usePermissions } from "@/features/auth/hooks/use-permissions";

/** Render children only when the user holds `permission` (e.g. "orders.update"). */
export function Can({
  permission,
  children,
  fallback = null,
}: {
  permission: string;
  children: ReactNode;
  fallback?: ReactNode;
}) {
  const { can } = usePermissions();
  return can(permission) ? children : fallback;
}
