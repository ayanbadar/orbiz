import type { ReactNode } from "react";
import { cn } from "cn";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { CHART_HEIGHT_PX } from "@/features/dashboard/utils/chart-theme";

type ChartCardProps = {
  title: string;
  description?: string;
  /** Controls shown at the right of the header, e.g. a SegmentedControl. */
  action?: ReactNode;
  isLoading?: boolean;
  isEmpty?: boolean;
  emptyMessage?: string;
  className?: string;
  children: ReactNode;
};

/** Shared frame for every dashboard panel: title, actions, then content with loading and empty states. */
export function ChartCard({
  title,
  description,
  action,
  isLoading = false,
  isEmpty = false,
  emptyMessage = "No data for this period.",
  className,
  children,
}: ChartCardProps) {
  return (
    <Card
      className={cn(
        "rounded-[24px] py-6 ring-0 transition-shadow duration-200 hover:ring-2 hover:ring-foreground/5",
        className,
      )}
    >
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-3 px-6">
        <div className="space-y-1">
          <CardTitle className="text-lg font-semibold">{title}</CardTitle>
          {description ? (
            <CardDescription>{description}</CardDescription>
          ) : null}
        </div>
        {action}
      </CardHeader>
      <CardContent className="px-6">
        {isLoading ? (
          <Skeleton style={{ height: CHART_HEIGHT_PX }} />
        ) : isEmpty ? (
          <div
            className="flex flex-col items-center justify-center gap-1 rounded-2xl bg-secondary/60 text-center"
            style={{ minHeight: 140 }}
            role="status"
          >
            <p className="text-sm font-medium text-foreground">
              Nothing here yet
            </p>
            <p className="text-sm text-muted-foreground">{emptyMessage}</p>
          </div>
        ) : (
          children
        )}
      </CardContent>
    </Card>
  );
}
