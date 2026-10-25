import { X } from "lucide-react";
import type { ReactNode } from "react";

import {
  DEFAULT_PAGE_SIZE,
  Pagination,
} from "@/components/pagination";
import { QueryState } from "@/components/query-state";
import { Button } from "@/components/ui/button";
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
  /** When true, shows a Clear filters control next to chips/search. */
  hasActiveFilters?: boolean;
  onClearFilters?: () => void;
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
  hasActiveFilters = false,
  onClearFilters,
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
        <div className="relative w-full max-w-sm sm:flex-1">
          <Input
            value={searchValue}
            placeholder={searchPlaceholder}
            className="h-9 w-full rounded-lg bg-card pr-9"
            onChange={(event) => onSearchChange(event.target.value)}
          />
          {searchValue ? (
            <button
              type="button"
              aria-label="Clear search"
              className="absolute top-1/2 right-2 flex size-6 -translate-y-1/2 items-center justify-center rounded-md text-muted-foreground hover:bg-secondary hover:text-foreground"
              onClick={() => onSearchChange("")}
            >
              <X className="size-3.5" strokeWidth={2} />
            </button>
          ) : null}
        </div>
        {filters || (hasActiveFilters && onClearFilters) ? (
          <div className="flex flex-wrap items-center gap-2">
            {filters}
            {hasActiveFilters && onClearFilters ? (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="rounded-lg text-muted-foreground"
                onClick={onClearFilters}
              >
                Clear filters
              </Button>
            ) : null}
          </div>
        ) : null}
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
              // pointer-events-none so AG Grid filter popups (popupParent=body)
              // stay clickable above this message layer.
              // z-[1] stays under AG Grid filter popups (.ag-popup z-index: 1000).
              <div className="pointer-events-none absolute inset-0 z-[1] flex items-center justify-center bg-card/80 p-6">
                <div
                  className={
                    hasActiveFilters ? undefined : "pointer-events-auto"
                  }
                >
                  {empty}
                </div>
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
