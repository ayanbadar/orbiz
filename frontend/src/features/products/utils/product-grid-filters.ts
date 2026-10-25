import type { FilterModel } from "ag-grid-community";

import {
  parseProductAvailabilityLabel,
  type ProductAvailabilityLabel,
} from "@/features/products/utils/product-status";
import {
  numberRangeModel,
  readNumberRange,
  readTextFilterValue,
  textContainsModel,
  textEqualsModel,
} from "@/lib/ag-grid-server-filter";

export type ProductGridFilterState = {
  name: string;
  sku: string;
  price_min: string | null;
  price_max: string | null;
  stock_min: string | null;
  stock_max: string | null;
  low_stock: boolean;
  out_of_stock: boolean;
  in_stock: boolean;
  is_active: boolean | null;
};

function formatBound(value: number | null): string | null {
  if (value == null || Number.isNaN(value)) return null;
  return String(value);
}

function availabilityFromState(
  filters: ProductGridFilterState,
): ProductAvailabilityLabel | null {
  if (filters.is_active === false) return "Inactive";
  if (filters.out_of_stock) return "Out of stock";
  if (filters.low_stock) return "Low stock";
  if (filters.in_stock) return "In stock";
  return null;
}

function availabilityToPatch(label: ProductAvailabilityLabel | null): Pick<
  ProductGridFilterState,
  "low_stock" | "out_of_stock" | "in_stock" | "is_active"
> {
  switch (label) {
    case "Inactive":
      return {
        is_active: false,
        low_stock: false,
        out_of_stock: false,
        in_stock: false,
      };
    case "Out of stock":
      return {
        out_of_stock: true,
        low_stock: false,
        in_stock: false,
        is_active: null,
      };
    case "Low stock":
      return {
        low_stock: true,
        out_of_stock: false,
        in_stock: false,
        is_active: null,
      };
    case "In stock":
      return {
        in_stock: true,
        low_stock: false,
        out_of_stock: false,
        is_active: null,
      };
    default:
      return {
        low_stock: false,
        out_of_stock: false,
        in_stock: false,
        is_active: null,
      };
  }
}

/** Build AG Grid filter model from URL/query state (chips + column filters). */
export function productFiltersToFilterModel(
  filters: ProductGridFilterState,
): FilterModel {
  const model: FilterModel = {};

  if (filters.name) {
    model.name = textContainsModel(filters.name);
  }
  if (filters.sku) {
    model.sku = textContainsModel(filters.sku);
  }

  const priceMin =
    filters.price_min != null ? Number(filters.price_min) : null;
  const priceMax =
    filters.price_max != null ? Number(filters.price_max) : null;
  const priceModel = numberRangeModel(
    priceMin != null && !Number.isNaN(priceMin) ? priceMin : null,
    priceMax != null && !Number.isNaN(priceMax) ? priceMax : null,
  );
  if (priceModel) {
    model.price = priceModel;
  }

  const stockMin =
    filters.stock_min != null ? Number(filters.stock_min) : null;
  const stockMax =
    filters.stock_max != null ? Number(filters.stock_max) : null;
  const stockModel = numberRangeModel(
    stockMin != null && !Number.isNaN(stockMin) ? stockMin : null,
    stockMax != null && !Number.isNaN(stockMax) ? stockMax : null,
  );
  if (stockModel) {
    model.stock_quantity = stockModel;
  }

  const availability = availabilityFromState(filters);
  if (availability) {
    model.status = textEqualsModel(availability);
  }

  return model;
}

/**
 * Map grid filter model → URL patch (null clears optional keys for nuqs).
 * `previous` preserves the Active-only chip (`is_active=true`), which has no
 * status-column representation, when other columns change.
 */
export function productFilterModelToPatch(
  model: FilterModel,
  previous: ProductGridFilterState,
): Partial<ProductGridFilterState> {
  const name = readTextFilterValue(model.name);
  const sku = readTextFilterValue(model.sku);
  const priceRange = readNumberRange(model.price);
  const stockRange = readNumberRange(model.stock_quantity);
  const hasStatus = Object.prototype.hasOwnProperty.call(model, "status");
  const statusRaw = hasStatus ? readTextFilterValue(model.status) : null;
  const availability = statusRaw
    ? parseProductAvailabilityLabel(statusRaw)
    : null;

  const availabilityPatch = hasStatus
    ? availabilityToPatch(availability)
    : {
        low_stock: false,
        out_of_stock: false,
        in_stock: false,
        // Active chip is not mirrored in the status column filter.
        is_active: previous.is_active === true ? true : null,
      };

  return {
    name: name ?? "",
    sku: sku ?? "",
    price_min: priceRange ? formatBound(priceRange.min) : null,
    price_max: priceRange ? formatBound(priceRange.max) : null,
    stock_min: stockRange ? formatBound(stockRange.min) : null,
    stock_max: stockRange ? formatBound(stockRange.max) : null,
    ...availabilityPatch,
  };
}
