import { useState } from "react";
import { Link } from "react-router-dom";

import { ConfirmDialog } from "@/components/confirm-dialog";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { toast } from "@/components/ui/sonner";
import { ROUTES } from "@/constants/routes";
import { getErrorMessage } from "@/features/auth/utils/form-errors";
import { useCancelOrder, useConfirmOrder, useOrder } from "@/features/orders/api/orders.api";
import { OrderConfirmDialog } from "@/features/orders/components/order-confirm-dialog";
import { OrderStatusBadge } from "@/features/orders/components/order-status-badge";
import { PaymentStatusBadge } from "@/features/orders/components/payment-status-badge";
import type { Order } from "@/features/orders/types";

/**
 * Orbiz AI auto-creates a Draft order — it deducts no stock and is fully
 * editable, so it's safe to render immediately. `order` is only the seed —
 * this subscribes to the live order so Confirm/Edit/Cancel react to whatever
 * actually happened (own confirm, cancel, or any other order mutation),
 * instead of staying frozen on the just-created snapshot.
 */
export function DraftOrderCard({ order: seed }: { order: Order }) {
  const { data: order = seed } = useOrder(seed.id, { initialData: seed });
  const confirmOrder = useConfirmOrder(order.id);
  const cancelOrder = useCancelOrder(order.id);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);

  const isDraft = order.fulfilment_status === "draft";
  const isCancelable =
    order.fulfilment_status !== "cancelled" && order.fulfilment_status !== "completed";

  const handleConfirm = async (notifyCustomer: boolean) => {
    try {
      await confirmOrder.mutateAsync({ notify_customer: notifyCustomer });
      toast.success(`${order.number} confirmed.`);
      setConfirmOpen(false);
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not confirm order."));
    }
  };

  const handleCancel = async () => {
    try {
      await cancelOrder.mutateAsync();
      toast.success(`${order.number} cancelled.`);
      setCancelOpen(false);
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not cancel order."));
    }
  };

  return (
    <Card className="max-w-md">
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center justify-between gap-2">
          <span>{order.number}</span>
          <span className="flex gap-1.5">
            <OrderStatusBadge status={order.fulfilment_status} />
            <PaymentStatusBadge status={order.payment_status} />
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div>
          <p className="font-medium text-foreground">{order.customer.name}</p>
          {order.customer.email ? (
            <p className="text-muted-foreground">{order.customer.email}</p>
          ) : null}
        </div>
        <ul className="space-y-1">
          {order.lines.map((line) => (
            <li key={line.id} className="flex justify-between gap-2">
              <span>
                {line.quantity} × {line.product_name} ({line.sku})
              </span>
              <span>{line.line_total}</span>
            </li>
          ))}
        </ul>
        <div className="flex justify-between border-t border-border pt-2 font-semibold">
          <span>Total</span>
          <span>
            {order.currency} {order.total}
          </span>
        </div>
        {order.delivery_notes ? (
          <p className="text-muted-foreground">Delivery: {order.delivery_notes}</p>
        ) : null}
        {order.source_message ? (
          <blockquote className="rounded-md bg-muted px-3 py-2 text-muted-foreground">
            From: “{order.source_message}”
          </blockquote>
        ) : null}
      </CardContent>
      <CardFooter className="flex flex-wrap gap-2">
        {isDraft ? (
          <>
            <Button
              size="sm"
              onClick={() => setConfirmOpen(true)}
              disabled={confirmOrder.isPending}
            >
              Confirm order
            </Button>
            <Button size="sm" variant="outline" asChild>
              <Link to={ROUTES.orders.edit(order.id)}>Edit</Link>
            </Button>
          </>
        ) : null}
        {isCancelable ? (
          <Button
            size="sm"
            variant="destructive"
            onClick={() => setCancelOpen(true)}
            disabled={cancelOrder.isPending}
          >
            Cancel order
          </Button>
        ) : null}
        <Button size="sm" variant="ghost" asChild>
          <Link to={ROUTES.orders.detail(order.id)}>Open order</Link>
        </Button>
      </CardFooter>
      <OrderConfirmDialog
        order={order}
        open={confirmOpen}
        pending={confirmOrder.isPending}
        onOpenChange={setConfirmOpen}
        onSubmit={handleConfirm}
      />
      <ConfirmDialog
        open={cancelOpen}
        onOpenChange={setCancelOpen}
        title={isDraft ? "Discard this draft order?" : "Cancel this order?"}
        description="Deducted stock, if any, will be restored."
        confirmLabel="Cancel order"
        cancelLabel="Keep order"
        variant="destructive"
        onConfirm={() => void handleCancel()}
      />
    </Card>
  );
}
