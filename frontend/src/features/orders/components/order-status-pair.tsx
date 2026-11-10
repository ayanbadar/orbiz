import type { ReactNode } from "react";

import { OrderStatusBadge } from "@/features/orders/components/order-status-badge";
import { PaymentStatusBadge } from "@/features/orders/components/payment-status-badge";
import type { FulfilmentStatus, PaymentStatus } from "@/features/orders/types";

/** Detail header: short badges + dimension captions (list uses column headers). */
export function OrderStatusPair({
  fulfilmentStatus,
  paymentStatus,
}: {
  fulfilmentStatus: FulfilmentStatus;
  paymentStatus: PaymentStatus;
}) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
      <StatusDimension label="Fulfilment">
        <OrderStatusBadge status={fulfilmentStatus} />
      </StatusDimension>
      <StatusDimension label="Payment">
        <PaymentStatusBadge status={paymentStatus} />
      </StatusDimension>
    </div>
  );
}

function StatusDimension({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <span className="inline-flex items-center gap-2">
      <span className="text-xs text-muted-foreground">{label}</span>
      {children}
    </span>
  );
}
