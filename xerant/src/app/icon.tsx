import { ImageResponse } from "next/og";
import { XerantMark } from "@/components/brand/mark";
import { BRAND_COLORS } from "@/components/brand/tokens";

export const size = { width: 512, height: 512 };
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          background: BRAND_COLORS.bg,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <XerantMark size={440} tone="dark" />
      </div>
    ),
    { ...size },
  );
}
