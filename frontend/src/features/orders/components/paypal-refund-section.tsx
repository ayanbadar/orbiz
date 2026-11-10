import { useState } from "react";

import { FormattedTime } from "@/components/formatted-time";
import { Button } from "@/components/ui/button";
import { PaypalRefundDialog } from "@/features/orders/components/paypal-refund-dialog";
import type { Order } from "@/features/orders/types";
import { canRefund } from "@/features/orders/utils/paypal-order";
import type { PaymentRefundStatus } from "@/features/payments/types";

const STATUS_LABELS: Record<PaymentRefundStatus, string> = {
  pending: "Pending",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
};

export function PaypalRefundSection({ order }: { order: Order }) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const refunds = order.paypal_refunds ?? [];
  const refundable = canRefund(order);

  if (!refundable && refunds.length === 0) return null;

  return (
    <div className="space-y-3 border-t border-background/15 pt-4">
      <p className="text-sm font-semibold text-background">Refunds</p>

      {refunds.length > 0 ? (
        <ul className="space-y-1 text-sm text-background/80">
          {refunds.map((refund) => (
            <li key={refund.id}>
              <span className="tabular-nums">
                {refund.currency} {refund.amount}
              </span>{" "}
              ·{" "}
              <span className="font-semibold text-primary">
                {STATUS_LABELS[refund.status]}
              </span>{" "}
              ·{" "}
              {refund.source === "paypal" ? "from the PayPal dashboard" : "from Orbiz"}{" "}
              · <FormattedTime value={refund.created_at} />
              {refund.last_error ? (
                <span className="block text-destructive" role="alert">
                  {refund.last_error}
                </span>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}

      {refundable ? (
        <>
          <p className="text-sm text-background/70 tabular-nums">
            Left to refund: {order.currency} {order.paypal_refundable_amount}
          </p>
          <Button
            type="button"
            className="rounded-[24px]"
            onClick={() => setDialogOpen(true)}
          >
            Refund via PayPal
          </Button>
          <PaypalRefundDialog
            order={order}
            open={dialogOpen}
            onOpenChange={setDialogOpen}
          />
        </>
      ) : null}
    </div>
  );
}
