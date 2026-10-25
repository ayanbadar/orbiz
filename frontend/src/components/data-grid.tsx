import {
  AllCommunityModule,
  themeQuartz,
  type ColDef,
  type FilterChangedEvent,
  type FilterModel,
  type GridApi,
  type GridOptions,
  type GridReadyEvent,
} from "ag-grid-community";
import { AgGridProvider, AgGridReact } from "ag-grid-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  type CSSProperties,
  type ReactNode,
  type Ref,
} from "react";

import { cn } from "cn";
import {
  filterModelsEqual,
  SERVER_FILTER_PARAMS,
  serverTextFilter,
} from "@/lib/ag-grid-server-filter";

export const GRID_ROW_HEIGHT_PX = 72;
export const GRID_HEADER_HEIGHT_PX = 48;
export const GRID_VIEWPORT_ROWS = 10;

/** Pixel height for ~10 visible rows (header + rows). */
export const GRID_VIEWPORT_HEIGHT_PX =
  GRID_HEADER_HEIGHT_PX + GRID_VIEWPORT_ROWS * GRID_ROW_HEIGHT_PX;

/** Inline height so AG Grid always gets a real viewport (Tailwind-safe). */
export const gridViewportStyle: CSSProperties = {
  height: `min(${GRID_VIEWPORT_HEIGHT_PX}px, 70vh)`,
  minHeight: "16rem",
};

/** Orbiz-tuned Quartz theme — reuse for products, orders, analytics grids. */
export const orbizGridTheme = themeQuartz.withParams({
  accentColor: "#9fe870",
  backgroundColor: "#ffffff",
  borderColor: "#d7dbd4",
  borderRadius: 12,
  browserColorScheme: "light",
  cellTextColor: "#0e0f0c",
  fontFamily: "Inter Variable, Inter, system-ui, sans-serif",
  fontSize: 14,
  foregroundColor: "#0e0f0c",
  headerBackgroundColor: "#ffffff",
  headerFontSize: 12,
  headerFontWeight: 500,
  headerTextColor: "#868685",
  oddRowBackgroundColor: "#ffffff",
  rowHoverColor: "#e2f6d5",
  selectedRowBackgroundColor: "#e2f6d5",
  spacing: 12,
});

const COMMUNITY_MODULES = [AllCommunityModule];

/** Delay before column filters hit nuqs/API so typing isn't wiped mid-keystroke. */
const FILTER_MODEL_DEBOUNCE_MS = 350;

function isInsideColumnFilterUi(target: EventTarget | null): boolean {
  if (!(target instanceof Element)) return false;
  return Boolean(
    target.closest(".ag-popup") ||
      target.closest(".ag-filter") ||
      target.closest(".ag-menu") ||
      target.closest(".ag-popup-child") ||
      target.closest(".ag-header-cell-filter-button") ||
      target.closest(".ag-header-cell-menu-button") ||
      target.closest(".ag-icon-filter"),
  );
}

function isColumnFilterPopupVisible(): boolean {
  return Boolean(
    document.querySelector(
      ".ag-popup .ag-filter, .ag-popup .ag-simple-filter-body-wrapper",
    ),
  );
}

type DataGridProviderProps = {
  children: ReactNode;
};

/** Register AG Grid Community once for the app (products + future orders). */
export function DataGridProvider({ children }: DataGridProviderProps) {
  return (
    <AgGridProvider modules={COMMUNITY_MODULES}>{children}</AgGridProvider>
  );
}

type DataGridProps<TData> = {
  rowData: TData[];
  columnDefs: ColDef<TData>[];
  getRowId?: GridOptions<TData>["getRowId"];
  onRowClicked?: GridOptions<TData>["onRowClicked"];
  defaultColDef?: ColDef<TData>;
  className?: string;
  style?: CSSProperties;
  gridOptions?: GridOptions<TData>;
  gridRef?: Ref<AgGridReact<TData>>;
  /**
   * Controlled AG Grid filter model. When set with `onFilterModelChange`,
   * column filters are pass-through (no client-side row hiding) so pages can
   * drive server/nuqs filtering — matching chip behaviour across pages.
   */
  filterModel?: FilterModel | null;
  onFilterModelChange?: (model: FilterModel) => void;
};

/**
 * Shared AG Grid shell. Feature folders own column defs + cell renderers;
 * this owns theme, defaults, and container sizing Ayan can reuse for Orders.
 */
