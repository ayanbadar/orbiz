import { StatusBadge } from "@/components/status-badge";
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
    <StatusBadge
      toneClassName={getProductAvailabilityBadgeClassName(product)}
      className={className}
    >
      {getProductAvailabilityLabel(product)}
    </StatusBadge>
  );
}
