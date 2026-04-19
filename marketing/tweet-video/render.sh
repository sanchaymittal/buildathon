#!/usr/bin/env bash
# render.sh — full pipeline: audio + video + mux -> out/xerant-tweet.mp4
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/out"
AUDIO="$OUT/audio.m4a"
VIDEO="$OUT/video-silent.mp4"
FINAL="$HERE/xerant-tweet.mp4"   # kept outside out/ so it isn't gitignored

mkdir -p "$OUT"

echo "[1/3] rendering audio ..."
bash "$HERE/render-audio.sh"

echo "[2/3] rendering video (Playwright + ffmpeg) ..."
pushd "$HERE/renderer" > /dev/null
if [ ! -d node_modules ]; then
  pnpm install
fi
node render.mjs
popd > /dev/null

echo "[3/3] muxing into $FINAL ..."
ffmpeg -y -hide_banner -loglevel warning \
  -i "$VIDEO" \
  -i "$AUDIO" \
  -map 0:v:0 -map 1:a:0 \
  -c:v copy \
  -c:a aac -b:a 192k \
  -shortest \
  -movflags +faststart \
  "$FINAL"

# Human-friendly summary
SIZE=$(ls -lh "$FINAL" | awk '{print $5}')
DUR=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$FINAL" | awk '{printf "%.2f", $1}')
DIM=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "$FINAL")

cat <<EOF

 Done.
    file:     $FINAL
    duration: ${DUR}s
    size:     $SIZE
    dims:     $DIM
    audio:    aac stereo 192k

Preview:
    open "$FINAL"

Tweet copy:
    $HERE/tweet.txt
EOF