export function DataGrid<TData>({
  rowData,
  columnDefs,
  getRowId,
  onRowClicked,
  defaultColDef,
  className,
  style,
  gridOptions,
  gridRef,
  filterModel,
  onFilterModelChange,
}: DataGridProps<TData>) {
  const innerRef = useRef<AgGridReact<TData>>(null);
  const serverDriven = Boolean(onFilterModelChange);
  const filterOpenRef = useRef(false);
  /** User wants the popup kept open until an outside click (not data refresh). */
  const keepFilterOpenRef = useRef(false);
  const openFilterColIdRef = useRef<string | null>(null);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reopenTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const filterModelRef = useRef(filterModel);
  filterModelRef.current = filterModel;
  const latestRowDataRef = useRef(rowData);
  latestRowDataRef.current = rowData;
  /** Last rowData shown via React prop; while filter is open we update via API. */
  const reactRowDataRef = useRef(rowData);

  const setRefs = useCallback(
    (instance: AgGridReact<TData> | null) => {
      innerRef.current = instance;
      if (!gridRef) return;
      if (typeof gridRef === "function") {
        gridRef(instance);
      } else {
        gridRef.current = instance;
      }
    },
    [gridRef],
  );

  const mergedDefaultColDef = useMemo<ColDef<TData>>(
    () => ({
      sortable: true,
      resizable: true,
      filter: serverDriven ? serverTextFilter : true,
      filterParams: serverDriven ? SERVER_FILTER_PARAMS : undefined,
      floatingFilter: false,
      minWidth: 96,
      cellStyle: {
        display: "flex",
        alignItems: "center",
      },
      ...defaultColDef,
    }),
    [defaultColDef, serverDriven],
  );

  const reopenFilterIfNeeded = useCallback(() => {
    const api = innerRef.current?.api;
    const colId = openFilterColIdRef.current;
    if (!api || !colId || !keepFilterOpenRef.current) return;
    if (isColumnFilterPopupVisible()) return;
    if (reopenTimerRef.current) {
      clearTimeout(reopenTimerRef.current);
    }
    // Collapse rapid close/reopen cycles into one restore (avoids visible jerk).
    reopenTimerRef.current = setTimeout(() => {
      reopenTimerRef.current = null;
      if (!keepFilterOpenRef.current || openFilterColIdRef.current !== colId) {
        return;
      }
      if (isColumnFilterPopupVisible()) return;
      const active = document.activeElement;
      const hadFocusInFilter =
        active instanceof Element && isInsideColumnFilterUi(active);
      const input =
        active instanceof HTMLInputElement || active instanceof HTMLTextAreaElement
          ? active
          : null;
      const selection = input
        ? { start: input.selectionStart, end: input.selectionEnd, value: input.value }
        : null;

      api.showColumnFilter(colId);
      filterOpenRef.current = true;

      if (hadFocusInFilter && selection) {
        requestAnimationFrame(() => {
          const nextInput = document.querySelector<HTMLInputElement>(
            ".ag-popup .ag-filter input, .ag-popup .ag-simple-filter-body-wrapper input",
          );
          if (!nextInput) return;
          nextInput.focus();
          if (selection.value === nextInput.value) {
            nextInput.setSelectionRange(
              selection.start ?? nextInput.value.length,
              selection.end ?? nextInput.value.length,
            );
          } else {
            nextInput.setSelectionRange(
              nextInput.value.length,
              nextInput.value.length,
            );
          }
        });
      }
    }, 0);
  }, []);

  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
      if (reopenTimerRef.current) clearTimeout(reopenTimerRef.current);
    };
  }, []);

  useEffect(() => {
    if (!serverDriven) return;
    const onPointerDown = (event: PointerEvent) => {
      if (!keepFilterOpenRef.current) return;
      if (isInsideColumnFilterUi(event.target)) return;
      keepFilterOpenRef.current = false;
      openFilterColIdRef.current = null;
      filterOpenRef.current = false;
      reactRowDataRef.current = latestRowDataRef.current;
      innerRef.current?.api?.setGridOption("rowData", latestRowDataRef.current);
    };
    document.addEventListener("pointerdown", onPointerDown, true);
    return () => document.removeEventListener("pointerdown", onPointerDown, true);
  }, [serverDriven]);

  // While the column filter is open, push row updates through the grid API so
  // React prop churn doesn't tear down the popup (that close→reopen is the jerk).
  useEffect(() => {
    if (!serverDriven) {
      reactRowDataRef.current = rowData;
      return;
    }
    const api = innerRef.current?.api;
    if (keepFilterOpenRef.current && api) {
      api.setGridOption("rowData", rowData);
      return;
    }
    reactRowDataRef.current = rowData;
  }, [rowData, serverDriven]);

  useEffect(() => {
    if (!serverDriven || filterModel === undefined) return;
    const api = innerRef.current?.api;
    if (!api) return;
    const current = api.getFilterModel() ?? {};
    const next = filterModel ?? {};
    if (filterModelsEqual(current, next)) return;
    if (keepFilterOpenRef.current && Object.keys(next).length > 0) return;
    api.setFilterModel(next);
  }, [filterModel, serverDriven]);

  const emitFilterModel = useCallback(
    (model: FilterModel) => {
      if (!onFilterModelChange) return;
      if (!filterModelsEqual(model, filterModelRef.current ?? {})) {
        onFilterModelChange(model);
      }
    },
    [onFilterModelChange],
  );

  const handleFilterChanged = useCallback(
    (event: FilterChangedEvent<TData>) => {
      gridOptions?.onFilterChanged?.(event);
      if (!onFilterModelChange) return;
      const next = event.api.getFilterModel() ?? {};
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
      debounceTimerRef.current = setTimeout(() => {
        debounceTimerRef.current = null;
        emitFilterModel(next);
      }, FILTER_MODEL_DEBOUNCE_MS);
    },
    [emitFilterModel, gridOptions, onFilterModelChange],
  );

  const flushFilterClosed = useCallback(
    (api: GridApi<TData>) => {
      filterOpenRef.current = false;
      keepFilterOpenRef.current = false;
      openFilterColIdRef.current = null;
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
        debounceTimerRef.current = null;
      }
      reactRowDataRef.current = latestRowDataRef.current;
      api.setGridOption("rowData", latestRowDataRef.current);
      if (!onFilterModelChange) return;
      emitFilterModel(api.getFilterModel() ?? {});
    },
    [emitFilterModel, onFilterModelChange],
  );

  const handleGridReady = useCallback(
    (event: GridReadyEvent<TData>) => {
      gridOptions?.onGridReady?.(event);
      if (!serverDriven) return;
      // filterClosed is an internal AG Grid event (not on AgPublicEventType).
      (
        event.api as GridApi<TData> & {
          addEventListener(eventType: "filterClosed", listener: () => void): void;
        }
      ).addEventListener("filterClosed", () => {
        if (keepFilterOpenRef.current && openFilterColIdRef.current) {
          reopenFilterIfNeeded();
          return;
        }
        flushFilterClosed(event.api);
      });
    },
    [flushFilterClosed, gridOptions, reopenFilterIfNeeded, serverDriven],
  );

  const {
    onFilterChanged: _ignoredOnFilterChanged,
    onFilterOpened: parentOnFilterOpened,
    onGridReady: _ignoredOnGridReady,
    ...restGridOptions
  } = gridOptions ?? {};

  const gridRowData =
    serverDriven && keepFilterOpenRef.current
      ? reactRowDataRef.current
      : rowData;

  return (
    <div
      className={cn("w-full", className)}
      style={{ ...gridViewportStyle, ...style }}
    >
      <AgGridReact<TData>
        ref={setRefs}
        theme={orbizGridTheme}
        rowData={gridRowData}
        columnDefs={columnDefs}
        getRowId={getRowId}
        onRowClicked={onRowClicked}
        enableFilterHandlers={serverDriven}
        defaultColDef={mergedDefaultColDef}
        animateRows={false}
        suppressCellFocus
        enableCellTextSelection
        ensureDomOrder
        suppressScrollWhenPopupsAreOpen
        // Escape card overflow so column-filter popups aren't clipped/covered.
        popupParent={
          typeof document !== "undefined" ? document.body : undefined
        }
        rowHeight={GRID_ROW_HEIGHT_PX}
        headerHeight={GRID_HEADER_HEIGHT_PX}
        domLayout="normal"
        {...restGridOptions}
        onGridReady={handleGridReady}
        onFilterChanged={handleFilterChanged}
        onFilterOpened={(event) => {
          filterOpenRef.current = true;
          keepFilterOpenRef.current = true;
          const column = event.column;
          openFilterColIdRef.current =
            "getColId" in column ? column.getColId() : null;
          reactRowDataRef.current = rowData;
          parentOnFilterOpened?.(event);
        }}
      />
    </div>
  );
}
