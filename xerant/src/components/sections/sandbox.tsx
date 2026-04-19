import { Section, SectionHeader, FadeIn } from "@/components/section";
import { AGENTS } from "@/lib/agents";

const ROWS = [
  {
    title: "Syscall filtering",
    body: "gVisor intercepts every syscall. An agent compromised by a prompt injection cannot escape to the host.",
  },
  {
    title: "No shared secrets",
    body: "Vector holds deploy keys. Forge never sees them. The bus mediates every cross-agent call.",
  },
  {
    title: "Full audit log",
    body: "Every tool call, every handoff, every decision is logged and signed. Replay any deploy.",
  },
];

export function SandboxSection() {
  return (
    <Section id="security">
      <SectionHeader
        eyebrow="ISOLATION"
        headline="Each agent runs in its own sandbox."
        subhead="Kernel-level isolation per agent — gVisor syscall filter, seccomp-BPF, and network namespaces. If Forge is compromised, it cannot reach Warden's tools. If Vector is compromised, it cannot reach your prod keys."
      />

      <FadeIn delay={0.1}>
        <div className="border border-[var(--color-border)] bg-[var(--color-surface-1)] p-8 md:p-12">
          <p className="font-mono text-xs uppercase tracking-[0.08em] text-[var(--color-fg-dim)]">
            YOUR INFRASTRUCTURE
          </p>

          <div className="mt-10 grid grid-cols-2 gap-3 sm:grid-cols-5 sm:gap-4">
            {AGENTS.map((a) => (
              <div
                key={a.name}
                className="flex flex-col items-center border border-[var(--color-border-strong)] bg-[var(--color-bg)] p-4"
              >
                <div className="flex gap-1.5">
                  <span className="size-1.5 bg-[var(--color-fg-dim)]" />
                  <span className="size-1.5 bg-[var(--color-fg-dim)]" />
                </div>
                <p className="mt-4 font-mono text-[11px] uppercase tracking-[0.1em] text-[var(--color-fg-muted)]">
                  {a.name}
                </p>
              </div>
            ))}
          </div>

          <div className="mt-8 flex flex-col items-center">
            <div className="h-8 w-px bg-[var(--color-border-strong)]" />
            <div className="w-full border-t border-dashed border-[var(--color-border-strong)]" />
            <p className="mt-4 font-mono text-[12px] text-[var(--color-fg-dim)]">
              mediated bus
            </p>
          </div>

          <div className="mt-8 flex items-center gap-4">
            <div className="h-px flex-1 bg-[var(--color-border)]" />
            <p className="font-mono text-[11px] uppercase tracking-[0.1em] text-[var(--color-fg-dim)]">
              gVisor · seccomp · netns
            </p>
            <div className="h-px flex-1 bg-[var(--color-border)]" />
          </div>
        </div>
      </FadeIn>

      <div className="mt-20 md:mt-24">
        {ROWS.map((row, i) => (
          <FadeIn key={row.title} delay={0.05 * i}>
            <div className="grid grid-cols-1 gap-6 border-t border-[var(--color-border)] py-8 md:grid-cols-[280px_1fr] md:gap-10">
              <p className="font-mono text-xs uppercase tracking-[0.08em] text-[var(--color-fg-dim)]">
                0{i + 1}
              </p>
              <div>
                <h3 className="text-[22px] font-medium tracking-[-0.02em] text-[var(--color-fg)]">
                  {row.title}
                </h3>
                <p className="mt-3 max-w-[640px] text-[17px] leading-[1.55] text-[var(--color-fg-muted)]">
                  {row.body}
                </p>
              </div>
            </div>
          </FadeIn>
        ))}
        <div className="border-t border-[var(--color-border)]" />
      </div>
    </Section>
  );
}
