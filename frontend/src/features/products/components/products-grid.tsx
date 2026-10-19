import type {
  ColDef,
  ICellRendererParams,
  RowClickedEvent,
  SortChangedEvent,
} from "ag-grid-community";
import { useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";

import { DataGrid } from "@/components/data-grid";
import { ROUTES } from "@/constants/routes";
import { ProductImage } from "@/features/products/components/product-image";
import type { Product, ProductListOrdering } from "@/features/products/types";
import {
  getProductAvailabilityClassName,
  getProductAvailabilityLabel,
} from "@/features/products/utils/product-status";
import { cn } from "cn";

type Props = {
  products: Product[];
  ordering: ProductListOrdering;
  onOrderingChange: (ordering: ProductListOrdering) => void;
};

/** Server `ordering` fields that map 1:1 to grid columns. */
const SERVER_SORT_FIELDS = new Set(["name", "price", "stock_quantity"]);

function ProductCell({ data }: ICellRendererParams<Product>) {
  if (!data) {
    return null;
  }
  return (
    <div className="flex h-full min-w-0 items-center gap-3">
      <ProductImage src={data.image_url} alt={data.name} size="sm" />
      <span className="truncate font-semibold text-foreground" title={data.name}>
        {data.name}
      </span>
    </div>
  );
}

function StatusCell({ data }: ICellRendererParams<Product>) {
  if (!data) {
    return null;
  }
  return (
    <span className={cn("font-medium", getProductAvailabilityClassName(data))}>
      {getProductAvailabilityLabel(data)}
    </span>
  );
}

function PriceCell({ data }: ICellRendererParams<Product>) {
  if (!data) {
    return null;
  }
  return (
    <span className="tabular-nums">
      {data.currency} {data.price}
    </span>
  );
}

function parseOrdering(ordering: ProductListOrdering): {
  colId: string;
  sort: "asc" | "desc";
} {
  if (ordering.startsWith("-")) {
    return { colId: ordering.slice(1), sort: "desc" };
  }
  return { colId: ordering, sort: "asc" };
}

/** Presentational AG Grid for the products list — page owns fetching. */
export function ProductsGrid({
  products,
  ordering,
  onOrderingChange,
}: Props) {
  const navigate = useNavigate();
  const { colId: sortColId, sort: sortDir } = parseOrdering(ordering);

  const columnDefs = useMemo<ColDef<Product>[]>(
    () => [
      {
        headerName: "Product",
        field: "name",
        flex: 2.4,
        minWidth: 220,
        cellRenderer: ProductCell,
        filter: "agTextColumnFilter",
        // Keep row order from the API when this column is the active server sort.
        comparator: () => 0,
        sort: sortColId === "name" ? sortDir : undefined,
        initialSort: sortColId === "name" ? sortDir : undefined,
      },
      {
        headerName: "SKU",
        field: "sku",
        flex: 1,
        minWidth: 120,
        cellClass: "font-mono text-xs text-body",
        filter: "agTextColumnFilter",
        // No backend ordering for SKU — client-sort current page only.
      },
      {
        headerName: "Price",
        field: "price",
        flex: 0.9,
        minWidth: 110,
        cellRenderer: PriceCell,
        filter: "agNumberColumnFilter",
        comparator: () => 0,
        sort: sortColId === "price" ? sortDir : undefined,
      },
      {
        headerName: "Stock",
        field: "stock_quantity",
        flex: 0.7,
        minWidth: 88,
        cellClass: "tabular-nums",
        filter: "agNumberColumnFilter",
        comparator: () => 0,
        sort: sortColId === "stock_quantity" ? sortDir : undefined,
      },
      {
        headerName: "Status",
        colId: "status",
        flex: 0.9,
        minWidth: 120,
        valueGetter: ({ data }) =>
          data ? getProductAvailabilityLabel(data) : "",
        cellRenderer: StatusCell,
        filter: "agTextColumnFilter",
      },
    ],
    [sortColId, sortDir],
  );

  const onRowClicked = (event: RowClickedEvent<Product>) => {
    const id = event.data?.id;
    if (id != null) {
      void navigate(ROUTES.products.detail(id));
    }
  };

  const onSortChanged = useCallback(
    (event: SortChangedEvent<Product>) => {
      const sorted = event.api
        .getColumnState()
        .find((column) => column.sort != null);
      if (!sorted?.colId || !sorted.sort) {
        onOrderingChange("name");
        return;
      }
      if (!SERVER_SORT_FIELDS.has(sorted.colId)) {
        return;
      }
      const next =
        sorted.sort === "desc"
          ? (`-${sorted.colId}` as ProductListOrdering)
          : (sorted.colId as ProductListOrdering);
      if (next !== ordering) {
        onOrderingChange(next);
      }
    },
    [onOrderingChange, ordering],
  );

  return (
    <DataGrid<Product>
      rowData={products}
      columnDefs={columnDefs}
      getRowId={(params) => String(params.data.id)}
      onRowClicked={onRowClicked}
      gridOptions={{
        rowStyle: { cursor: "pointer" },
        onSortChanged,
        enableCellTextSelection: true,
        ensureDomOrder: true,
      }}
    />
  );
}
