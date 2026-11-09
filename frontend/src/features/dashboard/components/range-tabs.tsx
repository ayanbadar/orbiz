import { SegmentedControl } from "@/features/dashboard/components/segmented-control";
import type { DashboardRange } from "@/features/dashboard/types";

const OPTIONS = [
  { value: "7d", label: "7 days" },
  { value: "30d", label: "30 days" },
  { value: "90d", label: "90 days" },
] as const satisfies readonly { value: DashboardRange; label: string }[];

export function RangeTabs({
  value,
  onChange,
}: {
  value: DashboardRange;
  onChange: (value: DashboardRange) => void;
}) {
  return (
    <SegmentedControl
      label="Period"
      value={value}
      onChange={onChange}
      options={OPTIONS}
    />
  );
}
