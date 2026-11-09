import {
  AlertTriangle,
  Receipt,
  ShoppingBag,
  UserPlus,
  Wallet,
} from "lucide-react";
import { useCallback, useState } from "react";
import { Link } from "react-router-dom";

import { FormattedTime } from "@/components/formatted-time";
import { QueryState } from "@/components/query-state";
import { StatusBadge, STATUS_TONES } from "@/components/status-badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ROUTES } from "@/constants/routes";
import { getErrorMessage } from "@/features/auth/utils/form-errors";
import { useStoreDashboard } from "@/features/dashboard/api/dashboard.api";
import {
  BreakdownChart,
  type BreakdownSlice,
} from "@/features/dashboard/components/breakdown-chart";
import { ChartCard } from "@/features/dashboard/components/chart-card";
import { DashboardHeader } from "@/features/dashboard/components/dashboard-header";
import {
  KpiTile,
  KpiTileSkeleton,
} from "@/features/dashboard/components/kpi-tile";
import { SegmentedControl } from "@/features/dashboard/components/segmented-control";
import { TrendChart } from "@/features/dashboard/components/trend-chart";
import { useDashboardRange } from "@/features/dashboard/hooks/use-dashboard-range";
import { CHART_COLORS } from "@/features/dashboard/utils/chart-theme";
import { formatCount, formatMoney } from "@/features/dashboard/utils/format";
import { OrderStatusBadge } from "@/features/orders/components/order-status-badge";
import { PaymentStatusBadge } from "@/features/orders/components/payment-status-badge";
import {
  getFulfilmentLabel,
  getPaymentLabel,
} from "@/features/orders/utils/order-status";

type Metric = "revenue" | "orders";
type Breakdown = "fulfilment" | "payment";

const METRIC_OPTIONS = [
  { value: "revenue", label: "Revenue" },
  { value: "orders", label: "Orders" },
] as const;

const BREAKDOWN_OPTIONS = [
  { value: "fulfilment", label: "Fulfilment" },
  { value: "payment", label: "Payment" },
] as const;

/** A thin bar showing `value` as a share of `max`. */
function ShareBar({ value, max }: { value: number; max: number }) {
  const width = max > 0 ? Math.max(4, Math.round((value / max) * 100)) : 0;
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-secondary">
      <div
        className="h-full rounded-full transition-[width] duration-500"
        style={{ width: `${width}%`, backgroundColor: CHART_COLORS.forest }}
      />
    </div>
  );
}

