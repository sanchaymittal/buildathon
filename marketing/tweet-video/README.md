# Xerant tweet video

15-second 1080×1080 MP4 for the "MaaS to replace our DevOps team" tweet.

Brand: black bg `#000`, yellow accent `#FFB800`, mono stencils, slab-bold headlines.

## Assets
- `render-audio.sh` — generates `out/audio.m4a` (15s kick + drone)
- `renderer/scene.html` + `renderer/render.mjs` — Playwright captures 450 frames @ 30fps; ffmpeg stitches to `out/video-silent.mp4`
- `render.sh` — runs both steps and muxes to `./xerant-tweet.mp4`
- `tweet.txt` — the tweet copy ready to paste into X

## Run
```bash
bash marketing/tweet-video/render.sh
```

Output: `marketing/tweet-video/xerant-tweet.mp4` (1080×1080, 15s, H.264 + AAC stereo)

## Tuning
- Scene timings and copy live in `renderer/scene.html` (`SCHEDULE` array).
- Per-element CSS (sizes, letter-spacing, colors) lives in the `<style>` block of the same file.
- Audio mix (kick decay, drone levels, sidechain-like compression) lives in `render-audio.sh`.
- All fonts pulled from the system: SF Mono + Arial Black (auto-fallbacks via `font-family` stacks).

## Why HTML+Playwright, not `ffmpeg drawtext`?
The Homebrew ffmpeg 8.1 on this machine was built without `--enable-libfreetype`,
so `drawtext` is unavailable. HTML/CSS via headless Chrome also gives pixel-perfect
text shaping, easy iteration, and matches the live xerant.cloud site's brand CSS.
