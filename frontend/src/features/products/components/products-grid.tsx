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
import { ROUTES } from "@/constants/routes";
import { ProductAvailabilityBadge } from "@/features/products/components/product-availability-badge";
import { ProductImage } from "@/features/products/components/product-image";
import type { Product, ProductListOrdering } from "@/features/products/types";
import { getProductAvailabilityLabel } from "@/features/products/utils/product-status";

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
    <div className="flex h-full items-center overflow-visible">
      <ProductAvailabilityBadge
        product={data}
        className="whitespace-nowrap"
      />
    </div>
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
  const gridRef = useRef<AgGridReact<Product>>(null);
  const { colId: sortColId, sort: sortDir } = parseOrdering(ordering);

  useEffect(() => {
    const api = gridRef.current?.api;
    if (!api || products.length === 0) {
      return;
    }
    api.ensureIndexVisible(0, "top");
  }, [products]);

  const columnDefs = useMemo<ColDef<Product>[]>(
    () => [
      {
        headerName: "Product",
        field: "name",
        flex: 2.4,
        minWidth: 220,
        cellRenderer: ProductCell,
        filter: "agTextColumnFilter",
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
        flex: 1.15,
        minWidth: 168,
        sortable: false,
        filter: "agTextColumnFilter",
        valueGetter: ({ data }) =>
          data ? getProductAvailabilityLabel(data) : "",
        cellRenderer: StatusCell,
        cellClass: "status-badge-cell",
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
      gridRef={gridRef}
      rowData={products}
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
