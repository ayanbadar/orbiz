import type {
  GridOptions,
  RowClickedEvent,
  SortChangedEvent,
  SortDirection,
} from "ag-grid-community";
import type { AgGridReact } from "ag-grid-react";
import { useCallback, useEffect, useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";

/** Split a DRF `ordering` value ("-created_at") into an AG Grid column + direction. */
export function parseServerOrdering(ordering: string): {
  colId: string;
  sort: "asc" | "desc";
} {
  if (ordering.startsWith("-")) {
    return { colId: ordering.slice(1), sort: "desc" };
  }
  return { colId: ordering, sort: "asc" };
}

/** Inverse of `parseServerOrdering`. */
export function toServerOrdering(colId: string, sort: "asc" | "desc"): string {
  return sort === "desc" ? `-${colId}` : colId;
}

type UseServerGridOptions<TData, TOrdering extends string> = {
  rows: TData[];
  /** Current server ordering from the URL. */
  ordering: TOrdering;
  /** Ordering to fall back to when the grid reports no sorted column. */
  defaultOrdering: TOrdering;
  /** Grid column ids that map 1:1 to a server ordering key. */
  sortableColIds: ReadonlySet<string>;
  onOrderingChange: (ordering: TOrdering) => void;
  /** Where a row click navigates (the record's detail page). */
  rowHref: (row: TData) => string;
};

/**
 * Wiring shared by every server-sorted, URL-driven list grid (products,
 * orders, customers). Feature grids keep only their column defs and cells:
 *
 *   const { sortFor, gridProps } = useServerGrid({ … });
 *   columns: { field: "name", sort: sortFor("name"), comparator: () => 0 }
 *   <DataGrid {...gridProps} columnDefs={…} filterModel={…} … />
 */
export function useServerGrid<TData extends { id: number }, TOrdering extends string>({
  rows,
  ordering,
  defaultOrdering,
  sortableColIds,
  onOrderingChange,
  rowHref,
}: UseServerGridOptions<TData, TOrdering>) {
  const navigate = useNavigate();
  const gridRef = useRef<AgGridReact<TData>>(null);
  const { colId: sortColId, sort: sortDir } = parseServerOrdering(ordering);

  // A new page/filter result starts at the top instead of the old scroll offset.
  useEffect(() => {
    const api = gridRef.current?.api;
    if (!api || rows.length === 0) return;
    api.ensureIndexVisible(0, "top");
  }, [rows]);

  const sortFor = useCallback(
    (colId: string): SortDirection | undefined =>
      colId === sortColId ? sortDir : undefined,
    [sortColId, sortDir],
  );

  const getRowId = useCallback(
    (params: { data: TData }) => String(params.data.id),
    [],
  );

  const onRowClicked = useCallback(
    (event: RowClickedEvent<TData>) => {
      if (event.data) {
        void navigate(rowHref(event.data));
      }
    },
    [navigate, rowHref],
  );

  const onSortChanged = useCallback(
    (event: SortChangedEvent<TData>) => {
      const sorted = event.api
        .getColumnState()
        .find((column) => column.sort != null);
      if (!sorted?.colId || !sorted.sort) {
        onOrderingChange(defaultOrdering);
        return;
      }
      if (!sortableColIds.has(sorted.colId)) {
        return;
      }
      const next = toServerOrdering(sorted.colId, sorted.sort) as TOrdering;
      if (next !== ordering) {
        onOrderingChange(next);
      }
    },
    [defaultOrdering, onOrderingChange, ordering, sortableColIds],
  );

  const gridOptions = useMemo(
    (): GridOptions<TData> => ({
      rowStyle: { cursor: "pointer" },
      onSortChanged,
      suppressOverlays: ["noRows"],
    }),
    [onSortChanged],
  );

  return {
    sortFor,
    gridProps: {
      gridRef,
      rowData: rows,
      getRowId,
      onRowClicked,
      gridOptions,
    },
  };
}
