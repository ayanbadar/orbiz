import {
  ChevronRight,
  ClipboardList,
  Mail,
  Pencil,
  Phone,
  StickyNote,
  UserRound,
} from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";

import { FormattedTime } from "@/components/formatted-time";
import { PageBackLink } from "@/components/page-back-link";
import { QueryState } from "@/components/query-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ROUTES } from "@/constants/routes";
import { getErrorMessage } from "@/features/auth/utils/form-errors";
import { EditCustomerDialog } from "@/features/customers/components/edit-customer-dialog";
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
        errorMessage={getErrorMessage(
          customerQuery.error,
          "Customer not found.",
        )}
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

function CustomerProfile({ customer }: { customer: CustomerSummary }) {
  const [editOpen, setEditOpen] = useState(false);

  return (
    <>
      <EditCustomerDialog
        customer={customer}
        open={editOpen}
        onOpenChange={setEditOpen}
      />
      <header className="overflow-hidden rounded-[24px] bg-card ring-1 ring-border">
        <div className="flex flex-wrap items-center justify-between gap-4 p-6">
          <div className="flex min-w-0 items-center gap-4">
            <span
              aria-hidden
              className="grid size-16 shrink-0 place-items-center rounded-full bg-primary text-xl font-semibold text-primary-foreground"
            >
              {initials(customer.name)}
            </span>
            <div className="min-w-0 space-y-2">
              <h1 className="truncate text-[28px] leading-none font-semibold tracking-tight text-foreground sm:text-[32px]">
                {customer.name}
              </h1>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-body">
                {customer.email ? (
                  <a
                    href={`mailto:${customer.email}`}
                    className="inline-flex items-center gap-1.5 hover:underline"
                  >
                    <Mail className="size-4" aria-hidden />
                    {customer.email}
                  </a>
                ) : null}
                {customer.phone ? (
                  <a
                    href={`tel:${customer.phone}`}
                    className="inline-flex items-center gap-1.5 hover:underline"
                  >
                    <Phone className="size-4" aria-hidden />
                    {customer.phone}
                  </a>
                ) : null}
              </div>
            </div>
          </div>
          <Button
            type="button"
            variant="secondary"
            size="cta"
            onClick={() => setEditOpen(true)}
          >
            <Pencil className="size-4" aria-hidden />
            Edit
          </Button>
        </div>

        <dl className="grid grid-cols-2 divide-x divide-y divide-border border-t border-border bg-muted/40 sm:grid-cols-4 sm:divide-y-0">
          <Stat label="Orders">
            <span className="text-lg font-semibold tabular-nums">
              {customer.order_count}
            </span>
          </Stat>
          <Stat label="Open orders">
            <span className="text-lg font-semibold tabular-nums">
              {customer.open_order_count}
            </span>
          </Stat>
          <Stat label="Last order">
            {customer.last_order_at ? (
              <FormattedTime
                value={customer.last_order_at}
                variant="relative"
                className="text-sm font-medium"
              />
            ) : (
              <span className="text-sm text-muted-foreground">None yet</span>
            )}
          </Stat>
          <Stat label="Customer since">
            <FormattedTime
              value={customer.created_at}
              variant="date"
              className="text-sm font-medium"
            />
          </Stat>
        </dl>
      </header>

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <RecentOrders customer={customer} />

        <aside className="space-y-6">
          <Card className="rounded-[24px] ring-1 ring-border">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <UserRound
                  className="size-4 text-muted-foreground"
                  aria-hidden
                />
                Contact
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              {customer.email ? (
                <a
                  href={`mailto:${customer.email}`}
                  className="flex items-center gap-2 break-all text-foreground hover:underline"
                >
                  <Mail
                    className="size-4 shrink-0 text-muted-foreground"
                    aria-hidden
                  />
                  {customer.email}
                </a>
              ) : (
                <p className="rounded-xl bg-muted/50 p-3 text-muted-foreground">
                  No email yet. Add one to send PayPal payment links and order
                  confirmations.
                </p>
              )}
              {customer.phone ? (
                <a
                  href={`tel:${customer.phone}`}
                  className="flex items-center gap-2 text-foreground hover:underline"
                >
                  <Phone
                    className="size-4 shrink-0 text-muted-foreground"
                    aria-hidden
                  />
                  {customer.phone}
                </a>
              ) : null}
            </CardContent>
          </Card>

          <Card className="rounded-[24px] ring-1 ring-border">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <StickyNote
                  className="size-4 text-muted-foreground"
                  aria-hidden
                />
                Internal notes
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm">
              {customer.notes ? (
                <p className="rounded-xl bg-muted/50 p-3 whitespace-pre-wrap text-foreground">
                  {customer.notes}
                </p>
              ) : (
                <p className="text-muted-foreground">No notes yet.</p>
              )}
            </CardContent>
          </Card>
        </aside>
      </div>
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
    <Card className="min-w-0 rounded-[24px] ring-1 ring-border">
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <ClipboardList
              className="size-4 text-muted-foreground"
              aria-hidden
            />
            Recent orders
          </CardTitle>
          {customer.order_count > 0 ? (
            <Link
              to={ROUTES.orders.forCustomer(customer.id)}
              className="text-sm font-semibold text-foreground underline-offset-4 hover:underline"
            >
              View all {customer.order_count}
            </Link>
          ) : null}
        </div>
      </CardHeader>
      <CardContent>
        <QueryState
          isLoading={ordersQuery.isLoading}
          isError={ordersQuery.isError}
          errorMessage={getErrorMessage(
            ordersQuery.error,
            "Failed to load orders.",
          )}
          onRetry={() => {
            void ordersQuery.refetch();
          }}
        >
          {orders.length === 0 ? (
            <div className="flex flex-col items-center gap-2 rounded-2xl bg-muted/50 px-4 py-10 text-center">
              <ClipboardList
                className="size-8 text-muted-foreground"
                aria-hidden
              />
              <p className="font-semibold">No orders yet</p>
              <p className="text-sm text-muted-foreground">
                Orders you create for {customer.name} show here.
              </p>
            </div>
          ) : (
            <ul className="divide-y divide-border">
              {orders.map((order) => (
                <li key={order.id}>
                  <Link
                    to={ROUTES.orders.detail(order.id)}
                    className="-mx-2 flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl px-2 py-3 text-sm transition-colors hover:bg-muted/60"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold">{order.number}</p>
                      <FormattedTime
                        value={order.created_at}
                        variant="relative"
                        className="text-xs text-muted-foreground"
                      />
                    </div>
                    <span className="flex flex-wrap items-center gap-2">
                      <OrderStatusBadge status={order.fulfilment_status} />
                      <PaymentStatusBadge status={order.payment_status} />
                    </span>
                    <span className="min-w-24 text-right font-semibold tabular-nums">
                      {order.currency} {order.total}
                    </span>
                    <ChevronRight
                      className="size-4 text-muted-foreground"
                      aria-hidden
                    />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </QueryState>
      </CardContent>
    </Card>
  );
}
