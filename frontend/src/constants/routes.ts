import { joinPath } from "@/utils";

/**
 * Centralized route definitions.
 * Always generate routes through these helpers — never hardcode path strings.
 */
export const ROUTES = {
  root: () => "/",
  signIn: () => joinPath(ROUTES.root(), "sign-in"),
  signUp: () => joinPath(ROUTES.root(), "sign-up"),
  forgotPassword: () => joinPath(ROUTES.root(), "forgot-password"),
  resetPassword: () => joinPath(ROUTES.root(), "reset-password"),
  account: () => joinPath(ROUTES.root(), "account"),

  stores: {
    onboarding: () => joinPath(ROUTES.root(), "stores", "onboarding"),
  },

  products: {
    root: () => joinPath(ROUTES.root(), "products"),
    new: () => joinPath(ROUTES.products.root(), "new"),
    detail: (id: number | string) => joinPath(ROUTES.products.root(), String(id)),
    edit: (id: number | string) =>
      joinPath(ROUTES.products.root(), String(id), "edit"),
  },

  orders: {
    root: () => joinPath(ROUTES.root(), "orders"),
    new: () => joinPath(ROUTES.orders.root(), "new"),
    detail: (id: number | string) => joinPath(ROUTES.orders.root(), String(id)),
    edit: (id: number | string) =>
      joinPath(ROUTES.orders.root(), String(id), "edit"),
  },

  demo: {
    root: () => joinPath(ROUTES.root(), "demo"),
  },
} as const;
