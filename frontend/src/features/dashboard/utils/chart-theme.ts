/** DESIGN.md colours for AG Charts (which takes plain values, not CSS variables). */
export const CHART_COLORS = {
  ink: "#0e0f0c",
  lime: "#9fe870",
  forest: "#163300",
  positive: "#2ead4b",
  mute: "#868685",
  grid: "#d7dbd4",
  orange: "#ffc091",
  cyan: "#38c8ff",
} as const;

export const CHART_PALETTE = [
  CHART_COLORS.forest,
  CHART_COLORS.lime,
  CHART_COLORS.cyan,
  CHART_COLORS.orange,
  CHART_COLORS.mute,
  CHART_COLORS.positive,
  CHART_COLORS.ink,
];

export const CHART_HEIGHT_PX = 280;
