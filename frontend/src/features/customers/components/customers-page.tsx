import type { FilterModel } from "ag-grid-community";
import {
  parseAsBoolean,
  parseAsInteger,
  parseAsString,
  parseAsStringLiteral,
  useQueryStates,
} from "nuqs";
import { useDeferredValue, useMemo, useState } from "react";

import { FilterChip } from "@/components/filter-chip";
import { DEFAULT_PAGE_SIZE } from "@/components/pagination";
import { ResourceListChrome } from "@/components/resource-list-chrome";
import { Button } from "@/components/ui/button";
import { getErrorMessage } from "@/features/auth/utils/form-errors";
import { useCustomers } from "@/features/customers/api/customers.api";
import { AddCustomerDialog } from "@/features/customers/components/add-customer-dialog";
import { CustomersGrid } from "@/features/customers/components/customers-grid";
import type { CustomerListOrdering } from "@/features/customers/types";
import {
  customerFilterModelToPatch,
  customerFiltersToFilterModel,
} from "@/features/customers/utils/customer-grid-filters";
import { useStoreGate } from "@/features/stores/components/use-store-gate";
import { getResourceListState } from "@/lib/resource-list-state";

const CUSTOMER_ORDERINGS = [
  "name",
  "-name",
  "order_count",
  "-order_count",
  "open_order_count",
  "-open_order_count",
  "last_order_at",
  "-last_order_at",
  "created_at",
  "-created_at",
] as const satisfies readonly CustomerListOrdering[];

/** Chip presets over the Orders column filter (orders_min / orders_max). */
const NO_ORDERS = { orders_min: null, orders_max: "0" } as const;
const REPEAT_CUSTOMERS = { orders_min: "2", orders_max: null } as const;

export function CustomersPage() {
  const [addOpen, setAddOpen] = useState(false);
  const storeGate = useStoreGate();
  const { store, storeReady } = storeGate;
  const [filters, setFilters] = useQueryStates({
    q: parseAsString.withDefault(""),
    name: parseAsString.withDefault(""),
    email: parseAsString.withDefault(""),
    phone: parseAsString.withDefault(""),
    orders_min: parseAsString,
    orders_max: parseAsString,
    needs_attention: parseAsBoolean.withDefault(false),
    page: parseAsInteger.withDefault(1),
    ordering: parseAsStringLiteral(CUSTOMER_ORDERINGS).withDefault("name"),
  });
  const deferredQ = useDeferredValue(filters.q);
  const deferredName = useDeferredValue(filters.name);
  const deferredEmail = useDeferredValue(filters.email);
  const deferredPhone = useDeferredValue(filters.phone);

  const filterModel = useMemo(
    () =>
      customerFiltersToFilterModel({
        name: filters.name,
        email: filters.email,
        phone: filters.phone,
        orders_min: filters.orders_min,
        orders_max: filters.orders_max,
      }),
    [
      filters.name,
      filters.email,
      filters.phone,
      filters.orders_min,
      filters.orders_max,
    ],
  );

  const customersQuery = useCustomers(
    {
      q: deferredQ || undefined,
      name: deferredName || undefined,
      email: deferredEmail || undefined,
      phone: deferredPhone || undefined,
      orders_min: filters.orders_min ?? undefined,
      orders_max: filters.orders_max ?? undefined,
      needs_attention: filters.needs_attention || undefined,
      page: filters.page,
      page_size: DEFAULT_PAGE_SIZE,
      ordering: filters.ordering,
    },
    { enabled: storeReady },
  );

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
  } = getResourceListState(customersQuery, storeGate);
  const hasActiveFilters = Boolean(
    filters.q ||
    filters.name ||
    filters.email ||
    filters.phone ||
    filters.orders_min ||
    filters.orders_max ||
    filters.needs_attention,
  );
  const noOrdersActive =
    filters.orders_min === NO_ORDERS.orders_min &&
    filters.orders_max === NO_ORDERS.orders_max;
  const repeatActive =
    filters.orders_min === REPEAT_CUSTOMERS.orders_min &&
    filters.orders_max === REPEAT_CUSTOMERS.orders_max;
  const clearOrderCount = { orders_min: null, orders_max: null };

  const onFilterModelChange = (model: FilterModel) => {
    void setFilters({ ...customerFilterModelToPatch(model), page: 1 });
  };

  const clearFilters = () => {
    void setFilters({
      q: "",
      name: "",
      email: "",
      phone: "",
      ...clearOrderCount,
      needs_attention: false,
      page: 1,
    });
  };

  const addCustomerButton = (
    <Button type="button" size="cta" onClick={() => setAddOpen(true)}>
      Add customer
    </Button>
  );

  return (
    <>
      <ResourceListChrome
        title="Customers"
        subtitle={
          store
            ? `${store.name} · contacts, order history, and notes`
            : "Customers for your store workspace."
        }
        actions={addCustomerButton}
        searchValue={filters.q}
        searchPlaceholder="Search name, email, or phone"
        onSearchChange={(q) => {
          void setFilters({ q, page: 1 });
        }}
        hasActiveFilters={hasActiveFilters}
        onClearFilters={clearFilters}
        filters={
          <>
            <FilterChip
              active={repeatActive}
              onClick={() => {
                void setFilters({
                  ...(repeatActive ? clearOrderCount : REPEAT_CUSTOMERS),
                  page: 1,
                });
              }}
            >
              Repeat customers
            </FilterChip>
            <FilterChip
              active={noOrdersActive}
              onClick={() => {
                void setFilters({
                  ...(noOrdersActive ? clearOrderCount : NO_ORDERS),
                  page: 1,
                });
              }}
            >
              No orders yet
            </FilterChip>
            <FilterChip
              active={filters.needs_attention}
              onClick={() => {
                void setFilters({
                  needs_attention: !filters.needs_attention,
                  page: 1,
                });
              }}
            >
              Needs attention
            </FilterChip>
          </>
        }
        isLoading={showInitialLoading}
        isError={customersQuery.isError}
        errorMessage={getErrorMessage(
          customersQuery.error,
          "Failed to load customers.",
        )}
        onRetry={() => {
          void customersQuery.refetch();
        }}
        isRefetching={isRefetching}
        showEmpty={showEmpty}
        empty={
          hasActiveFilters ? (
            <p
              className="max-w-sm text-center text-sm text-muted-foreground"
              role="status"
            >
              No customers match these filters.
            </p>
          ) : (
            <div className="max-w-sm space-y-3 text-center">
              <p className="text-lg font-semibold text-foreground">
                No customers yet
              </p>
              <p className="text-sm text-muted-foreground">
                Add the people who message you to order. Their email lets Orbiz
                send PayPal payment links and confirmations.
              </p>
              {addCustomerButton}
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
        <CustomersGrid
          customers={rows}
          ordering={filters.ordering}
          onOrderingChange={(ordering) => {
            void setFilters({ ordering, page: 1 });
          }}
          filterModel={filterModel}
          onFilterModelChange={onFilterModelChange}
        />
      </ResourceListChrome>
      <AddCustomerDialog
        open={addOpen}
        onOpenChange={setAddOpen}
        description="Add someone who orders from you."
        onCreated={() => undefined}
      />
    </>
  );
}
