import type { Product } from "@/features/products/types";

type AvailabilitySlice = Pick<
  Product,
  "is_active" | "stock_quantity" | "is_low_stock"
>;

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
