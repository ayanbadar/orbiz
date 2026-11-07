import { X } from "lucide-react";
import { useDeferredValue, useMemo } from "react";
import { Link } from "react-router-dom";
import type { FilterModel } from "ag-grid-community";
import {
  parseAsInteger,
  parseAsString,
  parseAsStringLiteral,
  useQueryStates,
} from "nuqs";

import { FilterChip } from "@/components/filter-chip";
import { DEFAULT_PAGE_SIZE } from "@/components/pagination";
import { ResourceListChrome } from "@/components/resource-list-chrome";
import { Button } from "@/components/ui/button";
import { ROUTES } from "@/constants/routes";
import { getErrorMessage } from "@/features/auth/utils/form-errors";
import { useCustomer } from "@/features/customers/api/customers.api";
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
import { useStoreGate } from "@/features/stores/components/use-store-gate";
import { getResourceListState } from "@/lib/resource-list-state";

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
  "partially_refunded",
  "refunded",
] as const satisfies readonly PaymentStatus[];

export function OrdersPage() {
  const storeGate = useStoreGate();
  const { store, storeReady } = storeGate;
  const [filters, setFilters] = useQueryStates({
    q: parseAsString.withDefault(""),
    number: parseAsString.withDefault(""),
    customer_name: parseAsString.withDefault(""),
    // Set by a customer profile's "View all orders" link.
    customer_id: parseAsInteger,
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
      customer_id: filters.customer_id ?? undefined,
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

  const filteredCustomer = useCustomer(filters.customer_id ?? 0);

  if (storeGate.gate) {
    return storeGate.gate;
  }

  const {
    rows,
    totalCount,
    showPagination,
    showInitialLoading,
    isRefetching,
    showEmpty,
  } = getResourceListState(ordersQuery, storeGate);
  const hasActiveFilters = Boolean(
    filters.q ||
      filters.number ||
      filters.customer_name ||
      filters.customer_id ||
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

  const clearFilters = () => {
    void setFilters({
      q: "",
      number: "",
      customer_name: "",
      customer_id: null,
      fulfilment_status: null,
      payment_status: null,
      total_min: null,
      total_max: null,
      created_after: null,
      created_before: null,
      page: 1,
    });
  };

  return (
    <ResourceListChrome
      title="Orders"
      subtitle={
        store
          ? `${store.name} · draft, confirm, and track fulfilment`
          : "Orders for your store workspace."
      }
      actions={
        <Button
          asChild
          size="cta"
        >
          <Link to={ROUTES.orders.new()}>Create order</Link>
        </Button>
      }
      searchValue={filters.q}
      searchPlaceholder="Search number, customer, SKU…"
      onSearchChange={(q) => {
        void setFilters({ q, page: 1 });
      }}
      hasActiveFilters={hasActiveFilters}
      onClearFilters={clearFilters}
      filters={
        <>
          {filters.customer_id ? (
            <FilterChip
              active
              onClick={() => void setFilters({ customer_id: null, page: 1 })}
            >
              <span>
                Customer: {filteredCustomer.data?.name ?? `#${filters.customer_id}`}
              </span>
              <X aria-hidden />
              <span className="sr-only">Remove customer filter</span>
            </FilterChip>
          ) : null}
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
          <p
            className="max-w-sm text-center text-sm text-muted-foreground"
            role="status"
          >
            No orders match these filters.
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
              size="cta"
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
