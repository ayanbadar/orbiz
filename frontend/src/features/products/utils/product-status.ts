import type { Product } from "@/features/products/types";

type AvailabilitySlice = Pick<
  Product,
  "is_active" | "stock_quantity" | "is_low_stock"
>;

export const PRODUCT_AVAILABILITY_LABELS = [
  "In stock",
  "Low stock",
  "Out of stock",
  "Inactive",
] as const;

export type ProductAvailabilityLabel =
  (typeof PRODUCT_AVAILABILITY_LABELS)[number];

/** Catalog / stock labels derived on the client — no backend field needed. */
export function getProductAvailabilityLabel(product: AvailabilitySlice): string {
  if (!product.is_active) {
    return "Inactive";
  }
  if (product.stock_quantity <= 0) {
    return "Out of stock";
  }
  if (product.is_low_stock) {
    return "Low stock";
  }
  return "In stock";
}

/** Match availability label (case-insensitive). */
export function parseProductAvailabilityLabel(
  raw: string,
): ProductAvailabilityLabel | null {
  const needle = raw.trim().toLowerCase();
  if (!needle) return null;
  return (
    PRODUCT_AVAILABILITY_LABELS.find(
      (label) => label.toLowerCase() === needle,
    ) ?? null
  );
}

/** Pill classes per DESIGN.md badges (positive / warning / negative). */
export function getProductAvailabilityBadgeClassName(
  product: AvailabilitySlice,
): string {
  if (!product.is_active) {
    return "bg-secondary text-muted-foreground";
  }
  if (product.stock_quantity <= 0) {
    return "bg-negative-bg text-white";
  }
  if (product.is_low_stock) {
    return "bg-warning text-warning-content";
  }
  return "bg-muted text-positive-deep";
}
