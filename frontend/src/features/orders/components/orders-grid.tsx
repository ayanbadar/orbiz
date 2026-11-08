import type {
  ColDef,
  FilterModel,
  ICellRendererParams,
} from "ag-grid-community";
import { useMemo } from "react";

import { DataGrid } from "@/components/data-grid";
import { FormattedTime } from "@/components/formatted-time";
import { ROUTES } from "@/constants/routes";
import { OrderStatusBadge } from "@/features/orders/components/order-status-badge";
import { PaymentStatusBadge } from "@/features/orders/components/payment-status-badge";
import type { OrderListItem, OrderListOrdering } from "@/features/orders/types";
import {
  getFulfilmentLabel,
  getPaymentLabel,
} from "@/features/orders/utils/order-status";
import { useServerGrid } from "@/hooks/use-server-grid";
import { formatRelativeTime } from "@/lib/format-datetime";
import {
  SERVER_FILTER_PARAMS,
  serverDateFilter,
  serverNumberFilter,
  serverTextFilter,
} from "@/lib/ag-grid-server-filter";

type Props = {
  orders: OrderListItem[];
  ordering: OrderListOrdering;
  onOrderingChange: (ordering: OrderListOrdering) => void;
  filterModel: FilterModel;
  onFilterModelChange: (model: FilterModel) => void;
};

const SERVER_SORT_FIELDS: ReadonlySet<string> = new Set([
  "number",
  "total",
  "created_at",
  "customer__name",
]);

const orderHref = (order: OrderListItem) => ROUTES.orders.detail(order.id);

function FulfilmentCell({ data }: ICellRendererParams<OrderListItem>) {
  if (!data) return null;
  return (
    <div className="flex h-full items-center overflow-visible">
      <OrderStatusBadge status={data.fulfilment_status} />
    </div>
  );
}

function PaymentCell({ data }: ICellRendererParams<OrderListItem>) {
  if (!data) return null;
  return (
    <div className="flex h-full items-center overflow-visible">
      <PaymentStatusBadge status={data.payment_status} />
    </div>
  );
}

function CreatedCell({ data }: ICellRendererParams<OrderListItem>) {
  if (!data) return null;
  return (
    <div className="flex h-full items-center">
      <FormattedTime
        value={data.created_at}
        variant="relative"
        className="text-sm text-muted-foreground"
      />
    </div>
  );
}

function TotalCell({ data }: ICellRendererParams<OrderListItem>) {
  if (!data) return null;
  return (
    <span className="tabular-nums">
      {data.currency} {data.total}
    </span>
  );
}

/** Presentational AG Grid for the orders list — page owns fetching. */
export function OrdersGrid({
  orders,
  ordering,
  onOrderingChange,
  filterModel,
  onFilterModelChange,
}: Props) {
  const { sortFor, gridProps } = useServerGrid({
    rows: orders,
    ordering,
    defaultOrdering: "-created_at",
    sortableColIds: SERVER_SORT_FIELDS,
    onOrderingChange,
    rowHref: orderHref,
  });

  const columnDefs = useMemo<ColDef<OrderListItem>[]>(
    () => [
      {
        headerName: "Order",
        field: "number",
        flex: 1.2,
        minWidth: 120,
        sortable: true,
        filter: serverTextFilter,
        comparator: () => 0,
        sort: sortFor("number"),
        initialSort: sortFor("number"),
      },
      {
        headerName: "Customer",
        field: "customer_name",
        // API / Django path — not the serializer field name.
        colId: "customer__name",
        flex: 1.6,
        minWidth: 140,
        sortable: true,
        filter: serverTextFilter,
        comparator: () => 0,
        sort: sortFor("customer__name"),
      },
      {
        headerName: "Total",
        field: "total",
        flex: 1,
        minWidth: 110,
        sortable: true,
        filter: serverNumberFilter,
        valueGetter: ({ data }) => (data ? Number(data.total) : undefined),
        comparator: () => 0,
        sort: sortFor("total"),
        cellRenderer: TotalCell,
      },
      {
        headerName: "Fulfilment",
        field: "fulfilment_status",
        flex: 1.4,
        minWidth: 168,
        sortable: false,
        filter: serverTextFilter,
        filterParams: {
          ...SERVER_FILTER_PARAMS,
          filterOptions: ["equals", "contains"],
          defaultOption: "equals",
        },
        valueGetter: ({ data }) =>
          data ? getFulfilmentLabel(data.fulfilment_status) : "",
        cellRenderer: FulfilmentCell,
        cellClass: "status-badge-cell",
      },
      {
        headerName: "Payment",
        field: "payment_status",
        flex: 1.4,
        minWidth: 168,
        sortable: false,
        filter: serverTextFilter,
        filterParams: {
          ...SERVER_FILTER_PARAMS,
          filterOptions: ["equals", "contains"],
          defaultOption: "equals",
        },
        valueGetter: ({ data }) =>
          data ? getPaymentLabel(data.payment_status) : "",
        cellRenderer: PaymentCell,
        cellClass: "status-badge-cell",
      },
      {
        headerName: "Created",
        field: "created_at",
        flex: 1.2,
        minWidth: 140,
        sortable: true,
        filter: serverDateFilter,
        comparator: () => 0,
        sort: sortFor("created_at"),
        cellRenderer: CreatedCell,
        valueFormatter: (p) =>
          p.value ? formatRelativeTime(String(p.value)) : "",
      },
    ],
    [sortFor],
  );

  return (
    <DataGrid<OrderListItem>
      {...gridProps}
      columnDefs={columnDefs}
      filterModel={filterModel}
      onFilterModelChange={onFilterModelChange}
    />
  );
}
