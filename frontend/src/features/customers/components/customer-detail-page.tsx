import { Link, useParams } from "react-router-dom";

import { FormattedTime } from "@/components/formatted-time";
import { PageBackLink } from "@/components/page-back-link";
import { QueryState } from "@/components/query-state";
import { StatTile } from "@/components/stat-tile";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ROUTES } from "@/constants/routes";
import { getErrorMessage } from "@/features/auth/utils/form-errors";
import { useCustomer } from "@/features/customers/api/customers.api";
import type { CustomerSummary } from "@/features/customers/types";
import { useOrders } from "@/features/orders/api/orders.api";
import { OrderStatusBadge } from "@/features/orders/components/order-status-badge";
import { PaymentStatusBadge } from "@/features/orders/components/payment-status-badge";

/** The profile previews the latest orders; the full history is the Orders grid. */
const RECENT_ORDER_COUNT = 5;

export function CustomerDetailPage() {
  const { id } = useParams();
  const customerId = Number(id);
  const customerQuery = useCustomer(customerId);
  const customer = customerQuery.data;

  return (
    <div className="space-y-6">
      <PageBackLink to={ROUTES.customers.root()}>Customers</PageBackLink>

      <QueryState
        isLoading={customerQuery.isLoading}
        isError={customerQuery.isError}
        errorMessage={getErrorMessage(customerQuery.error, "Customer not found.")}
        onRetry={() => {
          void customerQuery.refetch();
        }}
        isEmpty={!customer}
        emptyMessage="Customer not found."
      >
        {customer ? <CustomerProfile customer={customer} /> : null}
      </QueryState>
    </div>
  );
}

function CustomerProfile({ customer }: { customer: CustomerSummary }) {
  const contact = [customer.email, customer.phone].filter(Boolean).join(" · ");

  return (
    <>
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 space-y-1.5">
          <h1 className="text-[28px] font-semibold tracking-tight text-foreground sm:text-[32px]">
            {customer.name}
          </h1>
          {contact ? <p className="text-body">{contact}</p> : null}
        </div>
        <Button asChild variant="secondary" size="cta">
          <Link to={ROUTES.customers.edit(customer.id)}>Edit</Link>
        </Button>
      </header>

      <div className="grid gap-3 sm:grid-cols-3">
        <StatTile
          label="Orders"
          value={String(customer.order_count)}
          valueClassName="tabular-nums"
        />
        <StatTile
          label="Last order"
          value={
            customer.last_order_at ? (
              <FormattedTime value={customer.last_order_at} variant="relative" />
            ) : (
              "None yet"
            )
          }
        />
        <StatTile
          label="Customer since"
          value={<FormattedTime value={customer.created_at} variant="date" />}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card className="rounded-[24px] ring-0">
          <CardHeader>
            <CardTitle>Contact</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            {customer.email ? (
              <a
                href={`mailto:${customer.email}`}
                className="block text-foreground underline-offset-4 hover:underline"
              >
                {customer.email}
              </a>
            ) : (
              <p className="text-muted-foreground">
                No email yet. Add one to send PayPal payment links and order
                confirmations.
              </p>
            )}
            {customer.phone ? (
              <a
                href={`tel:${customer.phone}`}
                className="block text-foreground underline-offset-4 hover:underline"
              >
                {customer.phone}
              </a>
            ) : null}
          </CardContent>
        </Card>
        <Card className="rounded-[24px] ring-0">
          <CardHeader>
            <CardTitle>Internal notes</CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            {customer.notes ? (
              <p className="whitespace-pre-wrap text-body">{customer.notes}</p>
            ) : (
              <p className="text-muted-foreground">No notes yet.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <RecentOrders customer={customer} />
    </>
  );
}

function RecentOrders({ customer }: { customer: CustomerSummary }) {
  const ordersQuery = useOrders({
    customer_id: customer.id,
    page_size: RECENT_ORDER_COUNT,
    ordering: "-created_at",
  });
  const orders = ordersQuery.data?.results ?? [];

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">Recent orders</h2>
        {customer.order_count > 0 ? (
          <Link
            to={ROUTES.orders.forCustomer(customer.id)}
            className="text-sm font-semibold text-foreground underline-offset-4 hover:underline"
          >
            View all {customer.order_count} in Orders
          </Link>
        ) : null}
      </div>
      <QueryState
        isLoading={ordersQuery.isLoading}
        isError={ordersQuery.isError}
        errorMessage={getErrorMessage(ordersQuery.error, "Failed to load orders.")}
        onRetry={() => {
          void ordersQuery.refetch();
        }}
      >
        {orders.length === 0 ? (
          <Card className="rounded-[24px] ring-0">
            <CardHeader>
              <CardTitle>No orders yet</CardTitle>
              <CardDescription>
                Orders you create for {customer.name} show here.
              </CardDescription>
            </CardHeader>
          </Card>
        ) : (
          <ul className="space-y-2">
            {orders.map((order) => (
              <li key={order.id}>
                <Link
                  to={ROUTES.orders.detail(order.id)}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-[24px] bg-card px-4 py-3 text-sm ring-1 ring-border transition-colors hover:bg-muted/60"
                >
                  <span className="font-semibold">{order.number}</span>
                  <span className="flex flex-wrap items-center gap-2">
                    <OrderStatusBadge status={order.fulfilment_status} />
                    <PaymentStatusBadge status={order.payment_status} />
                  </span>
                  <span className="tabular-nums">
                    {order.currency} {order.total}
                  </span>
                  <FormattedTime
                    value={order.created_at}
                    variant="relative"
                    className="text-xs text-muted-foreground"
                  />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </QueryState>
    </section>
  );
}
