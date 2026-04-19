import { Section, SectionHeader, FadeIn } from "@/components/section";
import {
  Sparkles,
  Lock,
  Settings,
  DollarSign,
  Rocket,
  Puzzle,
  TrendingUp,
  Wrench,
  Globe,
  Check,
  X,
  TriangleAlert,
} from "lucide-react";
import type { ComponentType, SVGProps } from "react";

type Tone = "pro" | "con" | "warn" | "neutral";
type Cell = { label: string; tone: Tone };
type Row = {
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  feature: string;
  vercel: Cell;
  netlify: Cell;
  xerant: Cell;
};

const ROWS: Row[] = [
  {
    icon: Sparkles,
    feature: "AI-Powered Automation",
    vercel: { label: "No", tone: "con" },
    netlify: { label: "No", tone: "con" },
    xerant: { label: "Core feature", tone: "pro" },
  },
  {
    icon: Lock,
    feature: "Vendor Lock-in",
    vercel: { label: "High", tone: "con" },
    netlify: { label: "Medium", tone: "warn" },
    xerant: { label: "0% — own the infra", tone: "pro" },
  },
  {
    icon: Settings,
    feature: "Full Infra Control",
    vercel: { label: "None", tone: "con" },
    netlify: { label: "None", tone: "con" },
    xerant: { label: "100% control", tone: "pro" },
  },
  {
    icon: DollarSign,
    feature: "Predictable Pricing",
    vercel: { label: "No", tone: "con" },
    netlify: { label: "Moderate", tone: "warn" },
    xerant: { label: "Linear scaling", tone: "pro" },
  },
  {
    icon: Rocket,
    feature: "Full-Stack Support",
    vercel: { label: "Strong", tone: "pro" },
    netlify: { label: "Limited", tone: "warn" },
    xerant: { label: "Complete", tone: "pro" },
  },
  {
    icon: Puzzle,
    feature: "Built-in Features",
    vercel: { label: "Minimal", tone: "con" },
    netlify: { label: "Many", tone: "pro" },
    xerant: { label: "Fully customizable", tone: "pro" },
  },
  {
    icon: TrendingUp,
    feature: "Scaling Efficiency",
    vercel: { label: "Expensive at scale", tone: "con" },
    netlify: { label: "Moderate", tone: "warn" },
    xerant: { label: "Cost-optimized", tone: "pro" },
  },
  {
    icon: Wrench,
    feature: "Developer Flexibility",
    vercel: { label: "Medium", tone: "warn" },
    netlify: { label: "Medium", tone: "warn" },
    xerant: { label: "High", tone: "pro" },
  },
  {
    icon: Globe,
    feature: "Multi-Framework Support",
    vercel: { label: "Limited", tone: "warn" },
    netlify: { label: "Broad", tone: "pro" },
    xerant: { label: "Unlimited", tone: "pro" },
  },
];

const TONE_ICON: Record<Tone, ComponentType<SVGProps<SVGSVGElement>>> = {
  pro: Check,
  con: X,
  warn: TriangleAlert,
  neutral: Check,
};

const TONE_COLOR: Record<Tone, string> = {
  pro: "text-[var(--color-success)]",
  con: "text-[var(--color-danger)]",
  warn: "text-[var(--color-accent)]",
  neutral: "text-[var(--color-fg-muted)]",
};

function CellView({ cell }: { cell: Cell }) {
  const Icon = TONE_ICON[cell.tone];
  return (
    <span className="inline-flex items-center gap-2">
      <Icon
        className={`size-4 shrink-0 ${TONE_COLOR[cell.tone]}`}
        strokeWidth={2.25}
        aria-hidden="true"
      />
      <span className="text-[14px] text-[var(--color-fg)]">{cell.label}</span>
    </span>
  );
}

