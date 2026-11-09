import type { ColDef, ICellRendererParams, RowClickedEvent } from "ag-grid-community";
import { ChevronRight } from "lucide-react";
import { useMemo } from "react";
import { useNavigate } from "react-router-dom";

import { DataGrid } from "@/components/data-grid";
import { Button } from "@/components/ui/button";
import { ROUTES } from "@/constants/routes";
import { OrderStatusBadge } from "@/features/orders/components/order-status-badge";
import { PaymentStatusBadge } from "@/features/orders/components/payment-status-badge";
import type { FulfilmentStatus, PaymentStatus } from "@/features/orders/types";
import { ProductAvailabilityBadge } from "@/features/products/components/product-availability-badge";
import type { AssistantResultTable, AssistantResultTableKind } from "@/features/assistant/types";

type Row = Record<string, unknown>;

const ROW_HEIGHT_PX = 40;
const HEADER_HEIGHT_PX = 36;
const MAX_VISIBLE_ROWS = 5;

function hasField(rows: Row[], key: string): boolean {
  return rows.some((row) => row[key] !== undefined && row[key] !== null);
}

function asText(value: unknown): string {
  return value === null || value === undefined ? "" : String(value);
}

function OrderTotalCell({ data }: ICellRendererParams<Row>) {
  if (!data) return null;
  return (
    <span className="tabular-nums">
      {asText(data.currency)} {asText(data.total)}
    </span>
  );
}

function OrderPaymentCell({ data }: ICellRendererParams<Row>) {
  if (!data || typeof data.payment_status !== "string") return null;
  return <PaymentStatusBadge status={data.payment_status as PaymentStatus} />;
}

function OrderFulfilmentCell({ data }: ICellRendererParams<Row>) {
  if (!data || typeof data.fulfilment_status !== "string") return null;
  return <OrderStatusBadge status={data.fulfilment_status as FulfilmentStatus} />;
}

function ProductPriceCell({ data }: ICellRendererParams<Row>) {
  if (!data || data.price === undefined) return null;
  return (
    <span className="tabular-nums">
      {asText(data.currency)} {asText(data.price)}
    </span>
  );
}

function ProductStatusCell({ data }: ICellRendererParams<Row>) {
  if (!data) return null;
  const stock = Number(data.stock_quantity ?? 0);
  const threshold = typeof data.low_stock_threshold === "number" ? data.low_stock_threshold : null;
  return (
    <ProductAvailabilityBadge
      product={{
        is_active: typeof data.is_active === "boolean" ? data.is_active : true,
        stock_quantity: stock,
        is_low_stock: threshold !== null && stock <= threshold,
      }}
    />
  );
}

function orderColumns(rows: Row[]): ColDef<Row>[] {
  const cols: ColDef<Row>[] = [
    {
      headerName: "Order",
      field: "order_number",
      flex: 1,
      minWidth: 100,
      cellClass: "font-semibold text-foreground",
    },
  ];
  if (hasField(rows, "customer_name")) {
    cols.push({ headerName: "Customer", field: "customer_name", flex: 1.3, minWidth: 140 });
  }
  if (hasField(rows, "total")) {
    cols.push({
      headerName: "Total",
      colId: "total",
      flex: 0.9,
      minWidth: 96,
      comparator: () => 0,
      valueGetter: ({ data }) => (data ? Number(data.total) : undefined),
      cellRenderer: OrderTotalCell,
    });
  }
  if (hasField(rows, "payment_status")) {
    cols.push({
      headerName: "Payment",
      field: "payment_status",
      flex: 1.1,
      minWidth: 120,
      sortable: false,
      cellClass: "status-badge-cell",
      cellRenderer: OrderPaymentCell,
    });
  }
  if (hasField(rows, "fulfilment_status")) {
    cols.push({
      headerName: "Status",
      field: "fulfilment_status",
      flex: 1.1,
      minWidth: 120,
      sortable: false,
      cellClass: "status-badge-cell",
      cellRenderer: OrderFulfilmentCell,
    });
  }
  if (hasField(rows, "days_old")) {
    cols.push({
      headerName: "Age",
      field: "days_old",
      flex: 0.5,
      minWidth: 70,
      cellClass: "tabular-nums text-muted-foreground",
      valueFormatter: (params) => (typeof params.value === "number" ? `${params.value}d` : ""),
    });
  }
  return cols;
}

