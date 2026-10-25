import { useNavigate, useParams } from "react-router-dom";

import { useConfirmDialog } from "@/components/confirm-dialog";
import { FormattedTime } from "@/components/formatted-time";
import { PageBackLink } from "@/components/page-back-link";
import { QueryState } from "@/components/query-state";
import { getErrorMessage } from "@/features/auth/utils/form-errors";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ROUTES } from "@/constants/routes";
import { useOrder } from "@/features/orders/api/orders.api";
import {
  getOrderActionState,
  OrderActions,
} from "@/features/orders/components/order-actions";
import { OrderStatusPair } from "@/features/orders/components/order-status-pair";
import { OrderTimeline } from "@/features/orders/components/order-timeline";

export function OrderDetailPage() {
  const { id } = useParams();
  const orderId = Number(id);
  const navigate = useNavigate();
  const { confirm, dialog: confirmDialog } = useConfirmDialog();
  const orderQuery = useOrder(orderId);
  const order = orderQuery.data;
  const actionState = order ? getOrderActionState(order) : null;

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      {confirmDialog}
      <PageBackLink to={ROUTES.orders.root()}>Back to orders</PageBackLink>

      <QueryState
        isLoading={orderQuery.isLoading}
        isError={orderQuery.isError}
        errorMessage={getErrorMessage(
          orderQuery.error,
          "Failed to load order.",
        )}
        onRetry={() => {
          void orderQuery.refetch();
        }}
      >
        {order && actionState ? (
          <>
            <header className="flex flex-wrap items-start justify-between gap-4">
              <div className="space-y-2">
                <h1 className="text-[28px] font-semibold tracking-tight sm:text-[32px]">
                  {order.number}
                </h1>
                <OrderStatusPair
                  fulfilmentStatus={order.fulfilment_status}
                  paymentStatus={order.payment_status}
                />
                <p className="text-sm text-muted-foreground">
                  Created{" "}
                  <FormattedTime value={order.created_at} variant="relative" />
                  {order.confirmed_at ? (
                    <>
                      {" · Confirmed "}
                      <FormattedTime
                        value={order.confirmed_at}
                        variant="relative"
                      />
                    </>
                  ) : null}
                </p>
                {actionState.needsPaidBeforeNext ? (
                  <p className="text-sm text-warning-content" role="status">
                    Payment must be paid before marking{" "}
                    {actionState.nextStatus?.replaceAll("_", " ")}.
                  </p>
                ) : null}
              </div>
              <OrderActions order={order} confirm={confirm} />
            </header>

            <div className="grid gap-4 sm:grid-cols-2">
              <Card className="rounded-[24px] ring-0">
                <CardHeader>
                  <CardTitle>Customer</CardTitle>
                  <CardDescription>{order.customer.name}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-1 text-sm text-muted-foreground">
                  {order.customer.email ? <p>{order.customer.email}</p> : null}
                  {order.customer.phone ? <p>{order.customer.phone}</p> : null}
                </CardContent>
              </Card>
              <Card className="rounded-[24px] ring-0">
                <CardHeader>
                  <CardTitle>Totals</CardTitle>
                  <CardDescription>
                    {order.currency} {order.total}
                  </CardDescription>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  Subtotal {order.currency} {order.subtotal}
                </CardContent>
              </Card>
            </div>

            <Card className="rounded-[24px] ring-0">
              <CardHeader>
                <CardTitle>Line items</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="divide-y divide-border">
                  {order.lines.map((line) => (
                    <li
                      key={line.id}
                      className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm"
                    >
                      <div>
                        <p className="font-semibold text-foreground">
                          {line.product_name}
                        </p>
                        <p className="text-muted-foreground">
                          {line.sku} · qty {line.quantity} · {order.currency}{" "}
                          {line.unit_price}
                        </p>
                      </div>
                      <p className="tabular-nums font-semibold">
                        {order.currency} {line.line_total}
                      </p>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>

            {order.delivery_notes ||
            order.source_message ||
            order.internal_notes ? (
              <Card className="rounded-[24px] ring-0">
                <CardHeader>
                  <CardTitle>Notes</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  {order.delivery_notes ? (
                    <div>
                      <p className="font-semibold">Delivery</p>
                      <p className="whitespace-pre-wrap text-muted-foreground">
                        {order.delivery_notes}
                      </p>
                    </div>
                  ) : null}
                  {order.source_message ? (
                    <div>
                      <p className="font-semibold">Customer message</p>
                      <p className="whitespace-pre-wrap text-muted-foreground">
                        {order.source_message}
                      </p>
                    </div>
                  ) : null}
                  {order.internal_notes ? (
                    <div>
                      <p className="font-semibold">Internal</p>
                      <p className="whitespace-pre-wrap text-muted-foreground">
                        {order.internal_notes}
                      </p>
                    </div>
                  ) : null}
                </CardContent>
              </Card>
            ) : null}

            <Card className="rounded-[24px] bg-foreground text-background ring-0">
              <CardHeader>
                <CardTitle className="text-primary">PayPal Sandbox</CardTitle>
                <CardDescription className="text-background/70">
                  Real checkout attaches in §2.7. Until then use{" "}
                  <span className="text-primary">Mark paid (demo)</span> to
                  unlock fulfilment. Abandon payment leaves the order
                  unfulfilled without restoring stock.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button
                  type="button"
                  variant="outline"
                  className="rounded-[24px] border-primary bg-transparent text-primary"
                  disabled
                >
                  Create PayPal checkout — coming in Payments
                </Button>
              </CardContent>
            </Card>

            <section className="space-y-3">
              <h2 className="text-lg font-semibold">Activity</h2>
              <OrderTimeline events={order.events ?? []} />
            </section>

            <div className="flex gap-3">
              <Button
                type="button"
                variant="outline"
                className="rounded-[24px]"
                onClick={() => navigate(ROUTES.orders.root())}
              >
                Back to list
              </Button>
            </div>
          </>
        ) : null}
      </QueryState>
    </div>
  );
}