export function CompareSection() {
  return (
    <Section id="compare">
      <SectionHeader
        eyebrow="COMPARE"
        headline="Against the usual suspects."
        subhead="Xerant is a Vercel alternative and Netlify alternative that ships a built-in AI DevOps team. Vercel and Netlify host your code; Xerant also writes, reviews, deploys, and monitors it — in your cluster, not theirs. How the three stack up on the nine capabilities platform teams care about:"
      />

      <FadeIn>
        {/* Desktop / tablet: real table */}
        <div className="hidden overflow-hidden border border-[var(--color-border)] bg-[var(--color-surface-1)] md:block">
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="border-b border-[var(--color-border)]">
                <th
                  scope="col"
                  className="w-[34%] px-6 py-5 font-mono text-[11px] font-medium uppercase tracking-[0.12em] text-[var(--color-fg-dim)]"
                >
                  Feature / Capability
                </th>
                <th
                  scope="col"
                  className="w-[22%] px-6 py-5 font-mono text-[11px] font-medium uppercase tracking-[0.12em] text-[var(--color-fg-muted)]"
                >
                  Vercel
                </th>
                <th
                  scope="col"
                  className="w-[22%] px-6 py-5 font-mono text-[11px] font-medium uppercase tracking-[0.12em] text-[var(--color-fg-muted)]"
                >
                  Netlify
                </th>
                <th
                  scope="col"
                  className="w-[22%] px-6 py-5 font-mono text-[11px] font-medium uppercase tracking-[0.12em] text-[var(--color-accent)]"
                >
                  Xerant.cloud
                </th>
              </tr>
            </thead>
            <tbody>
              {ROWS.map((row, i) => (
                <tr
                  key={row.feature}
                  className={`group border-b border-[var(--color-border)] transition-colors hover:bg-[var(--color-surface-2)] ${
                    i === ROWS.length - 1 ? "border-b-0" : ""
                  }`}
                >
                  <th
                    scope="row"
                    className="px-6 py-5 text-left align-middle font-medium"
                  >
                    <span className="inline-flex items-center gap-3">
                      <row.icon
                        className="size-[18px] shrink-0 text-[var(--color-fg-muted)] transition-colors group-hover:text-[var(--color-fg)]"
                        strokeWidth={1.5}
                        aria-hidden="true"
                      />
                      <span className="text-[15px] text-[var(--color-fg)]">
                        {row.feature}
                      </span>
                    </span>
                  </th>
                  <td className="px-6 py-5 align-middle">
                    <CellView cell={row.vercel} />
                  </td>
                  <td className="px-6 py-5 align-middle">
                    <CellView cell={row.netlify} />
                  </td>
                  <td className="bg-[color-mix(in_srgb,var(--color-accent)_6%,transparent)] px-6 py-5 align-middle">
                    <CellView cell={row.xerant} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Mobile: stacked cards */}
        <div className="flex flex-col gap-4 md:hidden">
          {ROWS.map((row) => (
            <div
              key={row.feature}
              className="border border-[var(--color-border)] bg-[var(--color-surface-1)] p-5"
            >
              <div className="flex items-center gap-3">
                <row.icon
                  className="size-[18px] shrink-0 text-[var(--color-fg-muted)]"
                  strokeWidth={1.5}
                  aria-hidden="true"
                />
                <span className="text-[15px] font-medium text-[var(--color-fg)]">
                  {row.feature}
                </span>
              </div>
              <dl className="mt-4 divide-y divide-[var(--color-border)]">
                <div className="flex items-center justify-between py-3">
                  <dt className="font-mono text-[11px] uppercase tracking-[0.12em] text-[var(--color-fg-dim)]">
                    Vercel
                  </dt>
                  <dd>
                    <CellView cell={row.vercel} />
                  </dd>
                </div>
                <div className="flex items-center justify-between py-3">
                  <dt className="font-mono text-[11px] uppercase tracking-[0.12em] text-[var(--color-fg-dim)]">
                    Netlify
                  </dt>
                  <dd>
                    <CellView cell={row.netlify} />
                  </dd>
                </div>
                <div className="flex items-center justify-between py-3">
                  <dt className="font-mono text-[11px] uppercase tracking-[0.12em] text-[var(--color-accent)]">
                    Xerant.cloud
                  </dt>
                  <dd>
                    <CellView cell={row.xerant} />
                  </dd>
                </div>
              </dl>
            </div>
          ))}
        </div>
      </FadeIn>
    </Section>
  );
}
