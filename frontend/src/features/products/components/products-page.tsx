import { Link, Navigate } from "react-router-dom";
import {
  parseAsBoolean,
  parseAsInteger,
  parseAsString,
  useQueryStates,
} from "nuqs";

import { QueryState } from "@/components/query-state";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ROUTES } from "@/constants/routes";
import { useProducts } from "@/features/products/api/products.api";
import { Channel3SearchDialog } from "@/features/products/components/channel3-search-dialog";
import { useCurrentStore } from "@/features/stores/api/stores.api";
import { ApiError } from "@/lib/api";
import { useState } from "react";

export function ProductsPage() {
  const storeQuery = useCurrentStore();
  const [channel3Open, setChannel3Open] = useState(false);
  const [filters, setFilters] = useQueryStates({
    q: parseAsString.withDefault(""),
    low_stock: parseAsBoolean.withDefault(false),
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
      page: filters.page,
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

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-[32px] font-semibold tracking-tight text-foreground">
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
            className="h-11 rounded-[24px] px-5 font-semibold"
            onClick={() => setChannel3Open(true)}
            disabled={!storeReady}
          >
            Search Channel3
          </Button>
          <Button asChild className="h-11 rounded-[24px] px-5 font-semibold">
            <Link to={ROUTES.products.new()}>Add product</Link>
          </Button>
        </div>
      </header>

      <div className="flex flex-wrap items-center gap-3">
        <Input
          value={filters.q}
          placeholder="Search name or SKU"
          className="max-w-xs"
          onChange={(event) => {
            void setFilters({ q: event.target.value, page: 1 });
          }}
        />
        <Button
          type="button"
          size="sm"
          variant={filters.low_stock ? "default" : "outline"}
          onClick={() => {
            void setFilters({ low_stock: !filters.low_stock, page: 1 });
          }}
        >
          Low stock
        </Button>
      </div>

      <QueryState
        isLoading={productsQuery.isLoading || storeQuery.isLoading}
        isError={productsQuery.isError}
        errorMessage={
          productsQuery.error instanceof Error
            ? productsQuery.error.message
            : "Failed to load products."
        }
        isEmpty={!productsQuery.isLoading && storeReady && rows.length === 0}
        emptyMessage="No products yet. Add one manually or import from Channel3."
        onRetry={() => {
          void productsQuery.refetch();
        }}
      >
        <div className="overflow-x-auto rounded-[24px] bg-card">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="border-b border-border text-xs text-muted-foreground">
              <tr>
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">SKU</th>
                <th className="px-4 py-3 font-medium">Price</th>
                <th className="px-4 py-3 font-medium">Stock</th>
                <th className="px-4 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((product) => (
                <tr key={product.id} className="border-b border-border/60 last:border-0">
                  <td className="px-4 py-3">
                    <Link
                      to={ROUTES.products.detail(product.id)}
                      className="font-semibold underline-offset-4 hover:underline"
                    >
                      {product.name}
                    </Link>
                    {product.is_low_stock ? (
                      <span className="ml-2 rounded-full bg-accent px-2 py-0.5 text-xs text-warning-deep">
                        Low
                      </span>
                    ) : null}
                  </td>
                  <td className="px-4 py-3 text-body">{product.sku}</td>
                  <td className="px-4 py-3">
                    {product.currency} {product.price}
                  </td>
                  <td className="px-4 py-3">{product.stock_quantity}</td>
                  <td className="px-4 py-3">
                    {product.is_active ? "Active" : "Inactive"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </QueryState>

      <Channel3SearchDialog open={channel3Open} onOpenChange={setChannel3Open} />
    </div>
  );
}
