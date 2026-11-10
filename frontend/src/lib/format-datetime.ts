/**
 * Date display helpers — Cloudscape/Atlassian:
 * relative for recent scan, absolute without seconds when exact time matters,
 * full absolute always available for tooltips / title.
 */

const ABSOLUTE_DATETIME = new Intl.DateTimeFormat(undefined, {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

const ABSOLUTE_DATE = new Intl.DateTimeFormat(undefined, {
  day: "numeric",
  month: "short",
  year: "numeric",
});

const RELATIVE = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });

const MINUTE = 60;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;
const WEEK = 7 * DAY;

function toDate(value: string | Date): Date | null {
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

/** e.g. "25 Oct 2026, 00:17" (locale-aware; no seconds). */
export function formatAbsoluteDateTime(value: string | Date): string {
  const date = toDate(value);
  return date ? ABSOLUTE_DATETIME.format(date) : "";
}

/** e.g. "25 Oct 2026". */
export function formatAbsoluteDate(value: string | Date): string {
  const date = toDate(value);
  return date ? ABSOLUTE_DATE.format(date) : "";
}

/**
 * Relative within ~7 days ("2 hours ago", "yesterday"); older → absolute date.
 * Matches Atlassian: tooltip should still show the exact absolute time.
 */
export function formatRelativeTime(
  value: string | Date,
  now: Date = new Date(),
): string {
  const date = toDate(value);
  if (!date) return "";

  const diffSec = Math.round((date.getTime() - now.getTime()) / 1000);
  const absSec = Math.abs(diffSec);

  if (absSec < MINUTE) {
    return diffSec <= 0 ? "Just now" : "In a moment";
  }
  if (absSec >= WEEK) {
    return formatAbsoluteDate(date);
  }
  if (absSec >= DAY) {
    return RELATIVE.format(Math.round(diffSec / DAY), "day");
  }
  if (absSec >= HOUR) {
    return RELATIVE.format(Math.round(diffSec / HOUR), "hour");
  }
  return RELATIVE.format(Math.round(diffSec / MINUTE), "minute");
}
