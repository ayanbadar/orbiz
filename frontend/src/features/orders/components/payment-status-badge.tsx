import { StatusBadge } from "@/components/status-badge";
import type { PaymentStatus } from "@/features/orders/types";
import {
  getPaymentBadgeClassName,
  getPaymentLabel,
} from "@/features/orders/utils/order-status";

export function PaymentStatusBadge({
  status,
  className,
}: {
  status: PaymentStatus;
  className?: string;
}) {
  return (
    <StatusBadge
      toneClassName={getPaymentBadgeClassName(status)}
      className={className}
    >
      {getPaymentLabel(status)}
    </StatusBadge>
  );
}
