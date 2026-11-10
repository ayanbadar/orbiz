import { Button } from "@/components/ui/button";
import { cn } from "cn";

/** Matches backend `REST_FRAMEWORK["PAGE_SIZE"]` / StandardPagination default. */
export const DEFAULT_PAGE_SIZE = 20;

export function getPageCount(
  totalCount: number,
  pageSize: number = DEFAULT_PAGE_SIZE,
): number {
  if (totalCount <= 0 || pageSize <= 0) {
    return 1;
  }
  return Math.ceil(totalCount / pageSize);
}

type PaginationProps = {
  page: number;
  totalCount: number;
  pageSize?: number;
  onPageChange: (page: number) => void;
  className?: string;
};

/**
 * Shared Prev/Next control for DRF page-number lists.
 * Reuse on products, orders, and any other paginated table.
 */
export function Pagination({
  page,
  totalCount,
  pageSize = DEFAULT_PAGE_SIZE,
  onPageChange,
  className,
}: PaginationProps) {
  const pageCount = getPageCount(totalCount, pageSize);
  // Hide chrome when there is nothing to page through (avoids noisy "1 / 1").
  if (totalCount <= 0 || pageCount <= 1) {
    return null;
  }

  const from = (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, totalCount);
  const canPrev = page > 1;
  const canNext = page < pageCount;

  return (
    <nav
      aria-label="Pagination"
      className={cn(
        "flex flex-wrap items-center justify-between gap-3 text-sm text-muted-foreground",
        className,
      )}
    >
      <p>
        {from}–{to} of {totalCount}
      </p>
      <div className="flex items-center gap-2">
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={!canPrev}
          onClick={() => onPageChange(page - 1)}
        >
          Previous
        </Button>
        <span className="min-w-[5.5rem] text-center tabular-nums text-foreground">
          {page} / {pageCount}
        </span>
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={!canNext}
          onClick={() => onPageChange(page + 1)}
        >
          Next
        </Button>
      </div>
    </nav>
  );
}
