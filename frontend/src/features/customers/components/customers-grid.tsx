import type {
  ColDef,
  FilterModel,
  ICellRendererParams,
} from "ag-grid-community";
import { useMemo } from "react";

import { DataGrid } from "@/components/data-grid";
import { FormattedTime } from "@/components/formatted-time";
import { StatusBadge } from "@/components/status-badge";
import { ROUTES } from "@/constants/routes";
import type {
  CustomerListOrdering,
  CustomerSummary,
} from "@/features/customers/types";
import { getFulfilmentBadgeClassName } from "@/features/orders/utils/order-status";
import { useServerGrid } from "@/hooks/use-server-grid";
import { serverNumberFilter, serverTextFilter } from "@/lib/ag-grid-server-filter";

type Props = {
  customers: CustomerSummary[];
  ordering: CustomerListOrdering;
  onOrderingChange: (ordering: CustomerListOrdering) => void;
  filterModel: FilterModel;
  onFilterModelChange: (model: FilterModel) => void;
};

/** Grid column ids that map 1:1 to a server `ordering` key. */
const SERVER_SORT_FIELDS: ReadonlySet<string> = new Set([
  "name",
  "order_count",
  "open_order_count",
  "last_order_at",
]);

// Same tones the Orders page uses for these statuses — one place decides
// what "needs attention" vs. "settled" looks like.
const OPEN_TONE_CLASS = getFulfilmentBadgeClassName("unfulfilled");
const SETTLED_TONE_CLASS = getFulfilmentBadgeClassName("completed");

const customerHref = (customer: CustomerSummary) =>
  ROUTES.customers.detail(customer.id);

function NameCell({ data }: ICellRendererParams<CustomerSummary>) {
  if (!data) return null;
  return (
    <span className="truncate font-semibold text-foreground" title={data.name}>
      {data.name}
    </span>
  );
}

function ContactCell({ value }: ICellRendererParams<CustomerSummary, string>) {
  return value ? (
    <span className="truncate text-body" title={value}>
      {value}
    </span>
  ) : (
    <span className="text-muted-foreground">—</span>
  );
}

function OpenOrdersCell({ data }: ICellRendererParams<CustomerSummary>) {
  if (!data) return null;
  if (data.order_count === 0) {
    return <span className="text-muted-foreground">—</span>;
  }
  if (data.open_order_count > 0) {
    return (
      <StatusBadge toneClassName={OPEN_TONE_CLASS}>
        {data.open_order_count} open
      </StatusBadge>
    );
  }
  return <StatusBadge toneClassName={SETTLED_TONE_CLASS}>All settled</StatusBadge>;
}

function LastOrderCell({ data }: ICellRendererParams<CustomerSummary>) {
  if (!data) return null;
  return data.last_order_at ? (
    <FormattedTime
      value={data.last_order_at}
      variant="relative"
      className="text-sm text-muted-foreground"
    />
  ) : (
    <span className="text-sm text-muted-foreground">No orders yet</span>
  );
}

/** Presentational AG Grid for the customers list — page owns fetching. */
export function CustomersGrid({
  customers,
  ordering,
  onOrderingChange,
  filterModel,
  onFilterModelChange,
}: Props) {
  const { sortFor, gridProps } = useServerGrid({
    rows: customers,
    ordering,
    defaultOrdering: "name",
    sortableColIds: SERVER_SORT_FIELDS,
    onOrderingChange,
    rowHref: customerHref,
  });

  const columnDefs = useMemo<ColDef<CustomerSummary>[]>(
    () => [
      {
        headerName: "Customer",
        field: "name",
        flex: 1.6,
        minWidth: 180,
        cellRenderer: NameCell,
        filter: serverTextFilter,
        comparator: () => 0,
        sort: sortFor("name"),
        initialSort: sortFor("name"),
      },
      {
        headerName: "Email",
        field: "email",
        flex: 1.6,
        minWidth: 180,
        sortable: false,
        cellRenderer: ContactCell,
        filter: serverTextFilter,
      },
      {
        headerName: "Phone",
        field: "phone",
        flex: 1.1,
        minWidth: 140,
        sortable: false,
        cellRenderer: ContactCell,
        filter: serverTextFilter,
      },
      {
        headerName: "Orders",
        field: "order_count",
        flex: 0.7,
        minWidth: 104,
        cellClass: "tabular-nums",
        filter: serverNumberFilter,
        comparator: () => 0,
        sort: sortFor("order_count"),
      },
      {
        headerName: "Open",
        field: "open_order_count",
        flex: 0.9,
        minWidth: 128,
        filter: false,
        comparator: () => 0,
        sort: sortFor("open_order_count"),
        cellRenderer: OpenOrdersCell,
        cellClass: "status-badge-cell",
      },
      {
        headerName: "Last order",
        field: "last_order_at",
        flex: 1,
        minWidth: 140,
        filter: false,
        comparator: () => 0,
        sort: sortFor("last_order_at"),
        cellRenderer: LastOrderCell,
      },
    ],
    [sortFor],
  );

  return (
    <DataGrid<CustomerSummary>
      {...gridProps}
      columnDefs={columnDefs}
      filterModel={filterModel}
      onFilterModelChange={onFilterModelChange}
    />
  );
}
