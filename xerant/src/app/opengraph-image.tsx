import { ImageResponse } from "next/og";

export const alt = "Xerant. A specialized DevOps team, sandboxed and on-call.";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const AGENTS = ["AXIOM", "FORGE", "WARDEN", "VECTOR", "SENTRY"] as const;

export default async function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          background: "#000000",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "80px 96px",
          color: "#F5F5F5",
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
            color: "#8A8A8E",
            textTransform: "uppercase",
          }}
        >
          <span style={{ color: "#F5F5F5", letterSpacing: -0.5 }}>XERANT</span>
          <span>Sandboxed DevOps Agents</span>
        </div>

        <div style={{ display: "flex", flexDirection: "column" }}>
          <div
            style={{
              fontSize: 96,
              fontWeight: 600,
              letterSpacing: -4,
              lineHeight: 1.02,
              color: "#F5F5F5",
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
            borderTop: "1px solid #1F1F22",
            paddingTop: 32,
          }}
        >
          {AGENTS.map((name, i) => (
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
                    border: "2px solid #F5F5F5",
                  }}
                />
                <div
                  style={{
                    marginTop: 10,
                    fontSize: 14,
                    letterSpacing: 2,
                    color: "#F5F5F5",
                  }}
                >
                  {name}
                </div>
              </div>
              {i < AGENTS.length - 1 && (
                <div
                  style={{
                    flex: 1,
                    height: 1,
                    background: "#FFB800",
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
