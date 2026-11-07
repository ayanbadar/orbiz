import { useState } from "react";

import type { ConfirmDialogOptions } from "@/components/confirm-dialog";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/sonner";
import { getErrorMessage } from "@/features/auth/utils/form-errors";
import { ON_INK_OUTLINE_BUTTON } from "@/features/orders/components/paypal-card-styles";
import { PaypalInvoiceDialog } from "@/features/orders/components/paypal-invoice-dialog";
import type { Order } from "@/features/orders/types";
import { canRequestPayment, copyLink } from "@/features/orders/utils/paypal-order";
import { useCancelPaypalInvoice } from "@/features/payments/api/payments.api";
import type { PaymentInvoiceStatus } from "@/features/payments/types";

const STATUS_LABELS: Record<PaymentInvoiceStatus, string> = {
  draft: "Draft",
  sent: "Sent",
  shared: "Link only",
  paid: "Paid",
  partially_refunded: "Partially refunded",
  refunded: "Refunded",
  cancelled: "Cancelled",
  failed: "Failed",
};

const OPEN_STATUSES: PaymentInvoiceStatus[] = ["draft", "sent", "shared"];

type Props = {
  order: Order;
  confirm: (options: ConfirmDialogOptions) => Promise<boolean>;
  /** PayPal credentials are set and the order currency is accepted. */
  enabled: boolean;
};

export function PaypalInvoiceSection({ order, confirm, enabled }: Props) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const cancelInvoice = useCancelPaypalInvoice(order.id);
  const invoice = order.paypal_invoice ?? null;
  const isOpen = invoice ? OPEN_STATUSES.includes(invoice.status) : false;
  const payUrl = invoice?.recipient_view_url ?? "";

  const onCancel = async () => {
    if (!invoice) return;
    const ok = await confirm({
      title: "Cancel this PayPal invoice?",
      description: `Invoice ${invoice.invoice_number} will no longer be payable. The order stays as it is.`,
      confirmLabel: "Cancel invoice",
      cancelLabel: "Keep invoice",
      variant: "destructive",
    });
    if (!ok) return;
    try {
      await cancelInvoice.mutateAsync();
      toast.success("PayPal Sandbox invoice cancelled.");
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not cancel the invoice."));
    }
  };

  return (
    <div className="space-y-3 border-t border-background/15 pt-4">
      <p className="text-sm font-semibold text-background">PayPal invoice</p>

      {invoice ? (
        <div className="space-y-1 text-sm text-background/80">
          <p>
            {invoice.invoice_number} ·{" "}
            <span className="font-semibold text-primary">
              {STATUS_LABELS[invoice.status]}
            </span>
          </p>
          <p className="tabular-nums">
            {invoice.currency} {invoice.amount}
          </p>
          {invoice.status === "sent" ? (
            <p>
              Sent by PayPal to {invoice.recipient_email}. Sandbox never
              delivers real email and its Notifications page can lag — use
              Open invoice to pay as the buyer.
            </p>
          ) : null}
          {invoice.status === "shared" ? (
            <p>No email was sent — copy the link and share it with the buyer.</p>
          ) : null}
          {invoice.last_error ? (
            <p className="text-sm text-destructive" role="alert">
              {invoice.last_error}
            </p>
          ) : null}
        </div>
      ) : (
        <p className="text-sm text-background/70">
          Send the buyer a PayPal invoice instead of sharing a checkout link
          yourself.
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        {canRequestPayment(order) ? (
          <Button
            type="button"
            className="rounded-[24px]"
            disabled={!enabled}
            onClick={() => setDialogOpen(true)}
          >
            {invoice && isOpen ? "Send new invoice" : "Send PayPal invoice"}
          </Button>
        ) : null}

        {isOpen && payUrl ? (
          <>
            <Button
              type="button"
              variant="outline"
              className={ON_INK_OUTLINE_BUTTON}
              onClick={() =>
                window.open(payUrl, "_blank", "noopener,noreferrer")
              }
            >
              Open invoice
            </Button>
            <Button
              type="button"
              variant="outline"
              className={ON_INK_OUTLINE_BUTTON}
              onClick={() => {
                void copyLink(payUrl, "Invoice link");
              }}
            >
              Copy invoice link
            </Button>
          </>
        ) : null}

        {isOpen ? (
          <Button
            type="button"
            variant="outline"
            className={ON_INK_OUTLINE_BUTTON}
            disabled={cancelInvoice.isPending}
            onClick={() => {
              void onCancel();
            }}
          >
            {cancelInvoice.isPending ? "Cancelling…" : "Cancel invoice"}
          </Button>
        ) : null}
      </div>

      <PaypalInvoiceDialog
        order={order}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
      />
    </div>
  );
}
