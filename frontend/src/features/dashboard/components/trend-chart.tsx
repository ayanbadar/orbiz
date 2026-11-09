import "@/features/dashboard/utils/register-charts";
import { AgCharts } from "ag-charts-react";
import type { AgCartesianChartOptions } from "ag-charts-community";
import { useMemo } from "react";

import {
  CHART_COLORS,
  CHART_HEIGHT_PX,
} from "@/features/dashboard/utils/chart-theme";

export type TrendPoint = { date: string; value: number };

/** Daily line chart (revenue, orders, new stores, …). One series, formatted tooltip. */
export function TrendChart({
  data,
  name,
  formatValue,
  color = CHART_COLORS.forest,
}: {
  data: TrendPoint[];
  name: string;
  formatValue: (value: number) => string;
  color?: string;
}) {
  const options = useMemo<AgCartesianChartOptions>(
    () => ({
      data: data.map((point) => ({ ...point, day: new Date(point.date) })),
      height: CHART_HEIGHT_PX,
      legend: { enabled: false },
      series: [
        {
          type: "area",
          xKey: "day",
          yKey: "value",
          yName: name,
          stroke: color,
          strokeWidth: 2,
          fill: color,
          fillOpacity: 0.14,
          // Short ranges have few points, so dots help; 30+ points would be clutter.
          marker: {
            enabled: data.length <= 14,
            size: 6,
            fill: color,
            stroke: "#ffffff",
            strokeWidth: 2,
          },
          tooltip: {
            renderer: ({ datum }) => ({
              title: new Date(datum.day).toLocaleDateString(undefined, {
                month: "short",
                day: "numeric",
              }),
              data: [{ label: name, value: formatValue(datum.value) }],
            }),
          },
        },
      ],
      axes: {
        x: {
          type: "time",
          position: "bottom",
          label: { format: "%b %d" },
          crosshair: {
            enabled: true,
            stroke: CHART_COLORS.mute,
            lineDash: [4, 4],
          },
        },
        y: {
          type: "number",
          position: "left",
          min: 0,
          label: { formatter: ({ value }) => formatValue(Number(value)) },
          gridLine: {
            style: [{ stroke: CHART_COLORS.grid, lineDash: [4, 4] }],
          },
        },
      },
    }),
    [data, name, formatValue, color],
  );

  return <AgCharts options={options} />;
}
