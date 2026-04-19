/**
 * Xerant — Brand tokens.
 *
 * The canonical list of brand-safe values. These mirror the CSS custom
 * properties in xerant/src/app/globals.css and should be used whenever
 * brand values are referenced from TS (e.g., inside ImageResponse routes
 * where CSS variables are not available).
 */

export const BRAND_COLORS = {
  bg: "#000000",
  surface1: "#0A0A0A",
  surface2: "#111113",
  surface3: "#17171A",
  border: "#1F1F22",
  borderStrong: "#2A2A2E",
  fg: "#F5F5F5",
  fgMuted: "#8A8A8E",
  fgDim: "#5A5A5E",
  accent: "#FFB800",
  accentDim: "#8A6500",
  success: "#4ADE80",
  danger: "#F87171",
} as const;

export const BRAND_TAGLINE =
  "A specialized DevOps team. Sandboxed and on-call.";

export const BRAND_TAGLINE_UPPER = "SANDBOXED DEVOPS AGENTS";

/** The five canonical agents. Order is intentional; keep it stable. */
export const BRAND_AGENTS = [
  "AXIOM",
  "FORGE",
  "WARDEN",
  "VECTOR",
  "SENTRY",
] as const;

export const BRAND_TYPOGRAPHY = {
  sans: "Geist, Inter, 'SF Pro Display', -apple-system, BlinkMacSystemFont, system-ui, sans-serif",
  mono: "Geist Mono, 'SF Mono', ui-monospace, Menlo, monospace",
} as const;
