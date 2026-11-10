import axios from "axios";

import {
  clearTokens,
  getRefreshToken,
  SESSION_EXPIRED_EVENT,
  setTokens,
} from "@/lib/auth-token";
import { env } from "@/lib/env";

type RefreshResponse = {
  access: string;
  refresh?: string;
};

let refreshPromise: Promise<string | null> | null = null;

async function requestNewAccess(): Promise<string | null> {
  const refresh = getRefreshToken();
  if (!refresh) {
    return null;
  }

  try {
    const response = await axios.post<RefreshResponse>(
      `${env.VITE_API_URL}/api/v1/auth/token/refresh/`,
      { refresh },
      {
        headers: { "Content-Type": "application/json" },
        timeout: 30_000,
      },
    );
    const access = response.data.access;
    setTokens(access, response.data.refresh ?? refresh);
    return access;
  } catch {
    clearTokens();
    window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
    return null;
  }
}

export function refreshAccessToken(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = requestNewAccess().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}
