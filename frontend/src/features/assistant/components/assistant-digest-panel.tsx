import { Link } from "react-router-dom";

import { QueryState } from "@/components/query-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "@/components/ui/sonner";
import { ROUTES } from "@/constants/routes";
import { useAssistantDigest } from "@/features/assistant/api/assistant.api";
import { getErrorMessage } from "@/features/auth/utils/form-errors";
import { useEmailPaymentLink } from "@/features/payments/api/payments.api";

/**
 * Pure render of GET /assistant/digest/ — no LLM call. "Send reminder now" calls the
 * *existing* payments endpoint directly, the same one the order-detail PayPal card
 * uses, so this is a real human click and correctly stays attributed to the seller.
 */
function ReminderButton({ orderId }: { orderId: number }) {
  const emailLink = useEmailPaymentLink(orderId);

  const handleClick = async () => {
    try {
      await emailLink.mutateAsync({ kind: "reminder" });
      toast.success("Reminder sent.");
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not send the reminder."));
    }
  };

  return (
    <Button size="sm" variant="outline" onClick={handleClick} disabled={emailLink.isPending}>
      {emailLink.isPending ? "Sending…" : "Send reminder now"}
    </Button>
  );
}

export function AssistantDigestPanel() {
  const digest = useAssistantDigest();

  return (
    <QueryState
      isLoading={digest.isPending}
      isError={digest.isError}
      isEmpty={
        !digest.isPending &&
        !digest.isError &&
        (digest.data?.stale_unpaid_orders.length ?? 0) === 0 &&
        (digest.data?.low_stock_products.length ?? 0) === 0
      }
      errorMessage="Couldn't load today's digest."
      emptyMessage="Nothing needs attention right now."
    >
      <div className="space-y-4">
        {digest.data?.stale_unpaid_orders.length ? (
          <Card>
            <CardHeader>
              <CardTitle>Awaiting payment</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {digest.data.stale_unpaid_orders.map((row) => (
                <div
                  key={row.order_id}
                  className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3 text-sm last:border-0 last:pb-0"
                >
                  <div>
                    <Link
                      to={ROUTES.orders.detail(row.order_id)}
                      className="font-medium text-foreground underline-offset-4 hover:underline"
                    >
                      {row.order_number}
                    </Link>
                    <p className="text-muted-foreground">
                      {row.customer_name} · {row.currency} {row.total} · {row.days_old}d unpaid
                    </p>
                  </div>
                  <ReminderButton orderId={row.order_id} />
                </div>
              ))}
            </CardContent>
          </Card>
        ) : null}

        {digest.data?.low_stock_products.length ? (
          <Card>
            <CardHeader>
              <CardTitle>Low stock</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {digest.data.low_stock_products.map((row) => (
                <div key={row.sku} className="flex items-center justify-between text-sm">
                  <span>
                    {row.name} ({row.sku})
                  </span>
                  <span className="text-muted-foreground">
                    {row.stock_quantity} left (threshold {row.low_stock_threshold})
                  </span>
                </div>
              ))}
            </CardContent>
          </Card>
        ) : null}
      </div>
    </QueryState>
  );
}
