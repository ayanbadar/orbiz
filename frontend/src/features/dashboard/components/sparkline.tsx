import { useId } from "react";

const WIDTH = 100;
const HEIGHT = 32;

/** Tiny trend line for a KPI tile. Decorative: the value and delta carry the meaning. */
export function Sparkline({
  values,
  color,
}: {
  values: number[];
  color: string;
}) {
  const gradientId = useId();
  if (values.length < 2) return null;

  const max = Math.max(...values);
  const min = Math.min(...values);
  const span = max - min || 1;
  const points = values.map((value, index) => {
    const x = (index / (values.length - 1)) * WIDTH;
    // A flat series sits mid-height instead of hugging the bottom edge.
    const y =
      max === min
        ? HEIGHT / 2
        : HEIGHT - 2 - ((value - min) / span) * (HEIGHT - 4);
    return [x, y] as const;
  });
  const line = points
    .map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`)
    .join(" ");

  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      preserveAspectRatio="none"
      className="h-8 w-full"
      aria-hidden
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.25" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon
        points={`0,${HEIGHT} ${line} ${WIDTH},${HEIGHT}`}
        fill={`url(#${gradientId})`}
      />
      <polyline
        points={line}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinejoin="round"
        strokeLinecap="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}
