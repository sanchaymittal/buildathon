import { ImageResponse } from "next/og";

export const alt =
  "Xerant. Save 60% on hosting and military-grade security. Sandboxed AI DevOps team.";
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
          padding: "72px 88px",
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
          <span style={{ color: "#F5F5F5", letterSpacing: -0.5, fontSize: 28, fontWeight: 600 }}>
            XERANT
          </span>
          <span>Sandboxed DevOps Agents</span>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <div
            style={{
              fontSize: 88,
              fontWeight: 600,
              letterSpacing: -4,
              lineHeight: 1.02,
              color: "#F5F5F5",
              display: "flex",
              flexDirection: "column",
            }}
          >
            <span>Save 60% on hosting and</span>
            <span>
              <span style={{ color: "#FFB800" }}>military-grade</span> security.
            </span>
          </div>
          <div
            style={{
              fontSize: 26,
              color: "#8A8A8E",
              display: "flex",
              letterSpacing: -0.5,
            }}
          >
            Your sandboxed AI DevOps team — on-call, in your cluster.
          </div>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            borderTop: "1px solid #1F1F22",
            paddingTop: 28,
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
