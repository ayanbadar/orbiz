import axios, { AxiosError, type AxiosInstance } from "axios";

import { env } from "@/lib/env";

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

function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) {
    return error;
  }

  if (error instanceof AxiosError) {
    const status = error.response?.status;
    const data = error.response?.data as
      { message?: string; code?: string } | undefined;

    return new ApiError(data?.message ?? error.message ?? "Request failed", {
      status,
      code: data?.code,
      details: data,
      cause: error,
    });
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

  client.interceptors.response.use(
    (response) => response,
    (error: unknown) => {
      // Future: handle 401/403 auth redirects here.
      return Promise.reject(toApiError(error));
    },
  );

  return client;
}

export const api = createApiClient();
