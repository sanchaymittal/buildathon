export type FaqItem = { q: string; a: string };

export const FAQ: readonly FaqItem[] = [
  {
    q: "What is Xerant?",
    a: "Xerant is a sandboxed multi-agent DevOps platform. It replaces a three-engineer on-call rotation with five specialized AI agents — Axiom (orchestrator), Forge (staff engineer), Warden (security), Vector (deployer), Sentry (observer). Each agent runs in its own gVisor sandbox and communicates only through a mediated bus, so a prompt injection in one agent cannot escalate to another. Free during beta.",
  },
  {
    q: "Is Xerant a Vercel or Netlify alternative?",
    a: "Yes, but with a different scope. Vercel and Netlify host your app; Xerant hosts your deploy team. Xerant runs in your cluster, writes the PR, reviews it for security, ships the canary, and watches the rollout — work that Vercel and Netlify leave to your engineers. Teams using Xerant cut total hosting plus engineering cost by roughly 60% versus Vercel Pro plus a rotation.",
  },
  {
    q: "What is a gVisor sandbox and why does Xerant use one per agent?",
    a: "gVisor is a Google-built user-space kernel that intercepts every syscall an application makes and forwards only the allowlisted ones to the host. Xerant gives each of its five agents a separate gVisor sandbox so that a compromised agent cannot read files, open sockets, or call tools that belong to a different agent. This is kernel-level isolation, not container-level — a container escape in Forge's sandbox still cannot reach Vector's deploy keys.",
  },
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
    a: "Sign in with GitHub at xerant.vercel.app/signin. We'll give you a sandbox repo and you'll watch the full team ship a PR in under 10 minutes. Free while we're in beta — no card, no seat limits.",
  },
] as const;
