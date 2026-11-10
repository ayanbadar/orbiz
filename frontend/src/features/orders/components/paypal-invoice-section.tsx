import { useState } from "react";

import type { ConfirmDialogOptions } from "@/components/confirm-dialog";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/sonner";
import { getErrorMessage } from "@/features/auth/utils/form-errors";
import { ON_INK_OUTLINE_BUTTON } from "@/features/orders/components/paypal-card-styles";
import { PaypalEmailStatus } from "@/features/orders/components/paypal-email-status";
import { PaypalInvoiceDialog } from "@/features/orders/components/paypal-invoice-dialog";
import type { Order } from "@/features/orders/types";
import {
  canRequestPayment,
  copyLink,
} from "@/features/orders/utils/paypal-order";
import { useCancelPaypalInvoice } from "@/features/payments/api/payments.api";
import type {
  EmailLinkKind,
  PaymentInvoiceStatus,
} from "@/features/payments/types";

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
  onEmail: (kind: EmailLinkKind) => void;
};

/** The primary way to ask a buyer to pay: a PayPal invoice, emailed from Orbiz or by PayPal. */
export function PaypalInvoiceSection({
  order,
  confirm,
  enabled,
  onEmail,
}: Props) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const cancelInvoice = useCancelPaypalInvoice(order.id);
  const invoice = order.paypal_invoice ?? null;
  const request = order.paypal_payment_request;
  const isOpen = invoice ? OPEN_STATUSES.includes(invoice.status) : false;
  const payUrl = invoice?.recipient_view_url ?? "";
  const canEmail = isOpen && request?.kind === "invoice" && request.can_email;
  const emailedBefore = Boolean(request?.last_email_status);
  const orbizDelivers = (request?.delivery_mode ?? "orbiz") === "orbiz";

  const onCancel = async () => {
    if (!invoice) return;
    const ok = await confirm({
      title: "Cancel this payment request?",
      description: `Invoice ${invoice.invoice_number} will no longer be payable. The order stays as it is.`,
      confirmLabel: "Cancel request",
      cancelLabel: "Keep request",
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
    <div className="space-y-3">
      <p className="text-sm font-semibold text-background">Request payment</p>

      {invoice ? (
        <div className="space-y-1 text-sm text-background/80">
          <p>
            Invoice {invoice.invoice_number} ·{" "}
            <span className="font-semibold text-primary">
              {STATUS_LABELS[invoice.status]}
            </span>
          </p>
          <p className="tabular-nums">
            {invoice.currency} {invoice.amount}
          </p>
          {isOpen && invoice.delivered_via === "paypal" ? (
            <p>
              Sent by PayPal to {invoice.recipient_email}.
              {order.paypal_sandbox
                ? " Sandbox never delivers real email — use Open invoice to pay as the buyer."
                : ""}
            </p>
          ) : null}
          {isOpen && invoice.delivered_via === "none" ? (
            <p>No email sent yet — email the link or copy it to share.</p>
          ) : null}
          <PaypalEmailStatus request={request} />
          {invoice.last_error ? (
            <p className="text-sm text-destructive" role="alert">
              {invoice.last_error}
            </p>
          ) : null}
        </div>
      ) : (
        <p className="text-sm text-background/70">
          {orbizDelivers
            ? "Email the buyer a PayPal invoice link. They pay on PayPal and Orbiz marks the order paid."
            : "PayPal emails the buyer an invoice. They pay on PayPal and Orbiz marks the order paid."}
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
            {invoice && isOpen ? "Send new request" : "Request payment"}
          </Button>
        ) : null}

        {canEmail ? (
          <Button
            type="button"
            variant="outline"
            className={ON_INK_OUTLINE_BUTTON}
            onClick={() => onEmail("request")}
          >
            {emailedBefore ? "Resend email" : "Email link"}
          </Button>
        ) : null}

        {canEmail && request?.last_email_status === "sent" ? (
          <Button
            type="button"
            variant="outline"
            className={ON_INK_OUTLINE_BUTTON}
            onClick={() => onEmail("reminder")}
          >
            Send reminder
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
            {cancelInvoice.isPending ? "Cancelling…" : "Cancel request"}
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
