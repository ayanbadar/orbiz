import { useDeferredValue, useMemo, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import type { FilterModel } from "ag-grid-community";
import {
  parseAsBoolean,
  parseAsInteger,
  parseAsString,
  parseAsStringLiteral,
  useQueryStates,
} from "nuqs";

import { FilterChip } from "@/components/filter-chip";
import {
  DEFAULT_PAGE_SIZE,
  getPageCount,
} from "@/components/pagination";
import { QueryState } from "@/components/query-state";
import { ResourceListChrome } from "@/components/resource-list-chrome";
import { Button } from "@/components/ui/button";
import { ROUTES } from "@/constants/routes";
import { useProducts } from "@/features/products/api/products.api";
import { Channel3SearchDialog } from "@/features/products/components/channel3-search-dialog";
import { ProductsGrid } from "@/features/products/components/products-grid";
import type { ProductListOrdering } from "@/features/products/types";
import {
  productFilterModelToPatch,
  productFiltersToFilterModel,
} from "@/features/products/utils/product-grid-filters";
import { useCurrentStore } from "@/features/stores/api/stores.api";
import { ApiError } from "@/lib/api";

const PRODUCT_ORDERINGS = [
  "name",
  "-name",
  "price",
  "-price",
  "stock_quantity",
  "-stock_quantity",
  "updated_at",
  "-updated_at",
] as const satisfies readonly ProductListOrdering[];

export function ProductsPage() {
  const storeQuery = useCurrentStore();
  const [channel3Open, setChannel3Open] = useState(false);
  const [filters, setFilters] = useQueryStates({
    q: parseAsString.withDefault(""),
    name: parseAsString.withDefault(""),
    sku: parseAsString.withDefault(""),
    low_stock: parseAsBoolean.withDefault(false),
    out_of_stock: parseAsBoolean.withDefault(false),
    in_stock: parseAsBoolean.withDefault(false),
    // null = all; true = active only; false = inactive only
    is_active: parseAsBoolean,
    price_min: parseAsString,
    price_max: parseAsString,
    stock_min: parseAsString,
    stock_max: parseAsString,
    page: parseAsInteger.withDefault(1),
    ordering: parseAsStringLiteral(PRODUCT_ORDERINGS).withDefault("name"),
  });
  const deferredQ = useDeferredValue(filters.q);
  const deferredName = useDeferredValue(filters.name);
  const deferredSku = useDeferredValue(filters.sku);

  const storeReady = Boolean(storeQuery.data);
  const storeMissing =
    storeQuery.isError &&
    storeQuery.error instanceof ApiError &&
    storeQuery.error.status === 404;

  const filterModel = useMemo(
    () =>
      productFiltersToFilterModel({
        name: filters.name,
        sku: filters.sku,
        price_min: filters.price_min,
        price_max: filters.price_max,
        stock_min: filters.stock_min,
        stock_max: filters.stock_max,
        low_stock: filters.low_stock,
        out_of_stock: filters.out_of_stock,
        in_stock: filters.in_stock,
        is_active: filters.is_active,
      }),
    [
      filters.name,
      filters.sku,
      filters.price_min,
      filters.price_max,
      filters.stock_min,
      filters.stock_max,
      filters.low_stock,
      filters.out_of_stock,
      filters.in_stock,
      filters.is_active,
    ],
  );

  const productsQuery = useProducts(
    {
      q: deferredQ || undefined,
      name: deferredName || undefined,
      sku: deferredSku || undefined,
      low_stock: filters.low_stock || undefined,
      out_of_stock: filters.out_of_stock || undefined,
      in_stock: filters.in_stock || undefined,
      is_active: filters.is_active === null ? undefined : filters.is_active,
      price_min: filters.price_min ?? undefined,
      price_max: filters.price_max ?? undefined,
      stock_min: filters.stock_min ?? undefined,
      stock_max: filters.stock_max ?? undefined,
      page: filters.page,
      page_size: DEFAULT_PAGE_SIZE,
      ordering: filters.ordering,
    },
    { enabled: storeReady },
  );

  if (storeMissing) {
    return <Navigate to={ROUTES.stores.onboarding()} replace />;
  }

  if (storeQuery.isError) {
    return (
      <QueryState
        isLoading={false}
        isError
        errorMessage={
          storeQuery.error instanceof Error
            ? storeQuery.error.message
            : "Failed to load your store workspace."
        }
        onRetry={() => {
          void storeQuery.refetch();
        }}
      >
        {null}
      </QueryState>
    );
  }

  const rows = productsQuery.data?.results ?? [];
  const totalCount = productsQuery.data?.count ?? 0;
  const showPagination = getPageCount(totalCount, DEFAULT_PAGE_SIZE) > 1;
  const showInitialLoading =
    (storeQuery.isLoading && !storeQuery.data) ||
    (productsQuery.isLoading && !productsQuery.data);
  const isRefetching = productsQuery.isFetching && !showInitialLoading;
  const showEmpty =
    !showInitialLoading &&
    storeReady &&
    rows.length === 0 &&
    !productsQuery.isPlaceholderData;
  const hasActiveFilters = Boolean(
    deferredQ ||
      deferredName ||
      deferredSku ||
      filters.low_stock ||
      filters.out_of_stock ||
      filters.in_stock ||
      filters.is_active !== null ||
      filters.price_min ||
      filters.price_max ||
      filters.stock_min ||
      filters.stock_max,
  );

  const onFilterModelChange = (model: FilterModel) => {
    void setFilters({
      ...productFilterModelToPatch(model, {
        name: filters.name,
        sku: filters.sku,
        price_min: filters.price_min,
        price_max: filters.price_max,
        stock_min: filters.stock_min,
        stock_max: filters.stock_max,
        low_stock: filters.low_stock,
        out_of_stock: filters.out_of_stock,
        in_stock: filters.in_stock,
        is_active: filters.is_active,
      }),
      page: 1,
    });
  };

  return (
    <>
      <ResourceListChrome
        title="Products"
        subtitle={
          storeQuery.data
            ? `${storeQuery.data.name} · ${storeQuery.data.currency}`
            : "Catalog and stock for your store workspace."
        }
        actions={
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="secondary"
              className="h-12 rounded-[24px] px-6 text-base font-semibold"
              onClick={() => setChannel3Open(true)}
              disabled={!storeReady}
            >
              Search Channel3
            </Button>
            <Button
              asChild
              className="h-12 rounded-[24px] px-6 text-base font-semibold"
            >
              <Link to={ROUTES.products.new()}>Add product</Link>
            </Button>
          </div>
        }
        searchValue={filters.q}
        searchPlaceholder="Search name or SKU"
        onSearchChange={(q) => {
          void setFilters({ q, page: 1 });
        }}
        filters={
          <>
            <FilterChip
              active={filters.low_stock}
              onClick={() => {
                void setFilters({
                  low_stock: !filters.low_stock,
                  out_of_stock: false,
                  in_stock: false,
                  page: 1,
                });
              }}
            >
              Low stock
            </FilterChip>
            <FilterChip
              active={filters.out_of_stock}
              onClick={() => {
                void setFilters({
                  out_of_stock: !filters.out_of_stock,
                  low_stock: false,
                  in_stock: false,
                  page: 1,
                });
              }}
            >
              Out of stock
            </FilterChip>
            <FilterChip
              active={filters.is_active === true}
              onClick={() => {
                void setFilters({
                  is_active: filters.is_active === true ? null : true,
                  in_stock: false,
                  page: 1,
                });
              }}
            >
              Active
            </FilterChip>
            <FilterChip
              active={filters.is_active === false}
              onClick={() => {
                void setFilters({
                  is_active: filters.is_active === false ? null : false,
                  low_stock: false,
                  out_of_stock: false,
                  in_stock: false,
                  page: 1,
                });
              }}
            >
              Inactive
            </FilterChip>
          </>
        }
        isLoading={showInitialLoading}
        isError={productsQuery.isError}
        errorMessage={
          productsQuery.error instanceof Error
            ? productsQuery.error.message
            : "Failed to load products."
        }
        onRetry={() => {
          void productsQuery.refetch();
        }}
        isRefetching={isRefetching}
        showEmpty={showEmpty}
        empty={
          hasActiveFilters ? (
            <p
              className="max-w-sm text-center text-sm text-muted-foreground"
              role="status"
            >
              No products match these filters. Clear search or chips to see
              more.
            </p>
          ) : (
            <div className="max-w-sm space-y-3 text-center">
              <p className="text-lg font-semibold text-foreground">
                No products yet
              </p>
              <p className="text-sm text-muted-foreground">
                Add one manually or import from Channel3 to start your catalog.
              </p>
              <div className="flex flex-wrap justify-center gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  className="h-12 rounded-[24px] px-6 text-base font-semibold"
                  onClick={() => setChannel3Open(true)}
                >
                  Search Channel3
                </Button>
                <Button
                  asChild
                  className="h-12 rounded-[24px] px-6 text-base font-semibold"
                >
                  <Link to={ROUTES.products.new()}>Add product</Link>
                </Button>
              </div>
            </div>
          )
        }
        showPagination={showPagination}
        page={filters.page}
        totalCount={totalCount}
        onPageChange={(page) => {
          void setFilters({ page });
        }}
      >
        <ProductsGrid
          products={rows}
          ordering={filters.ordering}
          onOrderingChange={(ordering) => {
            void setFilters({ ordering, page: 1 });
          }}
          filterModel={filterModel}
          onFilterModelChange={onFilterModelChange}
        />
      </ResourceListChrome>

      <Channel3SearchDialog open={channel3Open} onOpenChange={setChannel3Open} />
    </>
  );
}
