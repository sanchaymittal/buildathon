import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowUpRight,
  Check,
  Download,
  X as XIcon,
} from "lucide-react";
import { Nav } from "@/components/nav";
import { Footer } from "@/components/footer";
import {
  XerantMark,
  XerantLockupHorizontal,
  XerantLockupStacked,
  XerantWordmark,
  BRAND_AGENTS,
  BRAND_COLORS,
  BRAND_TAGLINE,
  BRAND_TAGLINE_UPPER,
} from "@/components/brand";

export const metadata: Metadata = {
  title: "Brand",
  description:
    "Xerant brand guidelines — logo, color, typography, voice, and downloadable assets.",
  alternates: { canonical: "/brand" },
  openGraph: {
    title: "Xerant · Brand",
    description:
      "Logo, color, typography, voice, and downloads for Xerant.",
    url: "/brand",
  },
};

/** Tailwind v4 token names used across the page. */
const TOKENS: Array<{
  name: string;
  hex: string;
  token: string;
  usage: string;
  fg: string;
}> = [
  { name: "Background", hex: BRAND_COLORS.bg, token: "--color-bg", usage: "Primary canvas. Default for nearly every surface.", fg: BRAND_COLORS.fg },
  { name: "Surface 1", hex: BRAND_COLORS.surface1, token: "--color-surface-1", usage: "Cards, input chrome, quiet panels.", fg: BRAND_COLORS.fg },
  { name: "Surface 2", hex: BRAND_COLORS.surface2, token: "--color-surface-2", usage: "Elevated cards, modals.", fg: BRAND_COLORS.fg },
  { name: "Surface 3", hex: BRAND_COLORS.surface3, token: "--color-surface-3", usage: "Hover states, active chips.", fg: BRAND_COLORS.fg },
  { name: "Border", hex: BRAND_COLORS.border, token: "--color-border", usage: "Default dividers, hairlines.", fg: BRAND_COLORS.fg },
  { name: "Border strong", hex: BRAND_COLORS.borderStrong, token: "--color-border-strong", usage: "Node outlines, emphasized edges.", fg: BRAND_COLORS.fg },
  { name: "Foreground", hex: BRAND_COLORS.fg, token: "--color-fg", usage: "Body text, headings, primary content.", fg: "#000" },
  { name: "Muted", hex: BRAND_COLORS.fgMuted, token: "--color-fg-muted", usage: "Secondary copy, metadata.", fg: "#000" },
  { name: "Dim", hex: BRAND_COLORS.fgDim, token: "--color-fg-dim", usage: "Tertiary labels, eyebrows.", fg: "#000" },
  { name: "Accent", hex: BRAND_COLORS.accent, token: "--color-accent", usage: "Active state, brand signal. Used sparingly.", fg: "#000" },
  { name: "Accent dim", hex: BRAND_COLORS.accentDim, token: "--color-accent-dim", usage: "Disabled / quiet amber.", fg: "#000" },
  { name: "Success", hex: BRAND_COLORS.success, token: "--color-success", usage: "Healthy deploys, passing checks.", fg: "#000" },
  { name: "Danger", hex: BRAND_COLORS.danger, token: "--color-danger", usage: "Failed deploys, security findings.", fg: "#000" },
];

/** A single downloadable asset, grouped below. */
type Asset = { label: string; href: string; size?: string; kind: "svg" | "png" | "zip" };

