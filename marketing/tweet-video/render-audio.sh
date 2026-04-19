#!/usr/bin/env bash
# render-audio.sh — generates a subtle 15-second beat + sub-bass drone
# Output: out/audio.m4a
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/out/audio.m4a"
DUR=15

# Audio design:
#   kick   — 55Hz sine with per-beat exponential decay (120 BPM → 0.5s period)
#   drone  — 55Hz sine modulated slowly by 0.5Hz to create a throb under everything
#   tick   — tiny high-freq blip on off-beats to add rhythm
#   mix    — duck all to low level, limit, master fade in/out
#
# aevalsrc syntax:
#   mod(t,0.5) → position within each 0.5s beat
#   exp(-k*mod(t,0.5)) → decay envelope reset per beat
#   Everything clamped via amix + alimiter at the end

ffmpeg -y -hide_banner -loglevel warning \
  -f lavfi -i "aevalsrc='0.9*exp(-15*mod(t,0.5))*sin(2*PI*55*t)':d=${DUR}:s=48000" \
  -f lavfi -i "aevalsrc='0.25*sin(2*PI*55*t)*(0.7+0.3*sin(2*PI*0.5*t))':d=${DUR}:s=48000" \
  -f lavfi -i "aevalsrc='0.35*exp(-60*mod(t-0.25,0.5))*sin(2*PI*4200*t)':d=${DUR}:s=48000" \
  -filter_complex "
    [0:a]volume=0.55[kick];
    [1:a]volume=0.30[drone];
    [2:a]volume=0.05[tick];
    [kick][drone][tick]amix=inputs=3:duration=first:normalize=0,
    acompressor=threshold=-18dB:ratio=4:attack=5:release=120,
    alimiter=limit=0.92,
    afade=t=in:st=0:d=0.5,
    afade=t=out:st=$(echo "${DUR}-0.8" | bc):d=0.8,
    aformat=sample_rates=48000:channel_layouts=stereo
  " \
  -c:a aac -b:a 192k "${OUT}"

echo "wrote ${OUT}"
