#!/usr/bin/env bash
# render-audio.sh — brand-voice audio for the 15s launch video.
#
# Operator, not cheerleader. So: no EDM beat.
#   - Sub-bass drone @ 50Hz, slowly throbbing (tension)
#   - UI-style clicks on act transitions (~3s, 5s, 11s, 13s)
#   - Gentle swell into the final CTA (12.5s–15s)
# Target: -24 dB mean, -12 dB peak. Works muted (X autoplay), adds
# presence when sound is on. No melody, no hype.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/out/audio.m4a"
DUR=15
mkdir -p "$HERE/out"

# aevalsrc notes:
#   mod(t, 15) == t   (so never wraps)
#   Act transition click: narrow amplitude spike + 1.5k-3k sine for "UI tick" feel
#   Clicks trigger at: 2.9, 5.0, 11.0, 13.1 (each ~70ms)
#
# Click envelope:
#   click(t, t0) = exp(-80 * (t - t0))    for t >= t0
#
# Swell from 12.5 -> 15.0s lifts the drone ~3x.

ffmpeg -y -hide_banner -loglevel warning \
  -f lavfi -i "aevalsrc='
     0.28*sin(2*PI*50*t) * (0.65 + 0.35*sin(2*PI*0.22*t))
     * (1 + 0.6 * ( if(gt(t,12.5), (t-12.5)/2.5, 0) ))
   ':d=${DUR}:s=48000" \
  -f lavfi -i "aevalsrc='
     0.55 * sin(2*PI*2800*t) *
     (
       (if(gt(t,2.90), exp(-80*(t-2.90)), 0)) +
       (if(gt(t,5.00), exp(-80*(t-5.00)), 0)) +
       (if(gt(t,11.00), exp(-80*(t-11.00)), 0)) +
       (if(gt(t,13.10), exp(-80*(t-13.10)), 0))
     )
   ':d=${DUR}:s=48000" \
  -f lavfi -i "aevalsrc='
     0.12 * sin(2*PI*80*t)
     * (if(gt(t,13.10), 1, 0))
     * min(1, (t - 13.10) / 0.8)
   ':d=${DUR}:s=48000" \
  -filter_complex "
    [0:a]volume=0.60[drone];
    [1:a]volume=0.22[clicks];
    [2:a]volume=0.30[swell];
    [drone][clicks][swell]amix=inputs=3:duration=first:normalize=0,
    acompressor=threshold=-22dB:ratio=3:attack=8:release=160,
    alimiter=limit=0.9,
    afade=t=in:st=0:d=0.35,
    afade=t=out:st=14.3:d=0.7,
    aformat=sample_rates=48000:channel_layouts=stereo
  " \
  -c:a aac -b:a 192k "${OUT}"

echo "wrote ${OUT}"