const ASSETS: Record<string, Asset[]> = {
  "Mark": [
    { label: "mark.svg", href: "/brand/mark.svg", kind: "svg" },
    { label: "mark-onlight.svg", href: "/brand/mark-onlight.svg", kind: "svg" },
    { label: "mark-512.png", href: "/brand/png/mark-512.png", kind: "png", size: "512×512" },
    { label: "mark-1024.png", href: "/brand/png/mark-1024.png", kind: "png", size: "1024×1024" },
  ],
  "Wordmark & lockups": [
    { label: "wordmark.svg", href: "/brand/wordmark.svg", kind: "svg" },
    { label: "lockup-horizontal.svg", href: "/brand/lockup-horizontal.svg", kind: "svg" },
    { label: "lockup-horizontal-1600.png", href: "/brand/png/lockup-horizontal-1600.png", kind: "png", size: "1600×400" },
    { label: "lockup-stacked.svg", href: "/brand/lockup-stacked.svg", kind: "svg" },
    { label: "lockup-stacked-1200.png", href: "/brand/png/lockup-stacked-1200.png", kind: "png", size: "1200×1400" },
  ],
  "Avatar & favicon": [
    { label: "avatar.svg", href: "/brand/avatar.svg", kind: "svg" },
    { label: "avatar-400.png", href: "/brand/png/avatar-400.png", kind: "png", size: "400×400" },
    { label: "avatar-1024.png", href: "/brand/png/avatar-1024.png", kind: "png", size: "1024×1024" },
    { label: "favicon.svg", href: "/brand/favicon.svg", kind: "svg" },
    { label: "favicon-32.png", href: "/brand/png/favicon-32.png", kind: "png", size: "32×32" },
    { label: "favicon-180.png", href: "/brand/png/favicon-180.png", kind: "png", size: "180×180" },
  ],
  "Social": [
    { label: "twitter-cover.svg", href: "/brand/twitter-cover.svg", kind: "svg" },
    { label: "twitter-cover.png", href: "/brand/png/twitter-cover.png", kind: "png", size: "1500×500" },
    { label: "twitter-cover@2x.png", href: "/brand/png/twitter-cover@2x.png", kind: "png", size: "3000×1000" },
  ],
};

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <p className="font-mono text-xs uppercase tracking-[0.08em] text-[var(--color-fg-dim)]">
      {children}
    </p>
  );
}

function H2({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="mt-4 text-[36px] leading-[1.04] tracking-[-0.035em] font-semibold md:text-[44px]">
      {children}
    </h2>
  );
}

function Subhead({ children }: { children: React.ReactNode }) {
  return (
    <p className="mt-5 max-w-[640px] text-[16px] leading-[1.55] text-[var(--color-fg-muted)] md:text-[17px]">
      {children}
    </p>
  );
}

function Tile({
  children,
  label,
  tone = "dark",
  height = 260,
}: {
  children: React.ReactNode;
  label: string;
  tone?: "dark" | "light";
  height?: number;
}) {
  const bg = tone === "dark" ? "var(--color-surface-1)" : "#F5F5F5";
  const border = tone === "dark" ? "var(--color-border)" : "#D4D4D8";
  return (
    <div
      className="flex flex-col"
      style={{ border: `1px solid ${border}` }}
    >
      <div
        className="flex items-center justify-center"
        style={{ background: bg, height }}
      >
        {children}
      </div>
      <div
        className="flex items-center justify-between px-4 py-3 font-mono text-[11px] uppercase tracking-[0.12em]"
        style={{
          background: "var(--color-surface-1)",
          borderTop: "1px solid var(--color-border)",
          color: "var(--color-fg-dim)",
        }}
      >
        <span>{label}</span>
      </div>
    </div>
  );
}

function RuleCard({
  kind,
  title,
  body,
  children,
}: {
  kind: "do" | "dont";
  title: string;
  body: string;
  children: React.ReactNode;
}) {
  const ok = kind === "do";
  const color = ok ? "var(--color-success)" : "var(--color-danger)";
  return (
    <div className="flex flex-col border border-[var(--color-border)]">
      <div
        className="flex items-center justify-center bg-[var(--color-surface-1)]"
        style={{ height: 220 }}
      >
        {children}
      </div>
      <div className="border-t border-[var(--color-border)] p-5">
        <div className="flex items-center gap-2">
          {ok ? (
            <Check className="size-4" style={{ color }} />
          ) : (
            <XIcon className="size-4" style={{ color }} />
          )}
          <p
            className="font-mono text-[11px] uppercase tracking-[0.12em]"
            style={{ color }}
          >
            {ok ? "DO" : "DON'T"}
          </p>
        </div>
        <p className="mt-3 text-[15px] font-medium text-[var(--color-fg)]">
          {title}
        </p>
        <p className="mt-2 text-[14px] leading-[1.55] text-[var(--color-fg-muted)]">
          {body}
        </p>
      </div>
    </div>
  );
}

