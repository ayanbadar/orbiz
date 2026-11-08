import { Navigate, useSearchParams } from "react-router-dom";

import { ROUTES } from "@/constants/routes";
import { AuthLayout } from "@/features/auth/components/auth-layout";
import { AuthLoading } from "@/features/auth/components/auth-loading";
import { useAuth } from "@/features/auth/context/use-auth";

/**
 * Where PayPal sends the payer after approving or cancelling a pay-now link.
 *
 * Public on purpose: a buyer paying from an emailed link has no Orbiz login. A signed-in
 * seller is forwarded to the order, where the return triggers the capture fallback.
 */
export function PaymentReturnPage() {
  const [searchParams] = useSearchParams();
  const { status } = useAuth();
  const orderId = Number(searchParams.get("order"));
  const cancelled = searchParams.get("paypal") === "cancel";

  if (status === "loading") {
    return <AuthLoading />;
  }

  if (status === "authenticated" && Number.isFinite(orderId) && orderId > 0) {
    const forward = new URLSearchParams(searchParams);
    forward.delete("order");
    return (
      <Navigate
        to={`${ROUTES.orders.detail(orderId)}?${forward.toString()}`}
        replace
      />
    );
  }

  return (
    <AuthLayout
      title={cancelled ? "Payment cancelled" : "Thank you"}
      subtitle={
        cancelled
          ? "No payment was taken."
          : "Your PayPal payment was approved."
      }
    >
      <div className="space-y-3 text-sm text-body" role="status">
        {cancelled ? (
          <p>
            You can open the payment link from your email again whenever you are
            ready to pay.
          </p>
        ) : (
          <p>
            The seller is told as soon as PayPal confirms the payment, so there
            is nothing else for you to do.
          </p>
        )}
        <p className="text-muted-foreground">
          If this was a PayPal Sandbox test, no real money moved. You can close
          this page.
        </p>
      </div>
    </AuthLayout>
  );
}
