import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

import type { ConfirmDialogOptions } from "@/components/confirm-dialog";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { toast } from "@/components/ui/sonner";
import { getErrorMessage } from "@/features/auth/utils/form-errors";
import { PaypalEmailDialog } from "@/features/orders/components/paypal-email-dialog";
import { PaypalEmailStatus } from "@/features/orders/components/paypal-email-status";
import { ON_INK_OUTLINE_BUTTON } from "@/features/orders/components/paypal-card-styles";
import { PaypalInvoiceSection } from "@/features/orders/components/paypal-invoice-section";
import { PaypalRefundSection } from "@/features/orders/components/paypal-refund-section";
import type { Order } from "@/features/orders/types";
import { canRequestPayment, copyLink } from "@/features/orders/utils/paypal-order";
import {
  useCapturePaypalCheckout,
  useCreatePaypalCheckout,
} from "@/features/payments/api/payments.api";
import type { EmailLinkKind } from "@/features/payments/types";

type Props = {
  order: Order;
  confirm: (options: ConfirmDialogOptions) => Promise<boolean>;
};

export function PaypalSandboxCard({ order, confirm }: Props) {
  const [searchParams, setSearchParams] = useSearchParams();
  const createCheckout = useCreatePaypalCheckout(order.id);
  const captureCheckout = useCapturePaypalCheckout(order.id);
  const returnHandledRef = useRef(false);
  const [emailKind, setEmailKind] = useState<EmailLinkKind | null>(null);

  const checkout = order.paypal_checkout ?? null;
  const request = order.paypal_payment_request;
  const configured = order.paypal_configured ?? false;
  const sandbox = order.paypal_sandbox ?? true;
  const currencySupported = order.paypal_currency_supported ?? true;
  const busy = createCheckout.isPending || captureCheckout.isPending;
  // A superseded (cancelled) or finished checkout has no link worth sharing.
  const approveUrl =
    checkout && (checkout.status === "created" || checkout.status === "approved")
      ? checkout.approve_url
      : "";
  const canEmailCheckout =
    Boolean(approveUrl) && request?.kind === "checkout" && request.can_email;

  useEffect(() => {
    const flag = searchParams.get("paypal");
    if (!flag) {
      returnHandledRef.current = false;
      return;
    }

    if (flag === "cancel") {
      toast.message("PayPal Sandbox checkout was cancelled.");
      const next = new URLSearchParams(searchParams);
      next.delete("paypal");
      next.delete("token");
      next.delete("PayerID");
      setSearchParams(next, { replace: true });
      return;
    }

    if (flag !== "return") return;
    if (returnHandledRef.current) return;
    if (order.payment_status === "paid") {
      const next = new URLSearchParams(searchParams);
      next.delete("paypal");
      next.delete("token");
      next.delete("PayerID");
      setSearchParams(next, { replace: true });
      return;
    }

    returnHandledRef.current = true;
    void (async () => {
      try {
        await captureCheckout.mutateAsync();
        toast.success("PayPal Sandbox payment captured.");
      } catch (error) {
        toast.error(getErrorMessage(error, "Could not capture PayPal payment."));
      } finally {
        const next = new URLSearchParams(searchParams);
        next.delete("paypal");
        next.delete("token");
        next.delete("PayerID");
        setSearchParams(next, { replace: true });
      }
    })();
  }, [
    captureCheckout,
    order.payment_status,
    searchParams,
    setSearchParams,
  ]);

  const onCreate = async () => {
    const ok = await confirm({
      title: "Create PayPal Sandbox pay-now link?",
      description:
        "Opens a Sandbox approve link for this order total and cancels any open invoice. This is not a live charge.",
      confirmLabel: "Create pay-now link",
    });
    if (!ok) return;
    try {
      const created = await createCheckout.mutateAsync();
      toast.success("PayPal Sandbox pay-now link created.");
      if (created.approve_url) {
        window.open(created.approve_url, "_blank", "noopener,noreferrer");
      }
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not create PayPal checkout."));
    }
  };

  const onOpenApprove = () => {
    if (!approveUrl) return;
    window.open(approveUrl, "_blank", "noopener,noreferrer");
  };

  const onCapture = async () => {
    const ok = await confirm({
      title: "Capture PayPal Sandbox payment?",
      description: "Confirms the Sandbox payment on this order after buyer approval.",
      confirmLabel: "Capture payment",
    });
    if (!ok) return;
    try {
      await captureCheckout.mutateAsync();
      toast.success("PayPal Sandbox payment captured.");
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not capture PayPal payment."));
    }
  };

  return (
    <Card className="rounded-[24px] bg-foreground text-background ring-0">
      <CardHeader>
        <CardTitle className="text-primary">
          PayPal Sandbox{sandbox ? "" : " (live mode misconfigured)"}
        </CardTitle>
        <CardDescription className="text-background/70">
          {configured
            ? "Request payment with an emailed PayPal invoice, or create a pay-now link. The buyer pays with a Sandbox account and PayPal confirms it back to Orbiz. Not a live charge."
            : "PayPal credentials are not configured. Use Mark paid (demo) offline, or set PAYPAL_CLIENT_ID / SECRET on the API."}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {!currencySupported ? (
          <p className="text-sm text-destructive" role="alert">
            PayPal Sandbox can&apos;t take {order.currency} payments. Use an
            order in USD to pay with PayPal.
          </p>
        ) : null}

        <PaypalInvoiceSection
          order={order}
          confirm={confirm}
          enabled={configured && currencySupported}
          onEmail={setEmailKind}
        />

        <div className="space-y-3 border-t border-background/15 pt-4">
          <p className="text-sm font-semibold text-background">Pay-now link</p>
          <p className="text-sm text-background/70">
            A short-lived PayPal checkout link for paying right away, such as in
            a chat. For paying later, request payment above.
          </p>

          {checkout ? (
            <div className="space-y-1 text-sm text-background/80">
              <p>
                Status:{" "}
                <span className="font-semibold text-primary">
                  {checkout.status}
                </span>
              </p>
              <p className="tabular-nums">
                {checkout.currency} {checkout.amount}
              </p>
              {request?.kind === "checkout" ? (
                <PaypalEmailStatus request={request} />
              ) : null}
              {checkout.last_error ? (
                <p className="text-sm text-destructive" role="alert">
                  {checkout.last_error}
                </p>
              ) : null}
            </div>
          ) : null}

          <div className="flex flex-wrap gap-2">
            {canRequestPayment(order) ? (
              <Button
                type="button"
                variant="outline"
                className={ON_INK_OUTLINE_BUTTON}
                disabled={busy || !configured || !currencySupported}
                onClick={() => {
                  void onCreate();
                }}
              >
                {createCheckout.isPending
                  ? "Creating…"
                  : checkout
                    ? "Create new pay-now link"
                    : "Create pay-now link"}
              </Button>
            ) : null}

            {approveUrl ? (
              <>
                <Button
                  type="button"
                  variant="outline"
                  className={ON_INK_OUTLINE_BUTTON}
                  disabled={busy}
                  onClick={onOpenApprove}
                >
                  Open approve link
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  className={ON_INK_OUTLINE_BUTTON}
                  disabled={busy}
                  onClick={() => {
                    void copyLink(approveUrl, "Checkout link");
                  }}
                >
                  Copy checkout link
                </Button>
              </>
            ) : null}

            {canEmailCheckout ? (
              <Button
                type="button"
                variant="outline"
                className={ON_INK_OUTLINE_BUTTON}
                disabled={busy}
                onClick={() => setEmailKind("request")}
              >
                {request?.last_email_status ? "Resend email" : "Email link"}
              </Button>
            ) : null}

            {checkout &&
            checkout.status !== "captured" &&
            order.payment_status !== "paid" ? (
              <Button
                type="button"
                variant="outline"
                className={ON_INK_OUTLINE_BUTTON}
                disabled={busy || !configured}
                onClick={() => {
                  void onCapture();
                }}
              >
                {captureCheckout.isPending ? "Capturing…" : "Capture payment"}
              </Button>
            ) : null}
          </div>
        </div>

        <PaypalRefundSection order={order} />
      </CardContent>

      <PaypalEmailDialog
        order={order}
        kind={emailKind ?? "request"}
        open={emailKind !== null}
        onOpenChange={(open) => {
          if (!open) setEmailKind(null);
        }}
      />
    </Card>
  );
}
