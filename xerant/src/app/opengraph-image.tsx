import { ImageResponse } from "next/og";
import { XerantMark } from "@/components/brand/mark";
import { BRAND_AGENTS, BRAND_COLORS } from "@/components/brand/tokens";

export const alt = "Xerant. A specialized DevOps team, sandboxed and on-call.";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          background: BRAND_COLORS.bg,
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "80px 96px",
          color: BRAND_COLORS.fg,
          fontFamily: "sans-serif",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            fontSize: 20,
            letterSpacing: 2,
            color: BRAND_COLORS.fgMuted,
            textTransform: "uppercase",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <XerantMark size={48} tone="dark" glyphOnly />
            <span style={{ color: BRAND_COLORS.fg, letterSpacing: -0.5 }}>
              XERANT
            </span>
          </div>
          <span>Sandboxed DevOps Agents</span>
        </div>

        <div style={{ display: "flex", flexDirection: "column" }}>
          <div
            style={{
              fontSize: 96,
              fontWeight: 600,
              letterSpacing: -4,
              lineHeight: 1.02,
              color: BRAND_COLORS.fg,
              display: "flex",
              flexDirection: "column",
            }}
          >
            <span>A specialized DevOps team.</span>
            <span>Sandboxed and on-call.</span>
          </div>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            borderTop: `1px solid ${BRAND_COLORS.border}`,
            paddingTop: 32,
          }}
        >
          {BRAND_AGENTS.map((name, i) => (
            <div
              key={name}
              style={{
                display: "flex",
                alignItems: "center",
                flex: 1,
                gap: 12,
              }}
            >
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                }}
              >
                <div
                  style={{
                    width: 12,
                    height: 12,
                    borderRadius: 999,
                    border: `2px solid ${BRAND_COLORS.fg}`,
                  }}
                />
                <div
                  style={{
                    marginTop: 10,
                    fontSize: 14,
                    letterSpacing: 2,
                    color: BRAND_COLORS.fg,
                  }}
                >
                  {name}
                </div>
              </div>
              {i < BRAND_AGENTS.length - 1 && (
                <div
                  style={{
                    flex: 1,
                    height: 1,
                    background: BRAND_COLORS.accent,
                    marginBottom: 24,
                  }}
                />
              )}
            </div>
          ))}
        </div>
      </div>
    ),
    { ...size },
  );
}
