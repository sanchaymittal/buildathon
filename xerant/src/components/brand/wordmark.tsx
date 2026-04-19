/**
 * Xerant — Wordmark.
 *
 * Renders "XERANT" in the Geist-first stack that matches the landing page.
 * Use <XerantWordmark /> for typographic-only treatments and
 * <XerantLockup /> when pairing with the mark.
 */

import * as React from "react";

interface WordmarkProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** CSS size for the wordmark. Defaults to "2rem". */
  fontSize?: string | number;
  /** Foreground color. Default is the brand fg. */
  color?: string;
  /** Override the letter-spacing. Default is -0.025em (tight). */
  tracking?: string;
}

export function XerantWordmark({
  fontSize = "2rem",
  color = "#F5F5F5",
  tracking = "-0.025em",
  style,
  ...rest
}: WordmarkProps) {
  return (
    <span
      style={{
        fontFamily:
          "Geist, Inter, 'SF Pro Display', -apple-system, BlinkMacSystemFont, system-ui, sans-serif",
        fontWeight: 600,
        fontSize,
        letterSpacing: tracking,
        color,
        lineHeight: 1,
        display: "inline-block",
        ...style,
      }}
      {...rest}
    >
      XERANT
    </span>
  );
}
