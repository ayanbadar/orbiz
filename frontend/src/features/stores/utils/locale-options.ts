import type { SearchableSelectOption } from "@/components/searchable-select";

const FALLBACK_TIMEZONES = ["UTC"];
const FALLBACK_CURRENCIES = ["USD", "EUR", "GBP", "PKR", "INR", "AED"];

function supported(key: "timeZone" | "currency", fallback: string[]): string[] {
  try {
    const values = Intl.supportedValuesOf(key);
    return values.length > 0 ? values : fallback;
  } catch {
    return fallback;
  }
}

/** Current UTC offset label for a zone, e.g. "GMT+5". */
function offsetLabel(timeZone: string): string {
  try {
    return (
      new Intl.DateTimeFormat("en", { timeZone, timeZoneName: "shortOffset" })
        .formatToParts(new Date())
        .find((part) => part.type === "timeZoneName")?.value ?? ""
    );
  } catch {
    return "";
  }
}

export function getCurrencyOptions(): SearchableSelectOption[] {
  let names: Intl.DisplayNames | null = null;
  try {
    names = new Intl.DisplayNames(["en"], { type: "currency" });
  } catch {
    names = null;
  }
  return supported("currency", FALLBACK_CURRENCIES).map((code) => {
    const name = names?.of(code);
    return {
      value: code,
      label: code,
      primary: code,
      secondary: name && name !== code ? name : undefined,
      keywords: name,
    };
  });
}

export function getTimezoneOptions(): SearchableSelectOption[] {
  const zones = supported("timeZone", FALLBACK_TIMEZONES);
  // Some engines omit UTC from the canonical list.
  if (!zones.includes("UTC")) zones.unshift("UTC");
  return zones.map((zone) => ({
    value: zone,
    label: zone.replaceAll("_", " "),
    secondary: offsetLabel(zone) || undefined,
    keywords: zone,
  }));
}

/** Browser-detected timezone, only if it is a selectable option. */
export function detectTimezone(options: SearchableSelectOption[]): string {
  const detected = Intl.DateTimeFormat().resolvedOptions().timeZone;
  return options.some((o) => o.value === detected) ? detected : "UTC";
}