export default function BrandPage() {
  return (
    <>
      <Nav />
      <main className="pt-16">
        {/* Hero */}
        <section className="border-b border-[var(--color-border)]">
          <div className="mx-auto grid max-w-[1440px] items-center gap-10 px-6 pt-16 pb-20 md:grid-cols-[1fr_auto] md:gap-14 md:px-10 md:pt-24 md:pb-28 lg:px-20">
            <div>
              <Eyebrow>BRAND GUIDELINES · V1</Eyebrow>
              <h1 className="mt-5 text-[44px] leading-[1.02] tracking-[-0.04em] font-semibold md:text-[64px] lg:text-[80px]">
                The Xerant brand,
                <br />
                in one page.
              </h1>
              <p className="mt-6 max-w-[640px] text-[17px] leading-[1.55] text-[var(--color-fg-muted)] md:text-[19px]">
                Mark, lockups, color, type, voice, and the whole asset kit —
                everything you need to put Xerant on a deck, a shirt, a GitHub
                README, or a billboard without asking anyone.
              </p>
              <div className="mt-8 flex flex-wrap items-center gap-3">
                <Link
                  href="/brand/xerant-brand-kit.zip"
                  className="inline-flex items-center gap-2 border border-[var(--color-accent)] bg-[var(--color-accent)] px-5 py-2.5 text-[14px] font-medium text-[var(--color-bg)] transition-opacity hover:opacity-90"
                >
                  <Download className="size-4" />
                  Download brand kit (.zip)
                </Link>
                <Link
                  href="#downloads"
                  className="inline-flex items-center gap-2 border border-[var(--color-border-strong)] px-5 py-2.5 text-[14px] text-[var(--color-fg)] transition-colors hover:bg-[var(--color-surface-2)]"
                >
                  Individual files
                  <ArrowUpRight className="size-4" />
                </Link>
              </div>
            </div>

            <div
              className="hidden md:block"
              style={{
                padding: 32,
                border: "1px solid var(--color-border)",
                background: "var(--color-surface-1)",
              }}
            >
              <XerantMark size={300} />
            </div>
          </div>
        </section>

        {/* The Mark */}
        <section id="mark" className="border-b border-[var(--color-border)]">
          <div className="mx-auto max-w-[1440px] px-6 py-20 md:px-10 md:py-28 lg:px-20">
            <Eyebrow>01 · THE MARK</Eyebrow>
            <H2>Agent Lattice.</H2>
            <Subhead>
              Four sandboxed agents on the perimeter, one amber orchestrator at
              the core. The X = Xerant, and the gesture of signing off a
              deploy. Always pair with <XerantWordmark fontSize={18} /> when
              product context isn&apos;t obvious.
            </Subhead>

            <div className="mt-12 grid gap-6 md:grid-cols-3 lg:grid-cols-4">
              <Tile label="Mark · on black">
                <XerantMark size={180} tone="dark" />
              </Tile>
              <Tile label="Mark · on light" tone="light">
                <XerantMark size={180} tone="light" />
              </Tile>
              <Tile label="Glyph only · no grid">
                <XerantMark size={180} tone="dark" glyphOnly />
              </Tile>
              <Tile label="Favicon · 32px">
                <XerantMark size={64} tone="dark" glyphOnly />
              </Tile>
            </div>

            <div className="mt-10 grid gap-6 md:grid-cols-2">
              <Tile label="Horizontal lockup" height={200}>
                <XerantLockupHorizontal size={56} />
              </Tile>
              <Tile label="Stacked lockup" height={320}>
                <XerantLockupStacked size={96} />
              </Tile>
            </div>

            <div className="mt-10 border border-[var(--color-border)] bg-[var(--color-surface-1)] p-6 md:p-8">
              <Eyebrow>CLEAR SPACE · MINIMUM SIZE</Eyebrow>
              <p className="mt-3 max-w-[640px] text-[15px] leading-[1.6] text-[var(--color-fg-muted)]">
                Keep clear space equal to one corner-node diameter around the
                mark in every direction. Don&apos;t render the full mark below
                24 px — drop the grid and use the glyph-only variant, or switch
                to the favicon.
              </p>
            </div>
          </div>
        </section>

        {/* Do / Don't */}
        <section className="border-b border-[var(--color-border)]">
          <div className="mx-auto max-w-[1440px] px-6 py-20 md:px-10 md:py-28 lg:px-20">
            <Eyebrow>02 · LOGO USAGE</Eyebrow>
            <H2>Do / don&apos;t.</H2>
            <Subhead>
              The mark is a system, not a decoration. Keep its proportions,
              spacing, and colors intact everywhere it appears.
            </Subhead>

            <div className="mt-12 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
              <RuleCard
                kind="do"
                title="Use amber for the X and core."
                body="Corner nodes stay outline-only. Amber is reserved for the diagonals and the orchestrator."
              >
                <XerantMark size={140} />
              </RuleCard>
              <RuleCard
                kind="do"
                title="Pair with the wordmark."
                body="When used away from product context, always pair the mark with XERANT set in Geist 600."
              >
                <XerantLockupHorizontal size={42} />
              </RuleCard>
              <RuleCard
                kind="dont"
                title="No gradients or recolors."
                body="The accent is #FFB800. No pinks, no chromed metal, no seasonal skins. If you need contrast, go monochrome."
              >
                <div style={{ transform: "scale(0.9)" }}>
                  <svg viewBox="0 0 400 400" width={140} height={140}>
                    <defs>
                      <linearGradient id="bad-grad" x1="0" y1="0" x2="1" y2="1">
                        <stop offset="0%" stopColor="#f472b6" />
                        <stop offset="100%" stopColor="#60a5fa" />
                      </linearGradient>
                    </defs>
                    <g transform="translate(200 200)">
                      <g stroke="url(#bad-grad)" strokeWidth={9} strokeLinecap="round">
                        <line x1={-90} y1={-90} x2={-22} y2={-22} />
                        <line x1={22} y1={22} x2={90} y2={90} />
                        <line x1={90} y1={-90} x2={22} y2={-22} />
                        <line x1={-22} y1={22} x2={-90} y2={90} />
                      </g>
                      <circle cx={0} cy={0} r={20} fill="url(#bad-grad)" />
                      <g fill="#000" stroke="#F5F5F5" strokeWidth={5}>
                        <circle cx={-110} cy={-110} r={15} />
                        <circle cx={110} cy={-110} r={15} />
                        <circle cx={-110} cy={110} r={15} />
                        <circle cx={110} cy={110} r={15} />
                      </g>
                    </g>
                  </svg>
                </div>
              </RuleCard>
              <RuleCard
                kind="dont"
                title="No stretching or rotating."
                body="The lattice is square by design. Don&apos;t skew, tilt, squash, or squish it for layout."
              >
                <div style={{ transform: "scaleX(1.4) rotate(12deg)" }}>
                  <XerantMark size={120} />
                </div>
              </RuleCard>
            </div>
          </div>
        </section>

        {/* Palette */}
        <section id="color" className="border-b border-[var(--color-border)]">
          <div className="mx-auto max-w-[1440px] px-6 py-20 md:px-10 md:py-28 lg:px-20">
            <Eyebrow>03 · COLOR</Eyebrow>
            <H2>The palette.</H2>
            <Subhead>
              Xerant ships in the dark. Amber is the only accent — use it for
              the mark, active states, and moments that need to feel alive.
              Everything else is black, white, and a ladder of greys.
            </Subhead>

            <div className="mt-12 grid gap-0 border border-[var(--color-border)] md:grid-cols-2 lg:grid-cols-3">
              {TOKENS.map((t, i) => (
                <div
                  key={t.token}
                  className="border-b border-r border-[var(--color-border)] p-0"
                  style={{
                    borderBottomWidth:
                      i >= TOKENS.length - 3 ? 0 : undefined,
                  }}
                >
                  <div
                    className="flex h-32 items-end p-5"
                    style={{ background: t.hex, color: t.fg }}
                  >
                    <div>
                      <p className="font-mono text-[11px] uppercase tracking-[0.12em] opacity-80">
                        {t.name}
                      </p>
                      <p className="font-mono text-[15px]">{t.hex}</p>
                    </div>
                  </div>
                  <div className="p-5">
                    <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-[var(--color-fg-dim)]">
                      {t.token}
                    </p>
                    <p className="mt-2 text-[14px] leading-[1.55] text-[var(--color-fg-muted)]">
                      {t.usage}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-10 border border-[var(--color-border)] bg-[var(--color-surface-1)] p-6 md:p-8">
              <Eyebrow>ACCENT DISCIPLINE</Eyebrow>
              <p className="mt-3 max-w-[720px] text-[15px] leading-[1.6] text-[var(--color-fg-muted)]">
                Amber is a signal, not a decoration. If more than one thing on
                a screen is amber, the system is lying about which one matters.
                Keep it to: the logo core, the active agent, the primary CTA,
                and live status.
              </p>
            </div>
          </div>
        </section>

        {/* Typography */}
        <section id="typography" className="border-b border-[var(--color-border)]">
          <div className="mx-auto max-w-[1440px] px-6 py-20 md:px-10 md:py-28 lg:px-20">
            <Eyebrow>04 · TYPOGRAPHY</Eyebrow>
            <H2>Geist. And Geist Mono.</H2>
            <Subhead>
              One sans family, one mono family. Use Geist for everything
              readable. Use Geist Mono for labels, status chips, terminal
              output, and moments that should feel like system text.
            </Subhead>

            <div className="mt-12 grid gap-6 md:grid-cols-2">
              <div className="border border-[var(--color-border)] p-8">
                <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-[var(--color-fg-dim)]">
                  GEIST · Sans
                </p>
                <p
                  className="mt-6 text-[72px] leading-[1] tracking-[-0.04em] font-semibold"
                  style={{ fontFamily: "var(--font-sans)" }}
                >
                  Aa
                </p>
                <p className="mt-8 text-[44px] leading-[1.04] tracking-[-0.035em] font-semibold">
                  Headlines set in 600.
                </p>
                <p className="mt-4 text-[17px] leading-[1.55] text-[var(--color-fg-muted)]">
                  Body copy lives at 400 with 15–17 px line-height 1.55. Keep
                  tracking at -0.02em for headlines, 0 for body.
                </p>
              </div>
              <div className="border border-[var(--color-border)] p-8">
                <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-[var(--color-fg-dim)]">
                  GEIST MONO
                </p>
                <p
                  className="mt-6 font-mono text-[72px] leading-[1] tracking-[-0.02em] font-semibold"
                >
                  Aa
                </p>
                <p className="mt-8 font-mono text-[22px] leading-[1.3] text-[var(--color-fg)]">
                  $ xerant deploy --prod
                </p>
                <p className="mt-4 font-mono text-[12px] uppercase tracking-[0.12em] text-[var(--color-fg-dim)]">
                  SYSTEM LABEL · 12PX · 0.12EM
                </p>
              </div>
            </div>

            <div className="mt-6 grid gap-0 border border-[var(--color-border)] md:grid-cols-4">
              {[
                { role: "Display", weight: "600", size: "72 / 88", track: "-0.045em" },
                { role: "H1 / H2", weight: "600", size: "44 / 56", track: "-0.035em" },
                { role: "Body", weight: "400", size: "15 / 17", track: "0" },
                { role: "Mono label", weight: "500", size: "11 / 12", track: "0.12em" },
              ].map((row, i, arr) => (
                <div
                  key={row.role}
                  className="p-6"
                  style={{
                    borderRight:
                      i < arr.length - 1
                        ? "1px solid var(--color-border)"
                        : undefined,
                  }}
                >
                  <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-[var(--color-fg-dim)]">
                    {row.role}
                  </p>
                  <dl className="mt-4 space-y-2 text-[13px]">
                    <div className="flex justify-between text-[var(--color-fg-muted)]">
                      <dt>Weight</dt>
                      <dd className="font-mono text-[var(--color-fg)]">{row.weight}</dd>
                    </div>
                    <div className="flex justify-between text-[var(--color-fg-muted)]">
                      <dt>Size (px)</dt>
                      <dd className="font-mono text-[var(--color-fg)]">{row.size}</dd>
                    </div>
                    <div className="flex justify-between text-[var(--color-fg-muted)]">
                      <dt>Tracking</dt>
                      <dd className="font-mono text-[var(--color-fg)]">{row.track}</dd>
                    </div>
                  </dl>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Voice */}
        <section id="voice" className="border-b border-[var(--color-border)]">
          <div className="mx-auto max-w-[1440px] px-6 py-20 md:px-10 md:py-28 lg:px-20">
            <Eyebrow>05 · VOICE</Eyebrow>
            <H2>How Xerant talks.</H2>
            <Subhead>
              Confident, specific, short. We&apos;re operators, not cheerleaders.
              We describe the work, not the mood around it.
            </Subhead>

            <div className="mt-12 grid gap-6 md:grid-cols-3">
              {[
                {
                  k: "Precise, not vague",
                  v: "\"Five sandboxed agents run your deploy lifecycle\" — not \"an AI platform for the cloud\".",
                },
                {
                  k: "Plain, not performative",
                  v: "\"Ship 60% cheaper than a 3-engineer rotation.\" No exclamation points. No hype words.",
                },
                {
                  k: "Calm, not cautious",
                  v: "We claim specific outcomes and back them with specific numbers. No hedging.",
                },
              ].map((x) => (
                <div
                  key={x.k}
                  className="border border-[var(--color-border)] bg-[var(--color-surface-1)] p-6"
                >
                  <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-[var(--color-accent)]">
                    {x.k}
                  </p>
                  <p className="mt-4 text-[15px] leading-[1.55] text-[var(--color-fg)]">
                    {x.v}
                  </p>
                </div>
              ))}
            </div>

            <div className="mt-12 grid gap-6 md:grid-cols-2">
              <div className="border border-[var(--color-border)] bg-[var(--color-surface-1)] p-6">
                <div className="flex items-center gap-2">
                  <Check className="size-4 text-[var(--color-success)]" />
                  <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-[var(--color-success)]">
                    WRITE THIS
                  </p>
                </div>
                <ul className="mt-5 space-y-3 text-[15px] leading-[1.55] text-[var(--color-fg)]">
                  <li>&ldquo;{BRAND_TAGLINE}&rdquo;</li>
                  <li>&ldquo;Five agents. One deploy lifecycle.&rdquo;</li>
                  <li>&ldquo;gVisor isolation per agent. Zero prompt injection blast radius.&rdquo;</li>
                  <li>&ldquo;Ship to prod, or don&apos;t. No maybes.&rdquo;</li>
                </ul>
              </div>
              <div className="border border-[var(--color-border)] bg-[var(--color-surface-1)] p-6">
                <div className="flex items-center gap-2">
                  <XIcon className="size-4 text-[var(--color-danger)]" />
                  <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-[var(--color-danger)]">
                    AVOID
                  </p>
                </div>
                <ul className="mt-5 space-y-3 text-[15px] leading-[1.55] text-[var(--color-fg-muted)]">
                  <li>Revolutionary, game-changing, next-gen.</li>
                  <li>AI-powered, AI-driven, AI-first.</li>
                  <li>Unlock the power of &ldquo;X&rdquo;.</li>
                  <li>Emojis in shipped copy. Ever.</li>
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* Agents roster */}
        <section id="agents" className="border-b border-[var(--color-border)]">
          <div className="mx-auto max-w-[1440px] px-6 py-20 md:px-10 md:py-28 lg:px-20">
            <Eyebrow>06 · THE AGENTS</Eyebrow>
            <H2>Always five. Always in order.</H2>
            <Subhead>
              When listing the team, keep the sequence stable — it matches the
              deploy lifecycle. Names stay uppercase, monospace, tracked wide.
            </Subhead>

            <div className="mt-12 flex flex-col items-stretch gap-4 md:flex-row md:items-center">
              {BRAND_AGENTS.map((name, i) => (
                <div
                  key={name}
                  className="flex flex-1 items-center gap-4 md:flex-col md:gap-3"
                >
                  <div
                    className="size-4 shrink-0 rounded-full border-2 border-[var(--color-fg)]"
                    aria-hidden
                  />
                  <span className="font-mono text-[12px] uppercase tracking-[0.2em] text-[var(--color-fg)]">
                    {name}
                  </span>
                  {i < BRAND_AGENTS.length - 1 && (
                    <span
                      className="hidden h-px flex-1 bg-[var(--color-accent)] md:block"
                      aria-hidden
                    />
                  )}
                </div>
              ))}
            </div>

            <p className="mt-8 font-mono text-[12px] uppercase tracking-[0.12em] text-[var(--color-fg-dim)]">
              TAGLINE · {BRAND_TAGLINE_UPPER}
            </p>
          </div>
        </section>

        {/* Downloads */}
        <section id="downloads" className="border-b border-[var(--color-border)]">
          <div className="mx-auto max-w-[1440px] px-6 py-20 md:px-10 md:py-28 lg:px-20">
            <Eyebrow>07 · DOWNLOADS</Eyebrow>
            <H2>Every asset, every format.</H2>
            <Subhead>
              All assets live under <code className="font-mono text-[var(--color-accent)]">xerant/public/brand/</code>.
              SVGs are the source of truth. Need a size that&apos;s not here?
              Re-export from <code className="font-mono text-[var(--color-accent)]">marketing/brand/</code>.
            </Subhead>

            <div className="mt-12 grid gap-6 md:grid-cols-2">
              {Object.entries(ASSETS).map(([group, items]) => (
                <div key={group} className="border border-[var(--color-border)]">
                  <div className="border-b border-[var(--color-border)] bg-[var(--color-surface-1)] px-5 py-4">
                    <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-[var(--color-fg-dim)]">
                      {group}
                    </p>
                  </div>
                  <ul>
                    {items.map((a) => (
                      <li
                        key={a.href}
                        className="flex items-center justify-between border-b border-[var(--color-border)] px-5 py-3 last:border-b-0 hover:bg-[var(--color-surface-2)]"
                      >
                        <div className="flex items-center gap-3">
                          <span
                            className="font-mono text-[10px] uppercase tracking-[0.12em]"
                            style={{
                              color:
                                a.kind === "svg"
                                  ? "var(--color-accent)"
                                  : a.kind === "zip"
                                    ? "var(--color-success)"
                                    : "var(--color-fg-muted)",
                            }}
                          >
                            {a.kind}
                          </span>
                          <Link
                            href={a.href}
                            className="font-mono text-[13px] text-[var(--color-fg)] hover:underline"
                            download
                          >
                            {a.label}
                          </Link>
                        </div>
                        {a.size && (
                          <span className="font-mono text-[11px] text-[var(--color-fg-dim)]">
                            {a.size}
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>

            <div className="mt-10 flex flex-wrap items-center gap-3">
              <Link
                href="/brand/xerant-brand-kit.zip"
                className="inline-flex items-center gap-2 border border-[var(--color-accent)] bg-[var(--color-accent)] px-5 py-2.5 text-[14px] font-medium text-[var(--color-bg)] transition-opacity hover:opacity-90"
                download
              >
                <Download className="size-4" />
                xerant-brand-kit.zip (all of it)
              </Link>
            </div>
          </div>
        </section>

        {/* Contact */}
        <section>
          <div className="mx-auto max-w-[1440px] px-6 py-16 md:px-10 md:py-20 lg:px-20">
            <div className="flex flex-col items-start justify-between gap-6 md:flex-row md:items-center">
              <div>
                <Eyebrow>QUESTIONS</Eyebrow>
                <p className="mt-3 text-[18px] leading-[1.55] text-[var(--color-fg)]">
                  Press, partnerships, or a use case we haven&apos;t thought of?
                </p>
              </div>
              <Link
                href="mailto:hi@xerant.cloud"
                className="inline-flex items-center gap-2 border border-[var(--color-border-strong)] px-5 py-2.5 text-[14px] text-[var(--color-fg)] transition-colors hover:bg-[var(--color-surface-2)]"
              >
                hi@xerant.cloud
                <ArrowUpRight className="size-4" />
              </Link>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
