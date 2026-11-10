import "@/features/dashboard/utils/register-charts";
import { AgCharts } from "ag-charts-react";
import type { AgPolarChartOptions } from "ag-charts-community";
import { useMemo } from "react";

import {
  CHART_COLORS,
  CHART_HEIGHT_PX,
  CHART_PALETTE,
} from "@/features/dashboard/utils/chart-theme";

export type BreakdownSlice = { label: string; count: number };

/** Donut for "how many of each status", with the total in the middle. */
export function BreakdownChart({
  data,
  totalLabel = "Orders",
}: {
  data: BreakdownSlice[];
  totalLabel?: string;
}) {
  const total = data.reduce((sum, slice) => sum + slice.count, 0);

  const options = useMemo<AgPolarChartOptions>(
    () => ({
      data,
      height: CHART_HEIGHT_PX,
      legend: { position: "bottom" },
      series: [
        {
          type: "donut",
          angleKey: "count",
          legendItemKey: "label",
          innerRadiusRatio: 0.68,
          fills: CHART_PALETTE,
          strokes: ["#ffffff"],
          strokeWidth: 2,
          cornerRadius: 4,
          innerLabels: [
            {
              text: String(total),
              fontSize: 30,
              fontWeight: "bold",
              color: CHART_COLORS.ink,
            },
            { text: totalLabel, fontSize: 13, color: CHART_COLORS.mute },
          ],
          tooltip: {
            renderer: ({ datum }) => ({
              title: datum.label,
              data: [
                {
                  label: "Count",
                  value: `${datum.count} (${Math.round((datum.count / total) * 100)}%)`,
                },
              ],
            }),
          },
        },
      ],
    }),
    [data, total, totalLabel],
  );

  return <AgCharts options={options} />;
}
