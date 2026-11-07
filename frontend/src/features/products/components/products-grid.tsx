import type {
  ColDef,
  FilterModel,
  ICellRendererParams,
} from "ag-grid-community";
import { useMemo } from "react";

import { DataGrid } from "@/components/data-grid";
import { ROUTES } from "@/constants/routes";
import { ProductAvailabilityBadge } from "@/features/products/components/product-availability-badge";
import { ProductImage } from "@/features/products/components/product-image";
import type { Product, ProductListOrdering } from "@/features/products/types";
import { getProductAvailabilityLabel } from "@/features/products/utils/product-status";
import { useServerGrid } from "@/hooks/use-server-grid";
import {
  SERVER_FILTER_PARAMS,
  serverNumberFilter,
  serverTextFilter,
} from "@/lib/ag-grid-server-filter";

type Props = {
  products: Product[];
  ordering: ProductListOrdering;
  onOrderingChange: (ordering: ProductListOrdering) => void;
  filterModel: FilterModel;
  onFilterModelChange: (model: FilterModel) => void;
};

/** Server `ordering` fields that map 1:1 to grid columns. */
const SERVER_SORT_FIELDS: ReadonlySet<string> = new Set([
  "name",
  "price",
  "stock_quantity",
]);

const productHref = (product: Product) => ROUTES.products.detail(product.id);

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

/** Presentational AG Grid for the products list — page owns fetching. */
export function ProductsGrid({
  products,
  ordering,
  onOrderingChange,
  filterModel,
  onFilterModelChange,
}: Props) {
  const { sortFor, gridProps } = useServerGrid({
    rows: products,
    ordering,
    defaultOrdering: "name",
    sortableColIds: SERVER_SORT_FIELDS,
    onOrderingChange,
    rowHref: productHref,
  });

  const columnDefs = useMemo<ColDef<Product>[]>(
    () => [
      {
        headerName: "Product",
        field: "name",
        flex: 2.4,
        minWidth: 220,
        cellRenderer: ProductCell,
        filter: serverTextFilter,
        comparator: () => 0,
        sort: sortFor("name"),
        initialSort: sortFor("name"),
      },
      {
        headerName: "SKU",
        field: "sku",
        flex: 1,
        minWidth: 120,
        cellClass: "font-mono text-xs text-body",
        filter: serverTextFilter,
      },
      {
        headerName: "Price",
        field: "price",
        flex: 0.9,
        minWidth: 110,
        cellRenderer: PriceCell,
        filter: serverNumberFilter,
        valueGetter: ({ data }) =>
          data ? Number(data.price) : undefined,
        comparator: () => 0,
        sort: sortFor("price"),
      },
      {
        headerName: "Stock",
        field: "stock_quantity",
        flex: 0.7,
        minWidth: 88,
        cellClass: "tabular-nums",
        filter: serverNumberFilter,
        comparator: () => 0,
        sort: sortFor("stock_quantity"),
      },
      {
        headerName: "Status",
        colId: "status",
        flex: 1.15,
        minWidth: 168,
        sortable: false,
        filter: serverTextFilter,
        filterParams: {
          ...SERVER_FILTER_PARAMS,
          filterOptions: ["equals", "contains"],
          defaultOption: "equals",
        },
        valueGetter: ({ data }) =>
          data ? getProductAvailabilityLabel(data) : "",
        cellRenderer: StatusCell,
        cellClass: "status-badge-cell",
      },
    ],
    [sortFor],
  );

  return (
    <DataGrid<Product>
      {...gridProps}
      columnDefs={columnDefs}
      filterModel={filterModel}
      onFilterModelChange={onFilterModelChange}
    />
  );
}
