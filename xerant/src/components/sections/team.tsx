import { AGENTS } from "@/lib/agents";
import { AgentCard } from "@/components/agent-card";
import { Section, SectionHeader, FadeIn } from "@/components/section";

export function TeamSection() {
  return (
    <Section id="team">
      <SectionHeader
        eyebrow="THE TEAM"
        headline="Five agents. Five roles. One sandbox each."
        subhead="Not a single loop pretending to be a team. Five specialized agents with distinct prompts, distinct tools, and distinct blast radii."
      />

      <div className="grid grid-cols-1 gap-px border border-[var(--color-border)] bg-[var(--color-border)] md:grid-cols-2 lg:grid-cols-5">
        {AGENTS.map((agent, i) => (
          <FadeIn
            key={agent.name}
            delay={0.05 * i}
            y={24}
            className="h-full"
          >
            <AgentCard agent={agent} />
          </FadeIn>
        ))}
      </div>
    </Section>
  );
}
