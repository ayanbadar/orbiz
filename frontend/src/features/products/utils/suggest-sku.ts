/**
 * Suggest a store SKU from a product title (Channel3 import prefill).
 * Seller still owns the final SKU — this is only a starting value.
 */
export function suggestSkuFromTitle(title: string, maxLength = 20): string {
  const words = title
    .toUpperCase()
    .replace(/[^A-Z0-9\s]+/g, " ")
    .trim()
    .split(/\s+/)
    .filter((word) => word.length > 0);

  if (words.length === 0) {
    return "SKU";
  }

  const joined = words.slice(0, 3).join("-");
  return joined.slice(0, maxLength).replace(/-+$/, "") || "SKU";
}
