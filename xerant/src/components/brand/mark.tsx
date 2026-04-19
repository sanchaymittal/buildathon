/**
 * Xerant — Agent Lattice Mark.
 *
 * Shared primitive used by:
 *   - the landing-page React tree,
 *   - the /brand guidelines page,
 *   - the dynamic icon / apple-icon / opengraph routes (via Satori),
 *
 * so every surface draws from the same source of truth.
 */

import * as React from "react";

type Tone = "dark" | "light";

interface MarkProps extends React.SVGProps<SVGSVGElement> {
  /** Pixel size of the rendered mark. Defaults to 64. */
  size?: number;
  /**
   * "dark" renders the on-black variant (for the landing page, social, docs).
   * "light" renders the inverted version for light surfaces.
   */
  tone?: Tone;
  /**
   * Drop the inner grid frame (the four dim perimeter lines).
   * Recommended when the mark is smaller than 32px.
   */
  glyphOnly?: boolean;
  /** Override the accent color. Default is the brand amber (#FFB800). */
  accent?: string;
  /** Set a title for accessibility. Defaults to "Xerant". */
  title?: string;
}

const TOKENS = {
  dark: {
    bg: "transparent",
    nodeFill: "#000000",
    nodeStroke: "#F5F5F5",
    gridStroke: "#2A2A2E",
  },
  light: {
    bg: "transparent",
    nodeFill: "#F5F5F5",
    nodeStroke: "#0A0A0A",
    gridStroke: "#D4D4D8",
  },
} as const;

/**
 * Mark is drawn inside a 400×400 viewBox.
 * - 4 corner nodes at (±110, ±110)
 * - amber X running from each corner toward the center (broken at radius ±22)
 * - central amber orchestrator node at (0, 0)
 */
export function XerantMark({
  size = 64,
  tone = "dark",
  glyphOnly = false,
  accent = "#FFB800",
  title = "Xerant",
  ...rest
}: MarkProps) {
  const t = TOKENS[tone];
  const amberDim = tone === "light" ? "#C27A00" : accent;

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 400 400"
      width={size}
      height={size}
      role="img"
      aria-label={title}
      {...rest}
    >
      <title>{title}</title>
      <g transform="translate(200 200)">
        {!glyphOnly && (
          <g stroke={t.gridStroke} strokeWidth={2} fill="none">
            <line x1={-110} y1={-110} x2={110} y2={-110} />
            <line x1={110} y1={-110} x2={110} y2={110} />
            <line x1={110} y1={110} x2={-110} y2={110} />
            <line x1={-110} y1={110} x2={-110} y2={-110} />
          </g>
        )}
        <g stroke={amberDim} strokeWidth={7} strokeLinecap="round">
          <line x1={-90} y1={-90} x2={-22} y2={-22} />
          <line x1={22} y1={22} x2={90} y2={90} />
          <line x1={90} y1={-90} x2={22} y2={-22} />
          <line x1={-22} y1={22} x2={-90} y2={90} />
        </g>
        <g fill={t.nodeFill} stroke={t.nodeStroke} strokeWidth={5}>
          <circle cx={-110} cy={-110} r={15} />
          <circle cx={110} cy={-110} r={15} />
          <circle cx={-110} cy={110} r={15} />
          <circle cx={110} cy={110} r={15} />
        </g>
        <circle cx={0} cy={0} r={18} fill={amberDim} />
      </g>
    </svg>
  );
}
