import { ROUTES } from "@/constants/routes";
import type { Store } from "@/features/stores/types";

/** First page a user can use after signing in. */
export function getHomeRoute(
  args: { isPlatformAdmin: true } | { isPlatformAdmin?: false; store: Store },
): string {
  if (args.isPlatformAdmin) {
    return ROUTES.admin.stores();
  }
  const { store } = args;
  if (store.status === "pending_payment" && store.is_store_admin) {
    return ROUTES.billing();
  }
  const has = (code: string) =>
    store.is_store_admin || (store.permissions ?? []).includes(code);
  if (has("products.read")) return ROUTES.products.root();
  if (has("orders.read")) return ROUTES.orders.root();
  if (has("users.read")) return ROUTES.team.users();
  return ROUTES.account();
}
