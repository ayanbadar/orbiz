import { RefreshCw } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "cn";

import { Button } from "@/components/ui/button";
import { RangeTabs } from "@/features/dashboard/components/range-tabs";
import type { DashboardRange } from "@/features/dashboard/types";

/** Title, period tabs, and a refresh button that shows when the data was last fetched. */
export function DashboardHeader({
  title,
  subtitle,
  range,
  onRangeChange,
  onRefresh,
  isFetching,
  updatedAt,
}: {
  title: string;
  subtitle: ReactNode;
  range: DashboardRange;
  onRangeChange: (range: DashboardRange) => void;
  onRefresh: () => void;
  isFetching: boolean;
  /** Epoch ms of the last successful fetch (0 before the first one). */
  updatedAt: number;
}) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div className="space-y-1">
        <h1 className="text-[28px] font-semibold tracking-tight text-foreground sm:text-[32px]">
          {title}
        </h1>
        <p className="text-body">{subtitle}</p>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        {updatedAt ? (
          <span className="hidden text-xs text-muted-foreground sm:inline">
            Updated{" "}
            {new Date(updatedAt).toLocaleTimeString(undefined, {
              hour: "numeric",
              minute: "2-digit",
            })}
          </span>
        ) : null}
        <RangeTabs value={range} onChange={onRangeChange} />
        <Button
          type="button"
          variant="outline"
          size="icon"
          className="rounded-full bg-card"
          aria-label="Refresh dashboard"
          onClick={onRefresh}
        >
          <RefreshCw className={cn("size-4", isFetching && "animate-spin")} />
        </Button>
      </div>
    </header>
  );
}
