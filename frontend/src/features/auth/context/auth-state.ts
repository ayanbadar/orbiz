import { createContext } from "react";

import type { AuthSession, UserProfile } from "@/features/auth/types";

export type AuthStatus = "loading" | "authenticated" | "anonymous";

export type AuthContextValue = {
  user: UserProfile | null;
  status: AuthStatus;
  setSession: (session: AuthSession) => void;
  clearSession: () => void;
};

export const AuthContext = createContext<AuthContextValue | null>(null);
