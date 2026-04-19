# Xerant — Brand

The living brand guidelines are published on the marketing site at
[`/brand`](https://xerant.vercel.app/brand). Everything in this document
mirrors what lives in code, in case you want a terminal-friendly view.

## Where things live

```
buildathon/
├── marketing/brand/                 # design-side source of truth (SVGs, PNG exports,
│   ├── logo/*.svg                   # brand sheet HTML, export.sh re-runner)
│   ├── social/twitter-cover.svg
│   ├── png/                         # rasterized exports (mark, avatar, lockup, favicon)
│   └── index.html                   # open this for a standalone brand sheet
│
├── xerant/                          # Next.js landing page
│   ├── src/components/brand/        # React primitives — used by every surface
│   │   ├── mark.tsx                 # <XerantMark />
│   │   ├── wordmark.tsx             # <XerantWordmark />
│   │   ├── lockup.tsx               # <XerantLockupHorizontal />, <XerantLockupStacked />
│   │   ├── tokens.ts                # BRAND_COLORS, BRAND_AGENTS, BRAND_TAGLINE, etc.
│   │   └── index.ts                 # barrel export
│   ├── src/app/brand/page.tsx       # /brand — public brand guidelines page
│   ├── src/app/icon.tsx             # dynamic favicon (uses XerantMark)
│   ├── src/app/apple-icon.tsx       # dynamic apple touch icon (uses XerantMark)
│   ├── src/app/opengraph-image.tsx  # OG image (uses XerantMark + BRAND_AGENTS)
│   └── public/brand/                # downloadable assets served from the landing page
│       ├── mark.svg, wordmark.svg, lockup-*.svg, avatar.svg, favicon.svg
│       ├── twitter-cover.svg
│       ├── png/                     # rasterized copies for direct download
│       └── xerant-brand-kit.zip     # everything, zipped
│
└── BRAND.md                         # this file
```

## The mark — Agent Lattice

Four outline corner nodes, four amber diagonals, one amber orchestrator at the
center. The "X" reads both as Xerant and as the gesture of signing off a
deploy. The four corners are the four specialized agents sandboxed around the
orchestrator.

Source: `xerant/src/components/brand/mark.tsx` (React) or
`marketing/brand/logo/mark.svg` (raw SVG).

### Variants

| Variant        | When to use                                     | Source                              |
|----------------|-------------------------------------------------|-------------------------------------|
| Mark on dark   | Default. Every dark surface.                    | `<XerantMark tone="dark" />`        |
| Mark on light  | Light deck slides, print, paper.                | `<XerantMark tone="light" />`       |
| Glyph only     | Below 32 px, inside tight UI.                   | `<XerantMark glyphOnly />`          |
| Horizontal lockup | Header, footer, email signature.             | `<XerantLockupHorizontal />`        |
| Stacked lockup | Large-format, covers, loading screens.          | `<XerantLockupStacked />`           |

### Don't

- Don't recolor the amber. It's `#FFB800` always.
- Don't gradient-ize the nodes or the X.
- Don't stretch, skew, or rotate the lattice — it's square by design.
- Don't render the full mark below 24 px. Use the glyph-only variant.

## Palette

All tokens mirror `xerant/src/app/globals.css`:

| Token                  | Hex       | Usage                                   |
|------------------------|-----------|-----------------------------------------|
| `--color-bg`           | `#000000` | Primary canvas.                         |
| `--color-surface-1`    | `#0A0A0A` | Cards, quiet panels.                    |
| `--color-surface-2`    | `#111113` | Elevated cards, modals.                 |
| `--color-surface-3`    | `#17171A` | Hover, active chips.                    |
| `--color-border`       | `#1F1F22` | Default hairlines.                      |
| `--color-border-strong`| `#2A2A2E` | Emphasized edges, outline nodes.        |
| `--color-fg`           | `#F5F5F5` | Body text, headings.                    |
| `--color-fg-muted`     | `#8A8A8E` | Secondary copy.                         |
| `--color-fg-dim`       | `#5A5A5E` | Tertiary labels, eyebrows.              |
| `--color-accent`       | `#FFB800` | Mark amber, active state, primary CTA.  |
| `--color-success`      | `#4ADE80` | Healthy deploys, passing checks.        |
| `--color-danger`       | `#F87171` | Failed deploys, security findings.      |

From TypeScript: `import { BRAND_COLORS } from "@/components/brand";`

### Accent discipline

Amber is a signal, not a decoration. If more than one thing on a screen is
amber, the system is lying about which one matters. Reserve it for: the logo
core, the active agent, the primary CTA, and live status.

## Typography

- **Sans**: Geist (via `next/font/google`). Weight 600 for headlines, 400 for body.
- **Mono**: Geist Mono. Used for labels, chips, terminal output, system text.
- Set headlines at `tracking: -0.035em` (`-0.045em` for display).
- Set mono labels at `tracking: 0.12em`, uppercase, 11–12 px.

## Voice

Confident, specific, short. We're operators, not cheerleaders.

**Write this:**
- "A specialized DevOps team. Sandboxed and on-call."
- "Five agents. One deploy lifecycle."
- "gVisor isolation per agent. Zero prompt injection blast radius."
- "Ship to prod, or don't. No maybes."

**Avoid:**
- Revolutionary, game-changing, next-gen.
- AI-powered, AI-driven, AI-first.
- "Unlock the power of …"
- Emojis in shipped copy. Ever.

## The agents — always five, always in order

`AXIOM → FORGE → WARDEN → VECTOR → SENTRY`

Matches the deploy lifecycle: decompose → build → review → ship → observe.
From TypeScript: `import { BRAND_AGENTS } from "@/components/brand";`

## Re-exporting PNGs

PNGs under `marketing/brand/png/` and `xerant/public/brand/png/` are built
from the SVGs with `rsvg-convert` (librsvg). Rebuild them with:

```bash
brew install librsvg                      # one-time
cd marketing/brand && ./export.sh         # rebuilds every PNG
# then, if you want the xerant/public/brand copies refreshed:
cp -R marketing/brand/png/* xerant/public/brand/png/
cp marketing/brand/social/twitter-cover*.png xerant/public/brand/png/
```

## Changing the brand

1. Start in `marketing/brand/logo/*.svg` — those are the canonical SVGs.
2. Mirror the change in `xerant/src/components/brand/mark.tsx` (the React
   primitive). Keep the two in sync; the page components and ImageResponse
   routes all consume the TS version.
3. Re-run `./marketing/brand/export.sh` to refresh PNGs.
4. Copy the refreshed SVGs + PNGs into `xerant/public/brand/`.
5. If color tokens changed, update `xerant/src/components/brand/tokens.ts`
   and `xerant/src/app/globals.css` together.
6. Ship.
