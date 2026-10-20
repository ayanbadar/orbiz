import {
  AllCommunityModule,
  themeQuartz,
  type ColDef,
  type GridOptions,
} from "ag-grid-community";
import { AgGridProvider, AgGridReact } from "ag-grid-react";
import type { CSSProperties, ReactNode, Ref } from "react";

import { cn } from "cn";

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
}: DataGridProps<TData>) {
  return (
    <div
      className={cn("w-full", className)}
      style={{ ...gridViewportStyle, ...style }}
    >
      <AgGridReact<TData>
        ref={gridRef}
        theme={orbizGridTheme}
        rowData={rowData}
        columnDefs={columnDefs}
        getRowId={getRowId}
        onRowClicked={onRowClicked}
        defaultColDef={{
          sortable: true,
          resizable: true,
          filter: true,
          floatingFilter: false,
          minWidth: 96,
          cellStyle: {
            display: "flex",
            alignItems: "center",
          },
          ...defaultColDef,
        }}
        animateRows={false}
        suppressCellFocus
        enableCellTextSelection
        ensureDomOrder
        rowHeight={GRID_ROW_HEIGHT_PX}
        headerHeight={GRID_HEADER_HEIGHT_PX}
        domLayout="normal"
        {...gridOptions}
      />
    </div>
  );
}
