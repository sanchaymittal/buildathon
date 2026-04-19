import { ImageResponse } from "next/og";

export const size = { width: 512, height: 512 };
export const contentType = "image/png";

export default function Icon() {
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
            width: 360,
            height: 360,
            borderRadius: 999,
            border: "16px solid #FFB800",
          }}
        >
          <span
            style={{
              fontFamily: "sans-serif",
              fontSize: 240,
              fontWeight: 700,
              letterSpacing: -12,
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
