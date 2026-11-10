import {
  AlertCircle,
  History,
  Mail,
  Package,
  Phone,
  StickyNote,
  UserRound,
} from "lucide-react";
import type { ReactNode } from "react";
import { Link, useParams } from "react-router-dom";

import { useConfirmDialog } from "@/components/confirm-dialog";
import { FormattedTime } from "@/components/formatted-time";
import { PageBackLink } from "@/components/page-back-link";
import { QueryState } from "@/components/query-state";
import { getErrorMessage } from "@/features/auth/utils/form-errors";
import {
  Card,
  CardContent,
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
import { Can } from "@/features/auth/components/can";
import { PaypalSandboxCard } from "@/features/orders/components/paypal-sandbox-card";

function Stat({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="space-y-1 px-6 py-4">
      <dt className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
        {label}
      </dt>
      <dd>{children}</dd>
    </div>
  );
}

function initials(name: string) {
  return (
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join("") || "?"
  );
}

export function OrderDetailPage() {
  const { id } = useParams();
  const orderId = Number(id);
  const { confirm, dialog: confirmDialog } = useConfirmDialog();
  const orderQuery = useOrder(orderId);
  const order = orderQuery.data;
  const itemCount =
    order?.lines.reduce((n, l) => n + Number(l.quantity), 0) ?? 0;
  const actionState = order ? getOrderActionState(order) : null;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
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
            <header className="overflow-hidden rounded-[24px] bg-card ring-1 ring-border">
              <div className="flex flex-wrap items-start justify-between gap-4 p-6">
                <div className="space-y-3">
                  <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                    Order
                  </p>
                  <h1 className="text-[30px] leading-none font-semibold tracking-tight sm:text-[36px]">
                    {order.number}
                  </h1>
                  <OrderStatusPair
                    fulfilmentStatus={order.fulfilment_status}
                    paymentStatus={order.payment_status}
                  />
                  {actionState.needsPaidBeforeNext ? (
                    <p
                      className="flex items-center gap-2 rounded-lg bg-warning/15 px-3 py-2 text-sm font-medium text-warning-content"
                      role="status"
                    >
                      <AlertCircle className="size-4 shrink-0" aria-hidden />
                      Payment must be paid before marking{" "}
                      {actionState.nextStatus?.replaceAll("_", " ")}.
                    </p>
                  ) : null}
                </div>
                <Can permission="orders.update">
                  <OrderActions order={order} confirm={confirm} />
                </Can>
              </div>

              <dl className="grid grid-cols-2 divide-x divide-y divide-border border-t border-border bg-muted/40 sm:grid-cols-4 sm:divide-y-0">
                <Stat label="Total">
                  <span className="text-lg font-semibold tabular-nums">
                    {order.currency} {order.total}
                  </span>
                </Stat>
                <Stat label="Items">
                  <span className="text-lg font-semibold tabular-nums">
                    {itemCount}
                  </span>
                </Stat>
                <Stat label="Created">
                  <FormattedTime
                    value={order.created_at}
                    variant="relative"
                    className="text-sm font-medium"
                  />
                </Stat>
                <Stat label="Confirmed">
                  {order.confirmed_at ? (
                    <FormattedTime
                      value={order.confirmed_at}
                      variant="relative"
                      className="text-sm font-medium"
                    />
                  ) : (
                    <span className="text-sm text-muted-foreground">
                      Not yet
                    </span>
                  )}
                </Stat>
              </dl>
            </header>

            <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
              <div className="min-w-0 space-y-6">
                <Card className="rounded-[24px] ring-1 ring-border">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                      <Package
                        className="size-4 text-muted-foreground"
                        aria-hidden
                      />
                      Line items
                      <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-semibold text-muted-foreground">
                        {order.lines.length}
                      </span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="divide-y divide-border">
                      {order.lines.map((line) => (
                        <li
                          key={line.id}
                          className="flex items-center gap-4 py-4 first:pt-0"
                        >
                          <span
                            aria-hidden
                            className="grid size-11 shrink-0 place-items-center rounded-xl bg-muted text-muted-foreground"
                          >
                            <Package className="size-5" />
                          </span>
                          <div className="min-w-0 flex-1">
                            <p className="truncate font-semibold text-foreground">
                              {line.product_name}
                            </p>
                            <p className="truncate text-xs text-muted-foreground">
                              SKU {line.sku}
                            </p>
                            <p className="mt-1 text-sm text-muted-foreground tabular-nums">
                              {line.quantity} × {order.currency}{" "}
                              {line.unit_price}
                            </p>
                          </div>
                          <p className="shrink-0 text-base font-semibold tabular-nums">
                            {order.currency} {line.line_total}
                          </p>
                        </li>
                      ))}
                    </ul>
                    <dl className="mt-2 space-y-2 rounded-2xl bg-muted/50 p-4 text-sm">
                      <div className="flex justify-between text-muted-foreground">
                        <dt>Subtotal</dt>
                        <dd className="tabular-nums">
                          {order.currency} {order.subtotal}
                        </dd>
                      </div>
                      <div className="flex justify-between border-t border-border pt-2 text-base font-semibold">
                        <dt>Total</dt>
                        <dd className="tabular-nums">
                          {order.currency} {order.total}
                        </dd>
                      </div>
                    </dl>
                  </CardContent>
                </Card>

                <PaypalSandboxCard order={order} confirm={confirm} />

                <Card className="rounded-[24px] ring-1 ring-border">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                      <History
                        className="size-4 text-muted-foreground"
                        aria-hidden
                      />
                      Activity
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <OrderTimeline events={order.events ?? []} />
                  </CardContent>
                </Card>
              </div>

              <aside className="space-y-6 lg:sticky lg:top-6">
                <Card className="rounded-[24px] ring-1 ring-border">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                      <UserRound
                        className="size-4 text-muted-foreground"
                        aria-hidden
                      />
                      Customer
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center gap-3">
                      <span
                        aria-hidden
                        className="grid size-11 shrink-0 place-items-center rounded-full bg-primary text-sm font-semibold text-primary-foreground"
                      >
                        {initials(order.customer.name)}
                      </span>
                      <Link
                        to={ROUTES.customers.detail(order.customer.id)}
                        className="min-w-0 truncate font-semibold text-foreground underline-offset-4 hover:underline"
                      >
                        {order.customer.name}
                      </Link>
                    </div>
                    {order.customer.email || order.customer.phone ? (
                      <ul className="space-y-2 border-t border-border pt-3 text-sm text-muted-foreground">
                        {order.customer.email ? (
                          <li className="flex items-center gap-2">
                            <Mail className="size-4 shrink-0" aria-hidden />
                            <span className="min-w-0 break-all">
                              {order.customer.email}
                            </span>
                          </li>
                        ) : null}
                        {order.customer.phone ? (
                          <li className="flex items-center gap-2">
                            <Phone className="size-4 shrink-0" aria-hidden />
                            {order.customer.phone}
                          </li>
                        ) : null}
                      </ul>
                    ) : null}
                  </CardContent>
                </Card>

                {order.delivery_notes ||
                order.source_message ||
                order.internal_notes ? (
                  <Card className="rounded-[24px] ring-1 ring-border">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2 text-base">
                        <StickyNote
                          className="size-4 text-muted-foreground"
                          aria-hidden
                        />
                        Notes
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3 text-sm">
                      {[
                        ["Delivery", order.delivery_notes],
                        ["Customer message", order.source_message],
                        ["Internal", order.internal_notes],
                      ].map(([label, text]) =>
                        text ? (
                          <div
                            key={label}
                            className="rounded-xl bg-muted/50 p-3"
                          >
                            <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                              {label}
                            </p>
                            <p className="mt-1 whitespace-pre-wrap text-foreground">
                              {text}
                            </p>
                          </div>
                        ) : null,
                      )}
                    </CardContent>
                  </Card>
                ) : null}
              </aside>
            </div>
          </>
        ) : null}
      </QueryState>
    </div>
  );
}
