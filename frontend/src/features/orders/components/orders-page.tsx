import { useDeferredValue, useMemo } from "react";
import { Link, Navigate } from "react-router-dom";
import type { FilterModel } from "ag-grid-community";
import {
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
import { getErrorMessage } from "@/features/auth/utils/form-errors";
import { useOrders } from "@/features/orders/api/orders.api";
import { OrdersGrid } from "@/features/orders/components/orders-grid";
import type {
  FulfilmentStatus,
  OrderListOrdering,
  PaymentStatus,
} from "@/features/orders/types";
import {
  orderFilterModelToPatch,
  orderFiltersToFilterModel,
} from "@/features/orders/utils/order-grid-filters";
import { useCurrentStore } from "@/features/stores/api/stores.api";
import { ApiError } from "@/lib/api";

const ORDER_ORDERINGS = [
  "created_at",
  "-created_at",
  "total",
  "-total",
  "number",
  "-number",
  "customer__name",
  "-customer__name",
  "updated_at",
  "-updated_at",
] as const satisfies readonly OrderListOrdering[];

/** All API statuses — chips only surface a subset; column filters use the rest. */
const FULFILMENT_FILTERS = [
  "draft",
  "unfulfilled",
  "processing",
  "shipped",
  "completed",
  "cancelled",
] as const satisfies readonly FulfilmentStatus[];

const PAYMENT_FILTERS = [
  "unpaid",
  "pending",
  "paid",
  "failed",
  "cancelled",
] as const satisfies readonly PaymentStatus[];

export function OrdersPage() {
  const storeQuery = useCurrentStore();
  const [filters, setFilters] = useQueryStates({
    q: parseAsString.withDefault(""),
    number: parseAsString.withDefault(""),
    customer_name: parseAsString.withDefault(""),
    fulfilment_status: parseAsStringLiteral(FULFILMENT_FILTERS),
    payment_status: parseAsStringLiteral(PAYMENT_FILTERS),
    total_min: parseAsString,
    total_max: parseAsString,
    created_after: parseAsString,
    created_before: parseAsString,
    page: parseAsInteger.withDefault(1),
    ordering: parseAsStringLiteral(ORDER_ORDERINGS).withDefault("-created_at"),
  });
  const deferredQ = useDeferredValue(filters.q);
  const deferredNumber = useDeferredValue(filters.number);
  const deferredCustomer = useDeferredValue(filters.customer_name);

  const storeReady = Boolean(storeQuery.data);
  const storeMissing =
    storeQuery.isError &&
    storeQuery.error instanceof ApiError &&
    storeQuery.error.status === 404;

  const filterModel = useMemo(
    () =>
      orderFiltersToFilterModel({
        number: filters.number,
        customer_name: filters.customer_name,
        fulfilment_status: filters.fulfilment_status,
        payment_status: filters.payment_status,
        total_min: filters.total_min,
        total_max: filters.total_max,
        created_after: filters.created_after,
        created_before: filters.created_before,
      }),
    [
      filters.number,
      filters.customer_name,
      filters.fulfilment_status,
      filters.payment_status,
      filters.total_min,
      filters.total_max,
      filters.created_after,
      filters.created_before,
    ],
  );

  const ordersQuery = useOrders(
    {
      q: deferredQ || undefined,
      number: deferredNumber || undefined,
      customer_name: deferredCustomer || undefined,
      fulfilment_status: filters.fulfilment_status ?? undefined,
      payment_status: filters.payment_status ?? undefined,
      total_min: filters.total_min ?? undefined,
      total_max: filters.total_max ?? undefined,
      created_after: filters.created_after ?? undefined,
      created_before: filters.created_before ?? undefined,
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
        errorMessage={getErrorMessage(
          storeQuery.error,
          "Failed to load your store workspace.",
        )}
        onRetry={() => {
          void storeQuery.refetch();
        }}
      >
        {null}
      </QueryState>
    );
  }

  const rows = ordersQuery.data?.results ?? [];
  const totalCount = ordersQuery.data?.count ?? 0;
  const showPagination = getPageCount(totalCount, DEFAULT_PAGE_SIZE) > 1;
  const showInitialLoading =
    (storeQuery.isLoading && !storeQuery.data) ||
    (ordersQuery.isLoading && !ordersQuery.data);
  const isRefetching = ordersQuery.isFetching && !showInitialLoading;
  const showEmpty =
    !showInitialLoading &&
    storeReady &&
    rows.length === 0 &&
    !ordersQuery.isPlaceholderData;
  const hasActiveFilters = Boolean(
    deferredQ ||
      deferredNumber ||
      deferredCustomer ||
      filters.fulfilment_status ||
      filters.payment_status ||
      filters.total_min ||
      filters.total_max ||
      filters.created_after ||
      filters.created_before,
  );

  const onFilterModelChange = (model: FilterModel) => {
    void setFilters({
      ...orderFilterModelToPatch(model),
      page: 1,
    });
  };

  return (
    <ResourceListChrome
      title="Orders"
      subtitle={
        storeQuery.data
          ? `${storeQuery.data.name} · draft, confirm, and track fulfilment`
          : "Orders for your store workspace."
      }
      actions={
        <Button
          asChild
          className="h-12 rounded-[24px] px-6 text-base font-semibold"
        >
          <Link to={ROUTES.orders.new()}>Create order</Link>
        </Button>
      }
      searchValue={filters.q}
      searchPlaceholder="Search number, customer, SKU…"
      onSearchChange={(q) => {
        void setFilters({ q, page: 1 });
      }}
      filters={
        <>
          <FilterChip
            active={filters.fulfilment_status === "draft"}
            onClick={() =>
              void setFilters({
                fulfilment_status:
                  filters.fulfilment_status === "draft" ? null : "draft",
                page: 1,
              })
            }
          >
            Drafts
          </FilterChip>
          <FilterChip
            active={filters.fulfilment_status === "unfulfilled"}
            onClick={() =>
              void setFilters({
                fulfilment_status:
                  filters.fulfilment_status === "unfulfilled"
                    ? null
                    : "unfulfilled",
                page: 1,
              })
            }
          >
            Unfulfilled
          </FilterChip>
          <FilterChip
            active={filters.payment_status === "pending"}
            onClick={() =>
              void setFilters({
                payment_status:
                  filters.payment_status === "pending" ? null : "pending",
                page: 1,
              })
            }
          >
            Payment pending
          </FilterChip>
        </>
      }
      isLoading={showInitialLoading}
      isError={ordersQuery.isError}
      errorMessage={getErrorMessage(
        ordersQuery.error,
        "Failed to load orders.",
      )}
      onRetry={() => {
        void ordersQuery.refetch();
      }}
      isRefetching={isRefetching}
      showEmpty={showEmpty}
      empty={
        hasActiveFilters ? (
          <p className="max-w-sm text-center text-sm text-muted-foreground" role="status">
            No orders match these filters. Clear search or chips to see more.
          </p>
        ) : (
          <div className="max-w-sm space-y-3 text-center">
            <p className="text-lg font-semibold text-foreground">No orders yet</p>
            <p className="text-sm text-muted-foreground">
              Create a draft from a customer request, confirm when stock is
              ready, then track payment separately.
            </p>
            <Button
              asChild
              className="h-12 rounded-[24px] px-6 text-base font-semibold"
            >
              <Link to={ROUTES.orders.new()}>Create order</Link>
            </Button>
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
      <OrdersGrid
        orders={rows}
        ordering={filters.ordering}
        onOrderingChange={(ordering) => {
          void setFilters({ ordering, page: 1 });
        }}
        filterModel={filterModel}
        onFilterModelChange={onFilterModelChange}
      />
    </ResourceListChrome>
  );
}
