import type { ReactNode } from "react";

import {
  DEFAULT_PAGE_SIZE,
  Pagination,
} from "@/components/pagination";
import { QueryState } from "@/components/query-state";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type ResourceListChromeProps = {
  title: string;
  subtitle: ReactNode;
  actions?: ReactNode;
  searchValue: string;
  searchPlaceholder: string;
  onSearchChange: (value: string) => void;
  filters?: ReactNode;
  isLoading: boolean;
  isError: boolean;
  errorMessage?: string;
  onRetry?: () => void;
  isRefetching?: boolean;
  showEmpty?: boolean;
  empty?: ReactNode;
  showPagination: boolean;
  page: number;
  pageSize?: number;
  totalCount: number;
  onPageChange: (page: number) => void;
  children: ReactNode;
};

/**
 * Shared list page chrome for Products / Orders (header, search, chips, grid card).
 */
export function ResourceListChrome({
  title,
  subtitle,
  actions,
  searchValue,
  searchPlaceholder,
  onSearchChange,
  filters,
  isLoading,
  isError,
  errorMessage,
  onRetry,
  isRefetching,
  showEmpty,
  empty,
  showPagination,
  page,
  pageSize = DEFAULT_PAGE_SIZE,
  totalCount,
  onPageChange,
  children,
}: ResourceListChromeProps) {
  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-[28px] font-semibold tracking-tight text-foreground sm:text-[32px]">
            {title}
          </h1>
          <p className="text-body">{subtitle}</p>
        </div>
        {actions}
      </header>

      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
        <Input
          value={searchValue}
          placeholder={searchPlaceholder}
          className="h-9 w-full max-w-sm rounded-lg bg-card sm:flex-1"
          onChange={(event) => onSearchChange(event.target.value)}
        />
        {filters ? <div className="flex flex-wrap gap-2">{filters}</div> : null}
      </div>

      <QueryState
        isLoading={isLoading}
        isError={isError}
        errorMessage={errorMessage}
        onRetry={onRetry}
      >
        <Card
          aria-busy={isRefetching || undefined}
          className="relative gap-0 overflow-hidden rounded-[24px] py-0 ring-0"
        >
          <CardContent className="relative p-0">
            {children}
            {showEmpty && empty ? (
              <div className="absolute inset-0 z-10 flex items-center justify-center bg-card/80 p-6">
                {empty}
              </div>
            ) : null}
          </CardContent>
          {showPagination ? (
            <CardFooter className="justify-stretch border-t border-border bg-card px-4 py-3">
              <Pagination
                className="w-full"
                page={page}
                pageSize={pageSize}
                totalCount={totalCount}
                onPageChange={onPageChange}
              />
            </CardFooter>
          ) : null}
        </Card>
      </QueryState>
    </div>
  );
}
