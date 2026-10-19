import axios, {
  AxiosError,
  type AxiosInstance,
  type InternalAxiosRequestConfig,
} from "axios";

import { readApiErrorMessage } from "@/lib/api/errors";
import { refreshAccessToken } from "@/lib/auth-session";
import { getAccessToken } from "@/lib/auth-token";
import { env } from "@/lib/env";

export type { Paginated } from "@/lib/api/types";

const PUBLIC_AUTH_PATHS = [
  "/api/v1/auth/login/",
  "/api/v1/auth/register/",
  "/api/v1/auth/token/refresh/",
  "/api/v1/auth/forgot-password/",
  "/api/v1/auth/reset-password/",
];

type RetriableConfig = InternalAxiosRequestConfig & { _retry?: boolean };

export class ApiError extends Error {
  readonly status: number | undefined;
  readonly code: string | undefined;
  readonly details: unknown;

  constructor(
    message: string,
    options?: {
      status?: number;
      code?: string;
      details?: unknown;
      cause?: unknown;
    },
  ) {
    super(message, { cause: options?.cause });
    this.name = "ApiError";
    this.status = options?.status;
    this.code = options?.code;
    this.details = options?.details;
  }
}

function isPublicAuthRequest(url: string | undefined): boolean {
  if (!url) {
    return false;
  }
  return PUBLIC_AUTH_PATHS.some((path) => url.includes(path));
}

function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) {
    return error;
  }

  if (error instanceof AxiosError) {
    const status = error.response?.status;
    const data = error.response?.data as { code?: string } | undefined;

    return new ApiError(
      readApiErrorMessage(data) ?? error.message ?? "Request failed",
      {
        status,
        code: data?.code,
        details: data,
        cause: error,
      },
    );
  }

  if (error instanceof Error) {
    return new ApiError(error.message, { cause: error });
  }

  return new ApiError("An unexpected error occurred", { details: error });
}

function createApiClient(): AxiosInstance {
  const client = axios.create({
    baseURL: env.VITE_API_URL,
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    timeout: 30_000,
  });

  client.interceptors.request.use((config) => {
    const token = getAccessToken();
    if (token && !isPublicAuthRequest(config.url)) {
      config.headers.set("Authorization", `Bearer ${token}`);
    }
    return config;
  });

  client.interceptors.response.use(
    (response) => response,
    async (error: unknown) => {
      if (!(error instanceof AxiosError) || !error.config) {
        return Promise.reject(toApiError(error));
      }

      const config = error.config as RetriableConfig;
      const status = error.response?.status;
      if (
        status === 401 &&
        !config._retry &&
        !isPublicAuthRequest(config.url)
      ) {
        config._retry = true;
        const access = await refreshAccessToken();
        if (access) {
          config.headers.set("Authorization", `Bearer ${access}`);
          return client.request(config);
        }
      }

      return Promise.reject(toApiError(error));
    },
  );

  return client;
}

export const api = createApiClient();
