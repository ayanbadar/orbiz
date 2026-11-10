import { StatusBadge } from "@/components/status-badge";
import type { FulfilmentStatus } from "@/features/orders/types";
import {
  getFulfilmentBadgeClassName,
  getFulfilmentLabel,
} from "@/features/orders/utils/order-status";

export function OrderStatusBadge({
  status,
  className,
}: {
  status: FulfilmentStatus;
  className?: string;
}) {
  return (
    <StatusBadge
      toneClassName={getFulfilmentBadgeClassName(status)}
      className={className}
    >
      {getFulfilmentLabel(status)}
    </StatusBadge>
  );
}
