import { cn } from "cn";

import {
  formatAbsoluteDate,
  formatAbsoluteDateTime,
  formatRelativeTime,
} from "@/lib/format-datetime";

type Variant = "relative" | "datetime" | "date";

/**
 * Accessible `<time>` with human display + absolute tooltip.
 * Prefer `relative` in feeds/lists; `datetime` when the exact clock matters.
 */
export function FormattedTime({
  value,
  variant = "relative",
  className,
}: {
  value: string;
  variant?: Variant;
  className?: string;
}) {
  const absolute = formatAbsoluteDateTime(value);
  if (!absolute) return null;

  const display =
    variant === "relative"
      ? formatRelativeTime(value)
      : variant === "date"
        ? formatAbsoluteDate(value)
        : absolute;

  return (
    <time dateTime={value} title={absolute} className={cn(className)}>
      {display}
    </time>
  );
}
