import type {
  ColDef,
  ICellRendererParams,
  RowClickedEvent,
  SortChangedEvent,
} from "ag-grid-community";
import { AgGridReact } from "ag-grid-react";
import { useCallback, useEffect, useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";

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
import { formatRelativeTime } from "@/lib/format-datetime";

type Props = {
  orders: OrderListItem[];
  ordering: OrderListOrdering;
  onOrderingChange: (ordering: OrderListOrdering) => void;
};

const SERVER_SORT_FIELDS = new Set([
  "number",
  "total",
  "created_at",
  "customer__name",
]);

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

function parseOrdering(ordering: OrderListOrdering): {
  colId: string;
  sort: "asc" | "desc";
} {
  if (ordering.startsWith("-")) {
    return { colId: ordering.slice(1), sort: "desc" };
  }
  return { colId: ordering, sort: "asc" };
}

/** Presentational AG Grid for the orders list — page owns fetching. */
export function OrdersGrid({ orders, ordering, onOrderingChange }: Props) {
  const navigate = useNavigate();
  const gridRef = useRef<AgGridReact<OrderListItem>>(null);
  const { colId: sortColId, sort: sortDir } = parseOrdering(ordering);

  useEffect(() => {
    const api = gridRef.current?.api;
    if (!api || orders.length === 0) return;
    api.ensureIndexVisible(0, "top");
  }, [orders]);

  const columnDefs = useMemo<ColDef<OrderListItem>[]>(
    () => [
      {
        headerName: "Order",
        field: "number",
        flex: 1.2,
        minWidth: 120,
        sortable: true,
        comparator: () => 0,
        sort: sortColId === "number" ? sortDir : undefined,
        initialSort: sortColId === "number" ? sortDir : undefined,
      },
      {
        headerName: "Customer",
        field: "customer_name",
        // API / Django path — not the serializer field name.
        colId: "customer__name",
        flex: 1.6,
        minWidth: 140,
        sortable: true,
        comparator: () => 0,
        sort: sortColId === "customer__name" ? sortDir : undefined,
      },
      {
        headerName: "Total",
        field: "total",
        flex: 1,
        minWidth: 110,
        sortable: true,
        comparator: () => 0,
        sort: sortColId === "total" ? sortDir : undefined,
        cellRenderer: TotalCell,
      },
      {
        headerName: "Fulfilment",
        field: "fulfilment_status",
        flex: 1.4,
        minWidth: 168,
        sortable: false,
        cellRenderer: FulfilmentCell,
        cellClass: "status-badge-cell",
        valueFormatter: (p) =>
          p.data ? getFulfilmentLabel(p.data.fulfilment_status) : "",
      },
      {
        headerName: "Payment",
        field: "payment_status",
        flex: 1.4,
        minWidth: 168,
        sortable: false,
        cellRenderer: PaymentCell,
        cellClass: "status-badge-cell",
        valueFormatter: (p) =>
          p.data ? getPaymentLabel(p.data.payment_status) : "",
      },
      {
        headerName: "Created",
        field: "created_at",
        flex: 1.2,
        minWidth: 140,
        sortable: true,
        comparator: () => 0,
        sort: sortColId === "created_at" ? sortDir : undefined,
        cellRenderer: CreatedCell,
        valueFormatter: (p) =>
          p.value ? formatRelativeTime(String(p.value)) : "",
      },
    ],
    [sortColId, sortDir],
  );

  const onRowClicked = (event: RowClickedEvent<OrderListItem>) => {
    const id = event.data?.id;
    if (id != null) {
      void navigate(ROUTES.orders.detail(id));
    }
  };

  const onSortChanged = useCallback(
    (event: SortChangedEvent<OrderListItem>) => {
      const sorted = event.api
        .getColumnState()
        .find((column) => column.sort != null);
      if (!sorted?.colId || !sorted.sort) {
        onOrderingChange("-created_at");
        return;
      }
      if (!SERVER_SORT_FIELDS.has(sorted.colId)) {
        return;
      }
      const next =
        sorted.sort === "desc"
          ? (`-${sorted.colId}` as OrderListOrdering)
          : (sorted.colId as OrderListOrdering);
      if (next !== ordering) {
        onOrderingChange(next);
      }
    },
    [onOrderingChange, ordering],
  );

  return (
    <DataGrid<OrderListItem>
      gridRef={gridRef}
      rowData={orders}
      columnDefs={columnDefs}
      getRowId={(params) => String(params.data.id)}
      onRowClicked={onRowClicked}
      gridOptions={{
        rowStyle: { cursor: "pointer" },
        onSortChanged,
        suppressOverlays: ["noRows"],
      }}
    />
  );
}
