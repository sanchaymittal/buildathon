import type { Agent } from "@/lib/agents";

export function AgentCard({ agent }: { agent: Agent }) {
  return (
    <article className="group flex h-full flex-col bg-[var(--color-surface-1)] p-8 transition-colors duration-200 hover:bg-[var(--color-surface-2)]">
      <p className="font-mono text-xs uppercase tracking-[0.08em] text-[var(--color-fg-dim)]">
        {agent.num} / {agent.role}
      </p>
      <h3 className="mt-10 text-[32px] font-semibold tracking-[-0.025em] leading-[1.05] text-[var(--color-fg)]">
        {agent.name}
      </h3>
      <p className="mt-4 text-[15px] leading-[1.55] text-[var(--color-fg-muted)]">
        {agent.blurb}
      </p>

      <div className="mt-auto pt-8">
        <div className="h-px w-full bg-[var(--color-border)]" />
        <p className="mt-6 font-mono text-xs uppercase tracking-[0.08em] text-[var(--color-fg-dim)]">
          tools
        </p>
        <p className="mt-3 font-mono text-[13px] text-[var(--color-fg-muted)]">
          {agent.tools.join(" · ")}
        </p>
      </div>
    </article>
  );
}
