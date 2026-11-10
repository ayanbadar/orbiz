/** Format a decimal-string amount in the given ISO currency. */
export function formatMoney(value: string | number, currency: string): string {
  const amount = Number(value);
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency,
    }).format(amount);
  } catch {
    // Unknown currency code: still show the number rather than crash the page.
    return `${amount.toFixed(2)} ${currency}`;
  }
}

export function formatCount(value: number): string {
  return new Intl.NumberFormat().format(value);
}

export type Delta = {
  direction: "up" | "down" | "flat";
  /** Display text, e.g. "+12%" or "New". */
  label: string;
};

/** Change from the previous period to the current one. */
export function getDelta(
  current: string | number,
  previous: string | number,
): Delta {
  const now = Number(current);
  const before = Number(previous);
  if (before === 0) {
    return now > 0
      ? { direction: "up", label: "New" }
      : { direction: "flat", label: "No change" };
  }
  const percent = Math.round(((now - before) / before) * 100);
  if (percent === 0) return { direction: "flat", label: "No change" };
  return {
    direction: percent > 0 ? "up" : "down",
    label: `${percent > 0 ? "+" : ""}${percent}%`,
  };
}
