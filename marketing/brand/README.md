# Xerant — Brand Assets

The mark is the **Agent Lattice**: four outline corner nodes, an amber X, and a central amber orchestrator node. Shorthand for "sandboxed agents, coordinated by a core".

Open `index.html` in a browser for a visual brand sheet.

## Palette

Matches the existing landing page tokens in `xerant/src/app/globals.css`.

| Token       | Hex      | Use                              |
|-------------|----------|----------------------------------|
| `bg`        | #000000  | Primary background               |
| `surface-1` | #0A0A0A  | Cards / tiles                    |
| `fg`        | #F5F5F5  | Primary text, node outlines      |
| `fg-muted`  | #8A8A8E  | Secondary text                   |
| `accent`    | #FFB800  | Active lines, center node, rails |

## File map

```
marketing/brand/
├── index.html                         # visual brand sheet (open in browser)
├── concepts/                          # initial exploration (A/B/C)
│   ├── preview.html
│   ├── concept-a-cube.svg
│   ├── concept-b-nodes.svg            # chosen direction
│   └── concept-c-shield.svg
├── logo/                              # vector source (edit these)
│   ├── mark.svg                       # 400×400 mark on black
│   ├── mark-onlight.svg               # 400×400 mark on light
│   ├── favicon.svg                    # 32×32 simplified
│   ├── avatar.svg                     # 400×400 circle-safe
│   ├── wordmark.svg                   # 800×200 "XERANT" text only
│   ├── lockup-horizontal.svg          # 1200×300 mark + wordmark
│   └── lockup-stacked.svg             # 600×700 mark over wordmark + tagline
├── social/
│   ├── twitter-cover.svg              # 1500×500 source
│   ├── twitter-cover.png              # 1500×500 export
│   └── twitter-cover@2x.png           # 3000×1000 retina export
└── png/                               # rasterized exports
    ├── mark-{128,256,512,1024}.png
    ├── mark-onlight-1024.png
    ├── avatar-{400,512,1024}.png
    ├── favicon-{32,64,180}.png
    ├── lockup-horizontal-{800,1600}.png
    ├── lockup-stacked-1200.png
    └── wordmark-1600.png
```

## Re-exporting PNGs

PNGs are generated from the SVGs using `rsvg-convert` (from `librsvg`).

```bash
brew install librsvg   # once

# Re-run the whole export:
cd marketing/brand
./export.sh            # (script lives here after you save it)
```

The one-liner used:

```bash
rsvg-convert -w 1500 -h 500 social/twitter-cover.svg -o social/twitter-cover.png
rsvg-convert -w 512  -h 512  logo/mark.svg           -o png/mark-512.png
# ...etc
```

## Usage

### Twitter / X

- **Header:** upload `social/twitter-cover.png` (or `@2x` for crisper result on retina).
  Layout reserves the bottom-left avatar overlap zone; critical content lives in the upper-left tagline and right-side mark.
- **Profile pic:** upload `png/avatar-400.png` (or a larger one — X will downscale). Composition is circle-safe.

### Favicons (Next.js landing page)

```
xerant/src/app/
├── favicon.ico             # convert png/favicon-32.png via a real .ico if needed
├── icon.svg                # copy logo/favicon.svg here
└── apple-icon.png          # copy png/favicon-180.png here
```

### Docs / README badges

Use `png/lockup-horizontal-800.png` inline; falls back gracefully to the wordmark-only variant.

## Typography

- Wordmark: **Geist 600**, letter-spacing `-2` at 120px (falls back to Inter / SF Pro Display / system sans).
- Tagline: same family, 400 weight.
- Mono details (agent names, technical labels): **Geist Mono** / SF Mono.

The SVGs reference these via CSS `font-family` stacks — install Geist/Inter in any rendering context where you need pixel-perfect parity with the landing page.

## The meaning (for when someone asks)

> Four sandboxed agents around the edges. One amber node at the center coordinating. The X = Xerant, and the act of signing off a deploy. The grid = the sandbox.
