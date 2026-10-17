import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";

type QueryStateProps = {
  isLoading?: boolean;
  isError?: boolean;
  isEmpty?: boolean;
  errorMessage?: string;
  emptyMessage?: string;
  onRetry?: () => void;
  children: ReactNode;
};

/**
 * Shared loading / error / empty presentation conventions.
 */
export function QueryState({
  isLoading = false,
  isError = false,
  isEmpty = false,
  errorMessage = "Failed to load data.",
  emptyMessage = "Nothing to show yet.",
  onRetry,
  children,
}: QueryStateProps) {
  if (isLoading) {
    return (
      <p className="text-sm text-muted-foreground" role="status">
        Loading…
      </p>
    );
  }

  if (isError) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-destructive" role="alert">
          {errorMessage}
        </p>
        {onRetry ? (
          <Button type="button" variant="outline" size="sm" onClick={onRetry}>
            Retry
          </Button>
        ) : null}
      </div>
    );
  }

  if (isEmpty) {
    return (
      <p className="text-sm text-muted-foreground" role="status">
        {emptyMessage}
      </p>
    );
  }

  return children;
}
