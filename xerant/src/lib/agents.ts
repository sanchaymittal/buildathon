export type Agent = {
  num: string;
  role: string;
  name: string;
  blurb: string;
  tools: readonly string[];
  stage: {
    title: string;
    lines: readonly string[];
  };
};

export const AGENTS: readonly Agent[] = [
  {
    num: "01",
    role: "Orchestrator",
    name: "Axiom",
    blurb:
      "Receives the task, decomposes it, assigns work, holds shared state across the team.",
    tools: ["linear", "github", "slack"],
    stage: {
      title: "Axiom · Orchestrator",
      lines: [
        "$ task received · linear MFA-142",
        "> axiom: decomposing · 4 subtasks identified",
        "> axiom: assigning forge, warden",
      ],
    },
  },
  {
    num: "02",
    role: "Staff Engineer",
    name: "Forge",
    blurb:
      "Writes the diff. Owns the branch. Responds to review in-loop until the PR is approved.",
    tools: ["git", "editor", "test-runner"],
    stage: {
      title: "Forge · Staff Engineer",
      lines: [
        "> forge: drafting patch · src/api/rates.ts",
        "> forge: +47 -12 · tests updated",
        "> forge: handoff → warden",
      ],
    },
  },
  {
    num: "03",
    role: "Security Engineer",
    name: "Warden",
    blurb:
      "Runs SAST, dependency, secrets, and IAM scans on every PR. Blocks or approves. Deterministic-first.",
    tools: ["semgrep", "trivy", "gitleaks"],
    stage: {
      title: "Warden · Security Engineer",
      lines: [
        "> warden: scanning · semgrep, trivy, gitleaks",
        "> warden: 0 critical · 1 advisory (reviewed)",
        "> warden: approved · handoff → vector",
      ],
    },
  },
  {
    num: "04",
    role: "Deployer",
    name: "Vector",
    blurb:
      "Builds the image, pushes the registry, rolls out with canary or blue-green. Owns the deploy window.",
    tools: ["docker", "kubectl", "gh-actions"],
    stage: {
      title: "Vector · Deployer",
      lines: [
        "> vector: building image · xerant/rates:a7f2e1",
        "> vector: pushing to registry",
        "> vector: rolling out · canary 10% → 100%",
      ],
    },
  },
  {
    num: "05",
    role: "Observer",
    name: "Sentry",
    blurb:
      "Watches pod health, error rate, and p99 for the rollout window. Has rollback authority.",
    tools: ["prometheus", "loki", "pagerduty"],
    stage: {
      title: "Sentry · Observer",
      lines: [
        "> sentry: watching · p99, error rate, pod health",
        "> sentry: 120s clear · promoting to stable",
        "✓ deployed · 2m 14s · rollback available",
      ],
    },
  },
] as const;
