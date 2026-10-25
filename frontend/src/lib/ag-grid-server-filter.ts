import type {
  ColumnFilter,
  DateFilterModel,
  FilterModel,
  NumberFilterModel,
  TextFilterModel,
} from "ag-grid-community";

/** Column filter UI that never hides client rows — pair with server/nuqs filtering. */
export function serverColumnFilter(
  component:
    | "agTextColumnFilter"
    | "agNumberColumnFilter"
    | "agDateColumnFilter",
): ColumnFilter {
  return {
    component,
    doesFilterPass: () => true,
  };
}

export const serverTextFilter = serverColumnFilter("agTextColumnFilter");
export const serverNumberFilter = serverColumnFilter("agNumberColumnFilter");
export const serverDateFilter = serverColumnFilter("agDateColumnFilter");

export function filterModelsEqual(
  a: FilterModel | null | undefined,
  b: FilterModel | null | undefined,
): boolean {
  return JSON.stringify(a ?? {}) === JSON.stringify(b ?? {});
}

export function isTextFilterModel(model: unknown): model is TextFilterModel {
  if (!model || typeof model !== "object") return false;
  const typed = model as TextFilterModel;
  return typed.filterType === "text" || typed.filterType == null;
}

export function isNumberFilterModel(
  model: unknown,
): model is NumberFilterModel {
  if (!model || typeof model !== "object") return false;
  const typed = model as NumberFilterModel;
  return typed.filterType === "number" || typed.filterType == null;
}

export function isDateFilterModel(model: unknown): model is DateFilterModel {
  if (!model || typeof model !== "object") return false;
  const typed = model as DateFilterModel;
  return typed.filterType === "date" || typed.filterType == null;
}

/** Extract a non-empty text filter value (contains / equals / startsWith / …). */
export function readTextFilterValue(model: unknown): string | null {
  if (!isTextFilterModel(model)) return null;
  if (model.type === "blank" || model.type === "notBlank") return null;
  const value = model.filter?.trim();
  return value ? value : null;
}

export type NumberRange = {
  min: number | null;
  max: number | null;
};

/** Map AG Grid number filter ops onto inclusive min/max bounds for the API. */
export function readNumberRange(model: unknown): NumberRange | null {
  if (!isNumberFilterModel(model)) return null;
  const type = model.type ?? "equals";
  const from = model.filter;
  const to = model.filterTo;

  switch (type) {
    case "equals":
      return from == null ? null : { min: from, max: from };
    case "greaterThan":
    case "greaterThanOrEqual":
      return from == null ? null : { min: from, max: null };
    case "lessThan":
    case "lessThanOrEqual":
      return from == null ? null : { min: null, max: from };
    case "inRange":
      if (from == null && to == null) return null;
      return { min: from ?? null, max: to ?? null };
    case "blank":
    case "notBlank":
    case "notEqual":
      return null;
    default:
      return from == null ? null : { min: from, max: from };
  }
}

export type DateRange = {
  after: string | null;
  before: string | null;
};

function dateOnly(value: string | null | undefined): string | null {
  if (!value) return null;
  // AG Grid may send "YYYY-MM-DD" or "YYYY-MM-DD HH:mm:ss" / ISO.
  const match = /^(\d{4}-\d{2}-\d{2})/.exec(value.trim());
  return match ? match[1] : null;
}

/** Map AG Grid date filter ops onto created_after / created_before (YYYY-MM-DD). */
export function readDateRange(model: unknown): DateRange | null {
  if (!isDateFilterModel(model)) return null;
  const type = model.type ?? "equals";
  const from = dateOnly(model.dateFrom);
  const to = dateOnly(model.dateTo);

  switch (type) {
    case "equals":
      return from ? { after: from, before: from } : null;
    case "greaterThan":
    case "greaterThanOrEqual":
      return from ? { after: from, before: null } : null;
    case "lessThan":
    case "lessThanOrEqual":
      return from ? { after: null, before: from } : null;
    case "inRange":
      if (!from && !to) return null;
      return { after: from, before: to };
    default:
      return null;
  }
}

export function textContainsModel(value: string): TextFilterModel {
  return {
    filterType: "text",
    type: "contains",
    filter: value,
  };
}

export function textEqualsModel(value: string): TextFilterModel {
  return {
    filterType: "text",
    type: "equals",
    filter: value,
  };
}

export function numberRangeModel(
  min: number | null,
  max: number | null,
): NumberFilterModel | null {
  if (min != null && max != null && min === max) {
    return { filterType: "number", type: "equals", filter: min };
  }
  if (min != null && max != null) {
    return {
      filterType: "number",
      type: "inRange",
      filter: min,
      filterTo: max,
    };
  }
  if (min != null) {
    return {
      filterType: "number",
      type: "greaterThanOrEqual",
      filter: min,
    };
  }
  if (max != null) {
    return {
      filterType: "number",
      type: "lessThanOrEqual",
      filter: max,
    };
  }
  return null;
}

export function dateRangeModel(
  after: string | null,
  before: string | null,
): DateFilterModel | null {
  if (after && before && after === before) {
    return {
      filterType: "date",
      type: "equals",
      dateFrom: after,
      dateTo: null,
    };
  }
  if (after && before) {
    return {
      filterType: "date",
      type: "inRange",
      dateFrom: after,
      dateTo: before,
    };
  }
  if (after) {
    return {
      filterType: "date",
      type: "greaterThanOrEqual",
      dateFrom: after,
      dateTo: null,
    };
  }
  if (before) {
    return {
      filterType: "date",
      type: "lessThanOrEqual",
      dateFrom: before,
      dateTo: null,
    };
  }
  return null;
}
