export type FaqItem = { q: string; a: string };

export const FAQ: readonly FaqItem[] = [
  {
    q: "How is this different from GitHub Agentic Workflows?",
    a: "Xerant is a team, not an actor. Five agents with separate sandboxes and authority boundaries. Agentic Workflows runs one agent per workflow; we run five coordinated agents with mediated handoffs and independent rollback authority.",
  },
  {
    q: "What happens if an agent is prompt-injected?",
    a: "It's contained. The gVisor sandbox blocks syscalls outside its allowlist, and the mediated bus blocks cross-agent calls that aren't in its role contract. Warden can be compromised and still not reach Vector's deploy keys.",
  },
  {
    q: "Can I self-host?",
    a: "Yes, in the Enterprise tier. The full stack runs on your cluster; we ship the agent images and the bus.",
  },
  {
    q: "Which LLMs do you use?",
    a: "Claude for Axiom, Forge, and Warden. A smaller model (configurable) for Vector and Sentry where determinism matters more than reasoning.",
  },
  {
    q: "What if I don't trust it to deploy?",
    a: "Every agent can be set to advisory mode. Xerant drafts the PR, runs the review, stages the deploy — a human approves. Autonomy is a dial, not a switch.",
  },
  {
    q: "How do I try it?",
    a: "Request access. We'll give you a sandbox repo, you'll see the full team ship a PR inside 10 minutes.",
  },
] as const;