function customerColumns(): ColDef<Row>[] {
  return [
    {
      headerName: "Name",
      field: "name",
      flex: 1.3,
      minWidth: 140,
      cellClass: "font-semibold text-foreground",
    },
    { headerName: "Email", field: "email", flex: 1.4, minWidth: 160 },
    { headerName: "Phone", field: "phone", flex: 1, minWidth: 120 },
  ];
}

function productColumns(rows: Row[]): ColDef<Row>[] {
  const cols: ColDef<Row>[] = [
    {
      headerName: "Product",
      field: "name",
      flex: 1.6,
      minWidth: 160,
      cellClass: "font-semibold text-foreground",
    },
    { headerName: "SKU", field: "sku", flex: 1, minWidth: 110, cellClass: "font-mono text-xs text-body" },
  ];
  if (hasField(rows, "price")) {
    cols.push({
      headerName: "Price",
      colId: "price",
      flex: 0.9,
      minWidth: 96,
      comparator: () => 0,
      valueGetter: ({ data }) => (data ? Number(data.price) : undefined),
      cellRenderer: ProductPriceCell,
    });
  }
  cols.push({
    headerName: "Stock",
    field: "stock_quantity",
    flex: 0.6,
    minWidth: 80,
    cellClass: "tabular-nums",
  });
  cols.push({
    headerName: "Status",
    colId: "status",
    flex: 1,
    minWidth: 120,
    sortable: false,
    cellClass: "status-badge-cell",
    cellRenderer: ProductStatusCell,
  });
  return cols;
}

const KIND_ROOT: Record<AssistantResultTableKind, () => string> = {
  orders: ROUTES.orders.root,
  customers: ROUTES.customers.root,
  products: ROUTES.products.root,
};

/** The real list page's own URL, with `view_all`'s filters applied — same search, every row. */
function viewAllHref(table: AssistantResultTable): string {
  const root = KIND_ROOT[table.kind]();
  const entries = Object.entries(table.view_all).filter(([, value]) => value);
  if (entries.length === 0) return root;
  return `${root}?${new URLSearchParams(entries).toString()}`;
}

/**
 * Renders a list/search tool's own rows as a lightweight AG Grid preview — same shell, theme,
 * and status badges as the Orders/Products/Customers pages — instead of the model retyping
 * every row into prose. No column filters here (this is a preview, not a second place to
 * search); clicking anywhere in it opens the real page with the same search applied, so the
 * seller sees every matching row there, not just this preview's page. Columns adapt to
 * whichever fields the tool actually returned (list_customer_orders' rows, for example, have no
 * customer_name since the customer is already named in the title).
 */
export function AssistantResultsTable({ table }: { table: AssistantResultTable }) {
  const navigate = useNavigate();
  const rows = table.rows;
  const href = viewAllHref(table);

  const columnDefs = useMemo<ColDef<Row>[]>(() => {
    if (table.kind === "orders") return orderColumns(rows);
    if (table.kind === "customers") return customerColumns();
    return productColumns(rows);
  }, [table.kind, rows]);

  const previewRows = useMemo(() => rows.slice(0, MAX_VISIBLE_ROWS), [rows]);
  const height = HEADER_HEIGHT_PX + previewRows.length * ROW_HEIGHT_PX + 2;

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card">
      <Button
        type="button"
        variant="secondary"
        onClick={() => void navigate(href)}
        className="w-full justify-between rounded-none px-3 py-2 text-xs font-medium"
      >
        <span>{table.title}</span>
        <span className="flex items-center gap-1 text-[0.7rem] font-semibold text-foreground">
          View all
          <ChevronRight className="size-3.5 shrink-0" aria-hidden />
        </span>
      </Button>
      <DataGrid<Row>
        rowData={previewRows}
        columnDefs={columnDefs}
        defaultColDef={{ filter: false, sortable: false }}
        style={{ height, minHeight: HEADER_HEIGHT_PX + ROW_HEIGHT_PX }}
        gridOptions={{
          rowHeight: ROW_HEIGHT_PX,
          headerHeight: HEADER_HEIGHT_PX,
          domLayout: "normal",
          rowClass: "cursor-pointer",
        }}
        onRowClicked={(event: RowClickedEvent<Row>) => {
          if (event.data) void navigate(href);
        }}
      />
    </div>
  );
}
