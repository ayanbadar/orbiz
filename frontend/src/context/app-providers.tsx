import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { NuqsAdapter } from "nuqs/adapters/react-router/v7";
import type { ReactNode } from "react";
import { BrowserRouter } from "react-router-dom";

import { DataGridProvider } from "@/components/data-grid";
import { ErrorBoundary } from "@/components/error-boundary";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/features/auth/context/auth-context";
import { queryClient } from "@/lib/query-client";

type AppProvidersProps = {
  children: ReactNode;
};

/**
 * Flat provider composition for app-wide concerns.
 * Add new providers here only when they are genuinely global.
 */
export function AppProviders({ children }: AppProvidersProps) {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <NuqsAdapter>
            <AuthProvider>
              <DataGridProvider>{children}</DataGridProvider>
            </AuthProvider>
          </NuqsAdapter>
        </BrowserRouter>
        <ReactQueryDevtools initialIsOpen={false} />
        <Toaster />
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
