import { Link } from "react-router-dom";

import type { ConfirmDialogOptions } from "@/components/confirm-dialog";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/sonner";
import { ROUTES } from "@/constants/routes";
import { getErrorMessage } from "@/features/auth/utils/form-errors";
import {
  useAbandonPayment,
  useCancelOrder,
  useConfirmOrder,
  useMarkOrderPaid,
  useTransitionOrder,
} from "@/features/orders/api/orders.api";
import type { FulfilmentStatus, Order } from "@/features/orders/types";

const NEXT_FULFILMENT: Partial<Record<FulfilmentStatus, FulfilmentStatus>> = {
  unfulfilled: "processing",
  processing: "shipped",
  shipped: "completed",
};

const PAYMENT_GATED: ReadonlySet<FulfilmentStatus> = new Set([
  "processing",
  "shipped",
  "completed",
]);

type Props = {
  order: Order;
  confirm: (options: ConfirmDialogOptions) => Promise<boolean>;
};

export function getOrderActionState(order: Order) {
  const nextStatus = NEXT_FULFILMENT[order.fulfilment_status];
  const needsPaidBeforeNext =
    Boolean(nextStatus) &&
    PAYMENT_GATED.has(nextStatus as FulfilmentStatus) &&
    order.payment_status !== "paid";
  const canAbandonPayment =
    order.fulfilment_status === "unfulfilled" &&
    order.payment_status === "pending";
  const canMarkPaid =
    order.fulfilment_status !== "cancelled" &&
    order.fulfilment_status !== "draft" &&
    order.payment_status !== "paid" &&
    (order.payment_status === "pending" ||
      order.payment_status === "cancelled" ||
      order.payment_status === "failed" ||
      order.payment_status === "unpaid");
  return { nextStatus, needsPaidBeforeNext, canAbandonPayment, canMarkPaid };
}

/** Header action buttons for order detail — mutations live here. */
export function OrderActions({ order, confirm }: Props) {
  const confirmOrder = useConfirmOrder(order.id);
  const cancelOrder = useCancelOrder(order.id);
  const transitionOrder = useTransitionOrder(order.id);
  const markPaid = useMarkOrderPaid(order.id);
  const abandonPayment = useAbandonPayment(order.id);
  const { nextStatus, needsPaidBeforeNext, canAbandonPayment, canMarkPaid } =
    getOrderActionState(order);

  const onConfirm = async () => {
    const ok = await confirm({
      title: "Confirm this order?",
      description: "Stock will be deducted for each line.",
      confirmLabel: "Confirm order",
    });
    if (!ok) return;
    try {
      await confirmOrder.mutateAsync();
      toast.success("Order confirmed. Stock updated.");
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not confirm order."));
    }
  };

  const onCancel = async () => {
    const ok = await confirm({
      title: "Cancel this order?",
      description: "Deducted stock will be restored.",
      confirmLabel: "Cancel order",
      cancelLabel: "Keep order",
      variant: "destructive",
    });
    if (!ok) return;
    try {
      await cancelOrder.mutateAsync();
      toast.success("Order cancelled.");
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not cancel order."));
    }
  };

  const onTransition = async () => {
    if (!nextStatus) return;
    if (needsPaidBeforeNext) {
      toast.error("Mark payment as paid before advancing fulfilment.");
      return;
    }
    const label = nextStatus.replaceAll("_", " ");
    const ok = await confirm({
      title: `Move fulfilment to “${label}”?`,
      description: "This updates the order fulfilment status.",
      confirmLabel: `Mark ${label}`,
    });
    if (!ok) return;
    try {
      await transitionOrder.mutateAsync(nextStatus);
      toast.success("Fulfilment status updated.");
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not update status."));
    }
  };

  const onMarkPaid = async () => {
    const ok = await confirm({
      title: "Mark this order paid?",
      description: "Demo only — PayPal will own this in §2.7.",
      confirmLabel: "Mark paid",
    });
    if (!ok) return;
    try {
      await markPaid.mutateAsync();
      toast.success("Payment marked paid.");
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not mark paid."));
    }
  };

  const onAbandonPayment = async () => {
    const ok = await confirm({
      title: "Abandon this payment attempt?",
      description:
        "The order stays unfulfilled so you can retry or cancel separately.",
      confirmLabel: "Abandon payment",
      variant: "destructive",
    });
    if (!ok) return;
    try {
      await abandonPayment.mutateAsync();
      toast.success("Payment attempt abandoned.");
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not abandon payment."));
    }
  };

  return (
    <div className="flex flex-wrap gap-2">
      {order.fulfilment_status === "draft" ? (
        <>
          <Button asChild variant="outline" className="rounded-[24px]">
            <Link to={ROUTES.orders.edit(order.id)}>Edit draft</Link>
          </Button>
          <Button
            className="rounded-[24px]"
            onClick={() => {
              void onConfirm();
            }}
            disabled={confirmOrder.isPending}
          >
            Confirm order
          </Button>
        </>
      ) : null}
      {canMarkPaid ? (
        <Button
          variant="outline"
          className="rounded-[24px]"
          onClick={() => {
            void onMarkPaid();
          }}
          disabled={markPaid.isPending}
        >
          Mark paid (demo)
        </Button>
      ) : null}
      {canAbandonPayment ? (
        <Button
          variant="outline"
          className="rounded-[24px]"
          onClick={() => {
            void onAbandonPayment();
          }}
          disabled={abandonPayment.isPending}
        >
          Abandon payment
        </Button>
      ) : null}
      {nextStatus ? (
        <Button
          variant="outline"
          className="rounded-[24px]"
          onClick={() => {
            void onTransition();
          }}
          disabled={transitionOrder.isPending || needsPaidBeforeNext}
        >
          Mark {nextStatus.replaceAll("_", " ")}
        </Button>
      ) : null}
      {order.fulfilment_status !== "cancelled" &&
      order.fulfilment_status !== "completed" ? (
        <Button
          variant="destructive"
          className="rounded-[24px]"
          onClick={() => {
            void onCancel();
          }}
          disabled={cancelOrder.isPending}
        >
          Cancel order
        </Button>
      ) : null}
    </div>
  );
}
