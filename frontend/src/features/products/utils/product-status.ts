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

/** Shared status color for list + detail — keep tone rules in one place. */
export function getProductAvailabilityClassName(
  product: AvailabilitySlice,
): string {
  if (!product.is_active) {
    return "text-muted-foreground";
  }
  if (product.stock_quantity <= 0) {
    return "text-destructive";
  }
  if (product.is_low_stock) {
    return "text-warning-deep";
  }
  return "text-positive";
}
