import { useState, type ReactNode } from "react";
import { Link, Navigate } from "react-router-dom";
import {
  parseAsBoolean,
  parseAsInteger,
  parseAsString,
  useQueryStates,
} from "nuqs";

import {
  DEFAULT_PAGE_SIZE,
  getPageCount,
  Pagination,
} from "@/components/pagination";
import { QueryState } from "@/components/query-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ROUTES } from "@/constants/routes";
import { useProducts } from "@/features/products/api/products.api";
import { Channel3SearchDialog } from "@/features/products/components/channel3-search-dialog";
import { ProductImage } from "@/features/products/components/product-image";
import {
  getProductAvailabilityClassName,
  getProductAvailabilityLabel,
} from "@/features/products/utils/product-status";
import { useCurrentStore } from "@/features/stores/api/stores.api";
import { ApiError } from "@/lib/api";
import { cn } from "cn";

export function ProductsPage() {
  const storeQuery = useCurrentStore();
  const [channel3Open, setChannel3Open] = useState(false);
  const [filters, setFilters] = useQueryStates({
    q: parseAsString.withDefault(""),
    low_stock: parseAsBoolean.withDefault(false),
    out_of_stock: parseAsBoolean.withDefault(false),
    // null = all; true = active only; false = inactive only
    is_active: parseAsBoolean,
    page: parseAsInteger.withDefault(1),
  });

  const storeReady = Boolean(storeQuery.data);
  const storeMissing =
    storeQuery.isError &&
    storeQuery.error instanceof ApiError &&
    storeQuery.error.status === 404;

  const productsQuery = useProducts(
    {
      q: filters.q || undefined,
      low_stock: filters.low_stock || undefined,
      out_of_stock: filters.out_of_stock || undefined,
      is_active: filters.is_active === null ? undefined : filters.is_active,
      page: filters.page,
      page_size: DEFAULT_PAGE_SIZE,
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
  // First load only — filter/page changes keep prior rows via keepPreviousData.
  const showInitialLoading =
    (storeQuery.isLoading && !storeQuery.data) ||
    (productsQuery.isLoading && !productsQuery.data);
  const isRefetching =
    productsQuery.isFetching && !showInitialLoading;

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-[28px] font-semibold tracking-tight text-foreground sm:text-[32px]">
            Products
          </h1>
          <p className="text-body">
            {storeQuery.data
              ? `${storeQuery.data.name} · ${storeQuery.data.currency}`
              : "Catalog and stock for your store workspace."}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="secondary"
            className="h-10 rounded-xl px-4 font-semibold"
            onClick={() => setChannel3Open(true)}
            disabled={!storeReady}
          >
            Search Channel3
          </Button>
          <Button asChild className="h-10 rounded-xl px-4 font-semibold">
            <Link to={ROUTES.products.new()}>Add product</Link>
          </Button>
        </div>
      </header>

      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
        <Input
          value={filters.q}
          placeholder="Search name or SKU"
          className="h-9 w-full max-w-sm rounded-lg bg-card sm:flex-1"
          onChange={(event) => {
            void setFilters({ q: event.target.value, page: 1 });
          }}
        />
        <div className="flex flex-wrap gap-2">
          <FilterChip
            active={filters.low_stock}
            onClick={() => {
              void setFilters({
                low_stock: !filters.low_stock,
                out_of_stock: false,
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
                page: 1,
              });
            }}
          >
            Inactive
          </FilterChip>
        </div>
      </div>

      <QueryState
        isLoading={showInitialLoading}
        isError={productsQuery.isError}
        errorMessage={
          productsQuery.error instanceof Error
            ? productsQuery.error.message
            : "Failed to load products."
        }
        isEmpty={!showInitialLoading && storeReady && rows.length === 0}
        emptyMessage="No products yet. Add one manually or import from Channel3."
        onRetry={() => {
          void productsQuery.refetch();
        }}
      >
        <Card
          aria-busy={isRefetching || undefined}
          className={cn(
            "relative gap-0 py-0 ring-border/80 transition-opacity",
            isRefetching && "opacity-70",
          )}
        >
          {isRefetching ? (
            <p
              className="pointer-events-none absolute right-3 top-3 z-10 rounded-md bg-card/90 px-2 py-0.5 text-xs text-muted-foreground shadow-sm"
              role="status"
            >
              Updating…
            </p>
          ) : null}
          <CardContent className="overflow-x-auto p-0">
            {/*
              table-fixed + col widths keep SKU/price aligned when a long
              product name appears or disappears via filters.
            */}
            <table className="w-full min-w-[720px] table-fixed text-left text-sm">
              <colgroup>
                <col className="w-[42%]" />
                <col className="w-[18%]" />
                <col className="w-[16%]" />
                <col className="w-[10%]" />
                <col className="w-[14%]" />
              </colgroup>
              <thead className="border-b border-border text-xs text-muted-foreground">
                <tr>
                  <th className="px-4 py-3 font-medium">Product</th>
                  <th className="px-4 py-3 font-medium">SKU</th>
                  <th className="px-4 py-3 font-medium">Price</th>
                  <th className="px-4 py-3 font-medium">Stock</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((product) => (
                  <tr
                    key={product.id}
                    className="border-b border-border/60 last:border-0"
                  >
                    <td className="px-4 py-3">
                      <div className="flex min-w-0 items-center gap-3">
                        <ProductImage
                          src={product.image_url}
                          alt={product.name}
                          size="sm"
                        />
                        <Link
                          to={ROUTES.products.detail(product.id)}
                          title={product.name}
                          className="min-w-0 truncate font-semibold text-foreground underline-offset-4 hover:underline"
                        >
                          {product.name}
                        </Link>
                      </div>
                    </td>
                    <td
                      className="truncate px-4 py-3 font-mono text-xs text-body"
                      title={product.sku}
                    >
                      {product.sku}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 tabular-nums">
                      {product.currency} {product.price}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 tabular-nums">
                      {product.stock_quantity}
                    </td>
                    <td
                      className={cn(
                        "whitespace-nowrap px-4 py-3 font-medium",
                        getProductAvailabilityClassName(product),
                      )}
                    >
                      {getProductAvailabilityLabel(product)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
          {showPagination ? (
            <CardFooter className="justify-stretch border-border bg-card px-4 py-3">
              <Pagination
                className="w-full"
                page={filters.page}
                totalCount={totalCount}
                pageSize={DEFAULT_PAGE_SIZE}
                onPageChange={(page) => {
                  void setFilters({ page });
                }}
              />
            </CardFooter>
          ) : null}
        </Card>
      </QueryState>

      <Channel3SearchDialog open={channel3Open} onOpenChange={setChannel3Open} />
    </div>
  );
}

/** Thin toggle chip built on Button — reuse for list filters elsewhere. */
function FilterChip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <Button
      type="button"
      size="sm"
      variant={active ? "default" : "outline"}
      className="rounded-lg"
      onClick={onClick}
    >
      {children}
    </Button>
  );
}
