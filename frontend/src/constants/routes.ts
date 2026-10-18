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

  demo: {
    root: () => joinPath(ROUTES.root(), "demo"),
  },
} as const;
