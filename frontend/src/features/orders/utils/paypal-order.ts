import { toast } from "@/components/ui/sonner";
import type { Order } from "@/features/orders/types";

/** The order can still be asked to pay (checkout or invoice). */
export function canRequestPayment(order: Order): boolean {
  if (
    order.fulfilment_status === "cancelled" ||
    order.fulfilment_status === "draft"
  ) {
    return false;
  }
  return (
    order.payment_status === "pending" ||
    order.payment_status === "unpaid" ||
    order.payment_status === "failed" ||
    order.payment_status === "cancelled"
  );
}

/** A PayPal payment exists with money left to refund. */
export function canRefund(order: Order): boolean {
  return (
    (order.payment_status === "paid" ||
      order.payment_status === "partially_refunded") &&
    Number(order.paypal_refundable_amount ?? "0") > 0
  );
}

/** How long a queued payment email is worth polling for before the seller is told to check. */
const EMAIL_POLL_WINDOW_MS = 2 * 60 * 1000;

/** A payment email was queued moments ago and the worker has not reported back yet. */
export function isPaymentEmailInFlight(order: Order | undefined): boolean {
  const request = order?.paypal_payment_request;
  if (!request || request.last_email_status !== "queued" || !request.last_emailed_at) {
    return false;
  }
  return Date.now() - new Date(request.last_emailed_at).getTime() < EMAIL_POLL_WINDOW_MS;
}

export async function copyLink(url: string, label: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(url);
    toast.success(`${label} copied.`);
  } catch {
    toast.error("Could not copy the link — open it and copy from the address bar.");
  }
}
