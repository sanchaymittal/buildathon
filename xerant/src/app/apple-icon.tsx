import { ImageResponse } from "next/og";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          background: "#000000",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: 128,
            height: 128,
            borderRadius: 999,
            border: "6px solid #FFB800",
          }}
        >
          <span
            style={{
              fontFamily: "sans-serif",
              fontSize: 84,
              fontWeight: 700,
              letterSpacing: -4,
              color: "#F5F5F5",
              lineHeight: 1,
            }}
          >
            X
          </span>
        </div>
      </div>
    ),
    { ...size },
  );
}
