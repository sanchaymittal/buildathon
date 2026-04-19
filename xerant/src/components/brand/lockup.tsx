/**
 * Xerant — Logo Lockups.
 *
 * Mark + wordmark combinations. Both variants share one source of truth
 * (XerantMark + XerantWordmark) so spacing and scale stay proportional.
 */

import * as React from "react";
import { XerantMark } from "./mark";
import { XerantWordmark } from "./wordmark";

interface LockupProps {
  /** Height of the mark in px. Wordmark scales relative to this. */
  size?: number;
  tone?: "dark" | "light";
  /** Override tagline in the stacked variant. */
  tagline?: string;
  /** Hide tagline in the stacked variant. */
  showTagline?: boolean;
}

export function XerantLockupHorizontal({
  size = 56,
  tone = "dark",
  ...rest
}: LockupProps & React.HTMLAttributes<HTMLDivElement>) {
  const fg = tone === "light" ? "#0A0A0A" : "#F5F5F5";
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: Math.round(size * 0.35),
      }}
      {...rest}
    >
      <XerantMark size={size} tone={tone} />
      <XerantWordmark fontSize={size * 0.82} color={fg} />
    </div>
  );
}

export function XerantLockupStacked({
  size = 96,
  tone = "dark",
  tagline = "SANDBOXED DEVOPS AGENTS",
  showTagline = true,
  ...rest
}: LockupProps & React.HTMLAttributes<HTMLDivElement>) {
  const fg = tone === "light" ? "#0A0A0A" : "#F5F5F5";
  const muted = tone === "light" ? "#5A5A5E" : "#8A8A8E";
  return (
    <div
      style={{
        display: "inline-flex",
        flexDirection: "column",
        alignItems: "center",
        gap: Math.round(size * 0.28),
      }}
      {...rest}
    >
      <XerantMark size={size} tone={tone} />
      <XerantWordmark fontSize={size * 0.56} color={fg} />
      {showTagline ? (
        <span
          style={{
            fontFamily:
              "Geist Mono, 'SF Mono', ui-monospace, Menlo, monospace",
            fontSize: size * 0.11,
            letterSpacing: "0.3em",
            color: muted,
            textTransform: "uppercase",
          }}
        >
          {tagline}
        </span>
      ) : null}
    </div>
  );
}
