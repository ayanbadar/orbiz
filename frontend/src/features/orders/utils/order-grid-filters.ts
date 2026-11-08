import type { FilterModel } from "ag-grid-community";

import type { FulfilmentStatus, PaymentStatus } from "@/features/orders/types";
import {
  getFulfilmentLabel,
  getPaymentLabel,
  parseFulfilmentStatus,
  parsePaymentStatus,
} from "@/features/orders/utils/order-status";
import {
  dateRangeModel,
  numberRangeModelFromBounds,
  readDateRange,
  readNumberBounds,
  readTextFilterValue,
  textContainsModel,
  textEqualsModel,
} from "@/lib/ag-grid-server-filter";

export type OrderGridFilterState = {
  number: string;
  customer_name: string;
  fulfilment_status: FulfilmentStatus | null;
  payment_status: PaymentStatus | null;
  total_min: string | null;
  total_max: string | null;
  created_after: string | null;
  created_before: string | null;
};

/** Build AG Grid filter model from URL/query state (chips + column filters). */
export function orderFiltersToFilterModel(
  filters: OrderGridFilterState,
): FilterModel {
  const model: FilterModel = {};

  if (filters.number) {
    model.number = textContainsModel(filters.number);
  }
  if (filters.customer_name) {
    model["customer__name"] = textContainsModel(filters.customer_name);
  }
  if (filters.fulfilment_status) {
    model.fulfilment_status = textEqualsModel(
      getFulfilmentLabel(filters.fulfilment_status),
    );
  }
  if (filters.payment_status) {
    model.payment_status = textEqualsModel(
      getPaymentLabel(filters.payment_status),
    );
  }

  const totalModel = numberRangeModelFromBounds(
    filters.total_min,
    filters.total_max,
  );
  if (totalModel) {
    model.total = totalModel;
  }

  const createdModel = dateRangeModel(
    filters.created_after,
    filters.created_before,
  );
  if (createdModel) {
    model.created_at = createdModel;
  }

  return model;
}

/**
 * Map grid filter model → URL patch. Clears a key with `null` so nuqs drops it.
 * Resets page to 1 when any filter changes (caller should merge page: 1).
 */
export function orderFilterModelToPatch(
  model: FilterModel,
): Partial<OrderGridFilterState> {
  const number = readTextFilterValue(model.number);
  const customer = readTextFilterValue(model["customer__name"]);
  const fulfilmentRaw = readTextFilterValue(model.fulfilment_status);
  const paymentRaw = readTextFilterValue(model.payment_status);
  const total = readNumberBounds(model.total);
  const createdRange = readDateRange(model.created_at);

  return {
    number: number ?? "",
    customer_name: customer ?? "",
    fulfilment_status: fulfilmentRaw
      ? parseFulfilmentStatus(fulfilmentRaw)
      : null,
    payment_status: paymentRaw ? parsePaymentStatus(paymentRaw) : null,
    total_min: total.min,
    total_max: total.max,
    created_after: createdRange?.after ?? null,
    created_before: createdRange?.before ?? null,
  };
}
