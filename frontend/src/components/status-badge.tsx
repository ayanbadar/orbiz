import type { ReactNode } from "react";
import { cn } from "cn";

/** Shared status pill — DESIGN.md: Inter 14/600, padding 4×12, rounded-full. */
export function StatusBadge({
  children,
  toneClassName,
  className,
}: {
  children: ReactNode;
  toneClassName: string;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center whitespace-nowrap rounded-full px-3 py-1 text-sm font-semibold leading-none",
        toneClassName,
        className,
      )}
    >
      {children}
    </span>
  );
}

/** Tone classes for StatusBadge, matching the order/payment badges. */
export const STATUS_TONES = {
  positive: "bg-muted text-positive-deep",
  warning: "bg-warning text-warning-content",
  negative: "bg-negative-bg text-white",
  neutral: "bg-secondary text-foreground",
} as const;
