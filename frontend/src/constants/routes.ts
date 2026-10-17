import { joinPath } from "@/utils";

/**
 * Centralized route definitions.
 * Always generate routes through these helpers — never hardcode path strings.
 */
export const ROUTES = {
  root: () => "/",

  demo: {
    root: () => joinPath(ROUTES.root(), "demo"),
  },
} as const;
