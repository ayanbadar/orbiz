import type { FilterModel } from "ag-grid-community";

import {
  numberRangeModelFromBounds,
  readNumberBounds,
  readTextFilterValue,
  textContainsModel,
} from "@/lib/ag-grid-server-filter";

/** URL (nuqs) filter state that the customers grid's column filters mirror. */
export type CustomerGridFilterState = {
  name: string;
  email: string;
  phone: string;
  orders_min: string | null;
  orders_max: string | null;
};

const TEXT_COLUMNS = ["name", "email", "phone"] as const;

/** Build the AG Grid filter model from URL state (chips + column filters). */
export function customerFiltersToFilterModel(
  filters: CustomerGridFilterState,
): FilterModel {
  const model: FilterModel = {};
  for (const column of TEXT_COLUMNS) {
    if (filters[column]) {
      model[column] = textContainsModel(filters[column]);
    }
  }
  const ordersModel = numberRangeModelFromBounds(
    filters.orders_min,
    filters.orders_max,
  );
  if (ordersModel) {
    model.order_count = ordersModel;
  }
  return model;
}

/** Map a grid filter model back to a URL patch (null/"" clears a key). */
export function customerFilterModelToPatch(
  model: FilterModel,
): CustomerGridFilterState {
  const orders = readNumberBounds(model.order_count);
  return {
    name: readTextFilterValue(model.name) ?? "",
    email: readTextFilterValue(model.email) ?? "",
    phone: readTextFilterValue(model.phone) ?? "",
    orders_min: orders.min,
    orders_max: orders.max,
  };
}
