import { Section, SectionHeader, FadeIn } from "@/components/section";
import { GitBranch, ListChecks, Server } from "lucide-react";

const ITEMS = [
  {
    icon: GitBranch,
    title: "GitHub",
    body: "Point Xerant at a repo. It opens PRs, reviews its own PRs, and merges when Warden approves.",
  },
  {
    icon: ListChecks,
    title: "Linear",
    body: "Assign a Linear issue to Xerant. Axiom picks it up, the team ships it, the issue closes itself.",
  },
  {
    icon: Server,
    title: "Your cluster",
    body: "Bring your own k8s. Vector deploys via your existing CI or directly via kubectl.",
  },
];

export function IntegrationSection() {
  return (
    <Section id="integration">
      <SectionHeader
        eyebrow="INTEGRATION"
        headline="Drops into the stack you already have."
      />

      <div className="grid grid-cols-1 gap-px border border-[var(--color-border)] bg-[var(--color-border)] md:grid-cols-3">
        {ITEMS.map((item, i) => (
          <FadeIn key={item.title} delay={0.05 * i} className="h-full">
            <div className="flex h-full flex-col bg-[var(--color-bg)] p-10">
              <item.icon
                className="size-6 text-[var(--color-fg)]"
                strokeWidth={1.5}
                aria-hidden="true"
              />
              <h3 className="mt-10 text-[24px] font-medium tracking-[-0.02em] text-[var(--color-fg)]">
                {item.title}
              </h3>
              <p className="mt-4 text-[15px] leading-[1.55] text-[var(--color-fg-muted)]">
                {item.body}
              </p>
            </div>
          </FadeIn>
        ))}
      </div>
    </Section>
  );
}