/** Sales, orders, customers and stock for the signed-in user's store. */
export function StoreDashboardPage() {
  const [range, setRange] = useDashboardRange();
  const [metric, setMetric] = useState<Metric>("revenue");
  const [breakdown, setBreakdown] = useState<Breakdown>("fulfilment");
  const query = useStoreDashboard(range);
  const data = query.data;
  const currency = data?.currency ?? "USD";

  const money = useCallback(
    (value: number | string) => formatMoney(value, currency),
    [currency],
  );

  const revenueTrend = (data?.series ?? []).map((p) => Number(p.revenue));
  const ordersTrend = (data?.series ?? []).map((p) => p.orders);
  const averageTrend = (data?.series ?? []).map((p) =>
    p.orders > 0 ? Number(p.revenue) / p.orders : 0,
  );

  const slices: BreakdownSlice[] =
    breakdown === "fulfilment"
      ? (data?.orders_by_fulfilment ?? []).map((row) => ({
          label: getFulfilmentLabel(row.status),
          count: row.count,
        }))
      : (data?.orders_by_payment ?? []).map((row) => ({
          label: getPaymentLabel(row.status),
          count: row.count,
        }));

  const topMax = Math.max(
    0,
    ...(data?.top_products ?? []).map((p) => Number(p.revenue)),
  );

  return (
    <div className="space-y-5">
      <DashboardHeader
        title="Dashboard"
        subtitle={
          data ? (
            <>
              <Link
                to={ROUTES.orders.root()}
                className="font-semibold text-foreground underline-offset-4 hover:underline"
              >
                {formatCount(data.open_orders)} open{" "}
                {data.open_orders === 1 ? "order" : "orders"}
              </Link>{" "}
              waiting to be completed.
            </>
          ) : (
            "How your store is doing."
          )
        }
        range={range}
        onRangeChange={(next) => void setRange(next)}
        onRefresh={() => void query.refetch()}
        isFetching={query.isFetching}
        updatedAt={query.dataUpdatedAt}
      />

      <QueryState
        isError={query.isError && !data}
        errorMessage={getErrorMessage(
          query.error,
          "Failed to load the dashboard.",
        )}
        onRetry={() => {
          void query.refetch();
        }}
      >
        <div
          className="grid animate-in gap-4 duration-300 fade-in sm:grid-cols-2 xl:grid-cols-4"
          aria-busy={query.isFetching || undefined}
        >
          {data ? (
            <>
              <KpiTile
                label="Revenue"
                icon={Wallet}
                value={money(data.kpis.revenue.value)}
                delta={{
                  current: data.kpis.revenue.value,
                  previous: data.kpis.revenue.previous,
                }}
                trend={revenueTrend}
              />
              <KpiTile
                label="Orders"
                icon={ShoppingBag}
                value={formatCount(data.kpis.orders.value)}
                delta={{
                  current: data.kpis.orders.value,
                  previous: data.kpis.orders.previous,
                }}
                trend={ordersTrend}
              />
              <KpiTile
                label="Average order value"
                icon={Receipt}
                value={money(data.kpis.average_order_value.value)}
                delta={{
                  current: data.kpis.average_order_value.value,
                  previous: data.kpis.average_order_value.previous,
                }}
                trend={averageTrend}
              />
              <KpiTile
                label="New customers"
                icon={UserPlus}
                value={formatCount(data.kpis.new_customers.value)}
                delta={{
                  current: data.kpis.new_customers.value,
                  previous: data.kpis.new_customers.previous,
                }}
              />
            </>
          ) : (
            Array.from({ length: 4 }, (_, index) => (
              <KpiTileSkeleton key={index} />
            ))
          )}
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <ChartCard
            title="Sales overview"
            description={
              metric === "revenue"
                ? "Paid orders, per day"
                : "Orders placed, per day"
            }
            isLoading={!data}
            className="lg:col-span-2"
            action={
              <SegmentedControl
                label="Chart metric"
                value={metric}
                onChange={setMetric}
                options={METRIC_OPTIONS}
              />
            }
          >
            <TrendChart
              key={metric}
              name={metric === "revenue" ? "Revenue" : "Orders"}
              formatValue={
                metric === "revenue"
                  ? money
                  : (value) => String(Math.round(value))
              }
              color={
                metric === "revenue"
                  ? CHART_COLORS.forest
                  : CHART_COLORS.positive
              }
              data={(data?.series ?? []).map((point) => ({
                date: point.date,
                value:
                  metric === "revenue" ? Number(point.revenue) : point.orders,
              }))}
            />
          </ChartCard>

          <ChartCard
            title="Order breakdown"
            isLoading={!data}
            isEmpty={slices.length === 0}
            emptyMessage="Orders will appear here once you have some."
            action={
              <SegmentedControl
                label="Breakdown"
                value={breakdown}
                onChange={setBreakdown}
                options={BREAKDOWN_OPTIONS}
              />
            }
          >
            <BreakdownChart key={breakdown} data={slices} />
          </ChartCard>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <ChartCard
            title="Top products"
            description="By paid revenue"
            isLoading={!data}
            isEmpty={data?.top_products.length === 0}
            emptyMessage="No paid sales in this period."
          >
            <ol className="space-y-4">
              {data?.top_products.map((product, index) => (
                <li key={product.product_id} className="space-y-1.5">
                  <div className="flex items-center justify-between gap-3 text-sm">
                    <div className="flex min-w-0 items-center gap-3">
                      <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-semibold text-accent-foreground">
                        {index + 1}
                      </span>
                      <div className="min-w-0">
                        <p className="truncate font-semibold">{product.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {product.sku} · {formatCount(product.quantity)} sold
                        </p>
                      </div>
                    </div>
                    <span className="font-semibold">
                      {money(product.revenue)}
                    </span>
                  </div>
                  <ShareBar value={Number(product.revenue)} max={topMax} />
                </li>
              ))}
            </ol>
          </ChartCard>

          <ChartCard
            title="Low stock"
            description="Active products at or below their alert level"
            isLoading={!data}
            isEmpty={data?.low_stock.length === 0}
            emptyMessage="Every product is well stocked."
          >
            <ul className="space-y-1">
              {data?.low_stock.map((product) => {
                const out = product.stock_quantity === 0;
                return (
                  <li key={product.id}>
                    <Link
                      to={ROUTES.products.detail(product.id)}
                      className="flex items-center justify-between gap-3 rounded-xl p-2 text-sm transition-colors hover:bg-secondary"
                    >
                      <div className="flex min-w-0 items-center gap-3">
                        <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-warning/30 text-warning-content">
                          <AlertTriangle className="size-4" aria-hidden />
                        </span>
                        <div className="min-w-0">
                          <p className="truncate font-semibold">
                            {product.name}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {product.sku} · alert at{" "}
                            {product.low_stock_threshold}
                          </p>
                        </div>
                      </div>
                      <StatusBadge
                        toneClassName={
                          out ? STATUS_TONES.negative : STATUS_TONES.warning
                        }
                      >
                        {out
                          ? "Out of stock"
                          : `${product.stock_quantity} left`}
                      </StatusBadge>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </ChartCard>
        </div>

        <ChartCard
          title="Recent orders"
          isLoading={!data}
          isEmpty={data?.recent_orders.length === 0}
          emptyMessage="Orders you create will show up here."
          action={
            <Link
              to={ROUTES.orders.root()}
              className="text-sm font-semibold underline-offset-4 hover:underline"
            >
              View all
            </Link>
          }
        >
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead>Order</TableHead>
                <TableHead>Customer</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Payment</TableHead>
                <TableHead className="text-right">Total</TableHead>
                <TableHead>Placed</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.recent_orders.map((order) => (
                <TableRow key={order.id}>
                  <TableCell className="font-semibold">
                    <Link
                      to={ROUTES.orders.detail(order.id)}
                      className="hover:underline"
                    >
                      {order.number}
                    </Link>
                  </TableCell>
                  <TableCell>{order.customer_name}</TableCell>
                  <TableCell>
                    <OrderStatusBadge status={order.fulfilment_status} />
                  </TableCell>
                  <TableCell>
                    <PaymentStatusBadge status={order.payment_status} />
                  </TableCell>
                  <TableCell className="text-right font-semibold">
                    {formatMoney(order.total, order.currency)}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    <FormattedTime value={order.created_at} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </ChartCard>
      </QueryState>
    </div>
  );
}
