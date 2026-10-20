import {
  AllCommunityModule,
  themeQuartz,
  type ColDef,
  type GridOptions,
} from "ag-grid-community";
import { AgGridProvider, AgGridReact } from "ag-grid-react";
import type { ReactNode, Ref } from "react";

import { cn } from "cn";

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
  spacing: 8,
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
  /** Fixed height class; omit when using autoHeight via gridOptions. */
  heightClassName?: string;
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
  heightClassName = "min-h-[12rem]",
  gridOptions,
  gridRef,
}: DataGridProps<TData>) {
  return (
    <div className={cn("w-full", heightClassName, className)}>
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
          ...defaultColDef,
        }}
        animateRows
        suppressCellFocus
        enableCellTextSelection
        ensureDomOrder
        rowHeight={56}
        headerHeight={40}
        domLayout="autoHeight"
        {...gridOptions}
      />
    </div>
  );
}
