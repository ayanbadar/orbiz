import {
  ArrowDownRight,
  ArrowUpRight,
  Minus,
  type LucideIcon,
} from "lucide-react";
import { cn } from "cn";

import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Sparkline } from "@/features/dashboard/components/sparkline";
import { CHART_COLORS } from "@/features/dashboard/utils/chart-theme";
import { getDelta } from "@/features/dashboard/utils/format";

const DELTA_STYLE = {
  up: { icon: ArrowUpRight, className: "bg-muted text-positive-deep" },
  down: {
    icon: ArrowDownRight,
    className: "bg-destructive/10 text-destructive",
  },
  flat: { icon: Minus, className: "bg-secondary text-body" },
} as const;

type KpiTileProps = {
  label: string;
  /** Already formatted for display. */
  value: string;
  icon: LucideIcon;
  /** Compare with the previous period and show the change as a pill. */
  delta?: { current: string | number; previous: string | number };
  /** Small note under the value when there is nothing to compare. */
  hint?: string;
  /** Daily values for the sparkline. */
  trend?: number[];
};

/** Headline number with its change, an optional trend line, and a hover lift. */
export function KpiTile({
  label,
  value,
  icon: Icon,
  delta,
  hint,
  trend,
}: KpiTileProps) {
  const change = delta ? getDelta(delta.current, delta.previous) : null;
  const style = change ? DELTA_STYLE[change.direction] : null;

  return (
    <Card
      className={cn(
        "gap-3 rounded-[24px] p-5 ring-0 transition duration-200",
        "hover:-translate-y-0.5 hover:ring-2 hover:ring-foreground/10",
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm font-medium text-body">{label}</span>
        <span className="flex size-9 items-center justify-center rounded-full bg-muted text-accent-foreground">
          <Icon className="size-4.5" aria-hidden />
        </span>
      </div>

      <p className="text-[28px] leading-none font-semibold tracking-tight text-foreground">
        {value}
      </p>

      <div className="flex min-h-6 items-center gap-2 text-xs text-muted-foreground">
        {change && style ? (
          <>
            <span
              className={cn(
                "inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 font-semibold",
                style.className,
              )}
            >
              <style.icon className="size-3.5" aria-hidden />
              {change.label}
            </span>
            <span>vs previous period</span>
          </>
        ) : (
          <span>{hint}</span>
        )}
      </div>

      {trend ? <Sparkline values={trend} color={CHART_COLORS.forest} /> : null}
    </Card>
  );
}

export function KpiTileSkeleton() {
  return <Skeleton className="h-[176px] rounded-[24px]" />;
}
