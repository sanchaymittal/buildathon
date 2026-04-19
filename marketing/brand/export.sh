#!/usr/bin/env bash
# Re-export all Xerant PNG assets from SVG sources.
# Requires: rsvg-convert (brew install librsvg)

set -euo pipefail

cd "$(dirname "$0")"

if ! command -v rsvg-convert >/dev/null 2>&1; then
  echo "rsvg-convert not found. Install with: brew install librsvg" >&2
  exit 1
fi

OUT=png
rm -rf "$OUT" && mkdir -p "$OUT"

# Mark — square, multiple sizes
for s in 128 256 512 1024; do
  rsvg-convert -w "$s" -h "$s" logo/mark.svg -o "$OUT/mark-$s.png"
done
rsvg-convert -w 1024 -h 1024 logo/mark-onlight.svg -o "$OUT/mark-onlight-1024.png"

# Favicon
rsvg-convert -w 32  -h 32  logo/favicon.svg -o "$OUT/favicon-32.png"
rsvg-convert -w 64  -h 64  logo/favicon.svg -o "$OUT/favicon-64.png"
rsvg-convert -w 180 -h 180 logo/favicon.svg -o "$OUT/favicon-180.png"

# Avatar
for s in 400 512 1024; do
  rsvg-convert -w "$s" -h "$s" logo/avatar.svg -o "$OUT/avatar-$s.png"
done

# Lockups
rsvg-convert -w 800  logo/lockup-horizontal.svg -o "$OUT/lockup-horizontal-800.png"
rsvg-convert -w 1600 logo/lockup-horizontal.svg -o "$OUT/lockup-horizontal-1600.png"
rsvg-convert -w 1200 logo/lockup-stacked.svg    -o "$OUT/lockup-stacked-1200.png"
rsvg-convert -w 1600 logo/wordmark.svg          -o "$OUT/wordmark-1600.png"

# Twitter cover
rsvg-convert -w 1500 -h 500  social/twitter-cover.svg -o social/twitter-cover.png
rsvg-convert -w 3000 -h 1000 social/twitter-cover.svg -o social/twitter-cover@2x.png

echo "Done. Assets in: $OUT/ and social/"
