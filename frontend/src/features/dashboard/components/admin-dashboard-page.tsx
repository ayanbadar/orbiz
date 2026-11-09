import { Banknote, Store, CirclePlus, Users } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { QueryState } from "@/components/query-state";
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
import { usePlatformDashboard } from "@/features/dashboard/api/dashboard.api";
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

type Growth = "revenue" | "stores";
type Breakdown = "stores" | "subscriptions";

const GROWTH_OPTIONS = [
  { value: "revenue", label: "Revenue" },
  { value: "stores", label: "New stores" },
] as const;

const BREAKDOWN_OPTIONS = [
  { value: "stores", label: "Stores" },
  { value: "subscriptions", label: "Plans" },
] as const;

/** "past_due" → "Past due". */
function humanize(status: string): string {
  const text = status.replaceAll("_", " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function toSlices(rows: { status: string; count: number }[] | undefined) {
  return (rows ?? []).map((row): BreakdownSlice => ({
    label: humanize(row.status),
    count: row.count,
  }));
}

const cents = (value: number) => formatMoney(value / 100, "USD");

/** Platform-wide numbers for the super admin. */
export function AdminDashboardPage() {
  const [range, setRange] = useDashboardRange();
  const [growth, setGrowth] = useState<Growth>("revenue");
  const [breakdown, setBreakdown] = useState<Breakdown>("stores");
  const query = usePlatformDashboard(range);
  const data = query.data;

  const slices =
    breakdown === "stores"
      ? toSlices(data?.stores_by_status)
      : toSlices(data?.subscriptions_by_status);
  const activeStores =
    data?.stores_by_status.find((row) => row.status === "active")?.count ?? 0;

  return (
    <div className="space-y-5">
      <DashboardHeader
        title="Platform dashboard"
        subtitle="How Orbiz is doing across every store."
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
                label="Subscription revenue"
                icon={Banknote}
                value={cents(data.kpis.subscription_revenue_cents.value)}
                delta={{
                  current: data.kpis.subscription_revenue_cents.value,
                  previous: data.kpis.subscription_revenue_cents.previous,
                }}
                trend={data.series.map((p) => p.subscription_revenue_cents)}
              />
              <KpiTile
                label="New stores"
                icon={CirclePlus}
                value={formatCount(data.kpis.stores.value)}
                delta={{
                  current: data.kpis.stores.value,
                  previous: data.kpis.stores.previous,
                }}
                trend={data.series.map((p) => p.new_stores)}
              />
              <KpiTile
                label="Total stores"
                icon={Store}
                value={formatCount(data.totals.stores)}
                hint={`${formatCount(activeStores)} active`}
              />
              <KpiTile
                label="Users"
                icon={Users}
                value={formatCount(data.totals.users)}
                hint={`${formatCount(data.totals.active_users)} active`}
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
            title="Growth"
            description={
              growth === "revenue"
                ? "Subscription payments, per day"
                : "Stores created, per day"
            }
            isLoading={!data}
            className="lg:col-span-2"
            action={
              <SegmentedControl
                label="Chart metric"
                value={growth}
                onChange={setGrowth}
                options={GROWTH_OPTIONS}
              />
            }
          >
            <TrendChart
              key={growth}
              name={growth === "revenue" ? "Revenue" : "New stores"}
              formatValue={
                growth === "revenue"
                  ? cents
                  : (value) => String(Math.round(value))
              }
              color={
                growth === "revenue"
                  ? CHART_COLORS.forest
                  : CHART_COLORS.positive
              }
              data={(data?.series ?? []).map((point) => ({
                date: point.date,
                value:
                  growth === "revenue"
                    ? point.subscription_revenue_cents
                    : point.new_stores,
              }))}
            />
          </ChartCard>

          <ChartCard
            title="Status"
            isLoading={!data}
            isEmpty={slices.length === 0}
            action={
              <SegmentedControl
                label="Breakdown"
                value={breakdown}
                onChange={setBreakdown}
                options={BREAKDOWN_OPTIONS}
              />
            }
          >
            <BreakdownChart
              key={breakdown}
              data={slices}
              totalLabel={breakdown === "stores" ? "Stores" : "Plans"}
            />
          </ChartCard>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <ChartCard
            title="Orders by currency"
            description="Sales across all stores. Currencies are never added together."
            isLoading={!data}
            isEmpty={data?.orders_by_currency.length === 0}
            emptyMessage="No orders in this period."
          >
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Currency</TableHead>
                  <TableHead className="text-right">Stores</TableHead>
                  <TableHead className="text-right">Orders</TableHead>
                  <TableHead className="text-right">Paid revenue</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.orders_by_currency.map((row) => (
                  <TableRow key={row.currency}>
                    <TableCell className="font-semibold">
                      {row.currency}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatCount(row.stores)}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatCount(row.orders)}
                    </TableCell>
                    <TableCell className="text-right font-semibold">
                      {formatMoney(row.revenue ?? 0, row.currency)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </ChartCard>

          <ChartCard
            title="Top stores"
            description="By number of orders"
            isLoading={!data}
            isEmpty={data?.top_stores.length === 0}
            emptyMessage="No orders in this period."
            action={
              <Link
                to={ROUTES.admin.stores()}
                className="text-sm font-semibold underline-offset-4 hover:underline"
              >
                All stores
              </Link>
            }
          >
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Store</TableHead>
                  <TableHead className="text-right">Orders</TableHead>
                  <TableHead className="text-right">Paid revenue</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.top_stores.map((row) => (
                  <TableRow key={`${row.store_id}-${row.currency}`}>
                    <TableCell className="font-semibold">{row.name}</TableCell>
                    <TableCell className="text-right">
                      {formatCount(row.orders)}
                    </TableCell>
                    <TableCell className="text-right font-semibold">
                      {formatMoney(row.revenue, row.currency)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </ChartCard>
        </div>
      </QueryState>
    </div>
  );
}
