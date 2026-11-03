import { useEffect, useRef } from "react";
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
import {
  useCapturePaypalCheckout,
  useCreatePaypalCheckout,
} from "@/features/payments/api/payments.api";
import type { Order } from "@/features/orders/types";

type Props = {
  order: Order;
  confirm: (options: ConfirmDialogOptions) => Promise<boolean>;
};

function canCreateCheckout(order: Order): boolean {
  if (order.fulfilment_status === "cancelled" || order.fulfilment_status === "draft") {
    return false;
  }
  if (order.payment_status === "paid") {
    return false;
  }
  return (
    order.payment_status === "pending" ||
    order.payment_status === "unpaid" ||
    order.payment_status === "failed" ||
    order.payment_status === "cancelled"
  );
}

export function PaypalSandboxCard({ order, confirm }: Props) {
  const [searchParams, setSearchParams] = useSearchParams();
  const createCheckout = useCreatePaypalCheckout(order.id);
  const captureCheckout = useCapturePaypalCheckout(order.id);
  const returnHandledRef = useRef(false);

  const checkout = order.paypal_checkout ?? null;
  const configured = order.paypal_configured ?? false;
  const sandbox = order.paypal_sandbox ?? true;
  const busy = createCheckout.isPending || captureCheckout.isPending;

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
      title: "Create PayPal Sandbox checkout?",
      description:
        "Opens a Sandbox approve link for this order total. This is not a live charge.",
      confirmLabel: "Create checkout",
    });
    if (!ok) return;
    try {
      const created = await createCheckout.mutateAsync();
      toast.success("PayPal Sandbox checkout created.");
      if (created.approve_url) {
        window.open(created.approve_url, "_blank", "noopener,noreferrer");
      }
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not create PayPal checkout."));
    }
  };

  const onOpenApprove = () => {
    if (!checkout?.approve_url) return;
    window.open(checkout.approve_url, "_blank", "noopener,noreferrer");
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
            ? "Create a Sandbox checkout, approve with a buyer account, then capture. Not a live charge."
            : "PayPal credentials are not configured. Use Mark paid (demo) offline, or set PAYPAL_CLIENT_ID / SECRET on the API."}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {checkout ? (
          <div className="space-y-1 text-sm text-background/80">
            <p>
              Status:{" "}
              <span className="font-semibold text-primary">{checkout.status}</span>
            </p>
            <p className="tabular-nums">
              {checkout.currency} {checkout.amount}
            </p>
            {checkout.last_error ? (
              <p className="text-sm text-destructive" role="alert">
                {checkout.last_error}
              </p>
            ) : null}
          </div>
        ) : null}

        <div className="flex flex-wrap gap-2">
          {canCreateCheckout(order) ? (
            <Button
              type="button"
              className="rounded-[24px]"
              disabled={busy || !configured}
              onClick={() => {
                void onCreate();
              }}
            >
              {createCheckout.isPending
                ? "Creating…"
                : checkout
                  ? "Create new checkout"
                  : "Create PayPal checkout"}
            </Button>
          ) : null}

          {checkout?.approve_url && checkout.status !== "captured" ? (
            <Button
              type="button"
              variant="outline"
              className="rounded-[24px] border-primary bg-transparent text-primary"
              disabled={busy}
              onClick={onOpenApprove}
            >
              Open approve link
            </Button>
          ) : null}

          {checkout &&
          checkout.status !== "captured" &&
          order.payment_status !== "paid" ? (
            <Button
              type="button"
              variant="outline"
              className="rounded-[24px] border-primary bg-transparent text-primary"
              disabled={busy || !configured}
              onClick={() => {
                void onCapture();
              }}
            >
              {captureCheckout.isPending ? "Capturing…" : "Capture payment"}
            </Button>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}
