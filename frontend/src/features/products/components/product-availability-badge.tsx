import { cn } from "cn";

import type { Product } from "@/features/products/types";
import {
  getProductAvailabilityBadgeClassName,
  getProductAvailabilityLabel,
} from "@/features/products/utils/product-status";

type AvailabilitySlice = Pick<
  Product,
  "is_active" | "stock_quantity" | "is_low_stock"
>;

export function ProductAvailabilityBadge({
  product,
  className,
}: {
  product: AvailabilitySlice;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center whitespace-nowrap rounded-full px-3 py-1.5 text-sm font-semibold leading-none",
        getProductAvailabilityBadgeClassName(product),
        className,
      )}
    >
      {getProductAvailabilityLabel(product)}
    </span>
  );
}
