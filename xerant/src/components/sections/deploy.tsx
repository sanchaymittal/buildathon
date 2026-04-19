"use client";

import { useEffect, useMemo, useState } from "react";
import { Section, SectionHeader, FadeIn } from "@/components/section";

type DeployResult = {
  id: string;
  user_id?: string | null;
  url: string;
  status: string;
};

type DeployLogs = {
  deploy_id: string;
  logs: string;
};

const DEFAULT_API_BASE = "http://localhost:8000";

export function DeploySection() {
  const apiBase = useMemo(() => {
    return process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE;
  }, []);
  const [repository, setRepository] = useState("");
  const [userId, setUserId] = useState("");
  const [result, setResult] = useState<DeployResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [token, setToken] = useState("");
  const [branch, setBranch] = useState("main");
  const [logs, setLogs] = useState<string>("");
  const [polling, setPolling] = useState(false);

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setResult(null);
    setLogs("");
    setLoading(true);

    try {
      const requestBody = {
        repository: repository.trim(),
        user_id: userId.trim(),
        branch,
        github_token: token.trim() || undefined,
      };

      let response: Response;

      try {
        response = await fetch("/api/deploy", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(requestBody),
        });
      } catch (err) {
        response = await fetch(`${apiBase}/deployments/quick/replace`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(requestBody),
        });
      }

      const payloadText = await response.text();
      const payload = payloadText ? JSON.parse(payloadText) : null;
      if (!response.ok) {
        const detail = payload?.detail || payload?.message || "Deployment failed";
        throw new Error(detail);
      }

      const data = payload as DeployResult;
      setResult(data);
      setPolling(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!polling || !result) return;

    let alive = true;

    const poll = async () => {
      try {
        const statusParams = new URLSearchParams({
          deploy_id: result.id,
          user_id: userId.trim(),
        });
        const statusRes = await fetch(`/api/deploy/status?${statusParams.toString()}`);
        if (statusRes.ok) {
          const data = (await statusRes.json()) as DeployResult;
          if (!alive) return;
          setResult((prev) => (prev ? { ...prev, status: data.status } : data));
          if (data.status === "running" || data.status === "failed") {
            setPolling(false);
          }
        }

        const logsParams = new URLSearchParams({
          deploy_id: result.id,
          user_id: userId.trim(),
          tail: "200",
        });
        const logsRes = await fetch(`/api/deploy/logs?${logsParams.toString()}`);
        if (logsRes.ok) {
          const data = (await logsRes.json()) as DeployLogs;
          if (!alive) return;
          setLogs(data.logs || "");
        }
      } catch (err) {
        if (!alive) return;
        setPolling(false);
      }
    };

    poll();
    const interval = window.setInterval(poll, 4000);

    return () => {
      alive = false;
      window.clearInterval(interval);
    };
  }, [polling, result, userId]);

  return (
    <Section id="deploy" topBorder={false}>
      <SectionHeader
        eyebrow="DEPLOY"
        headline="Drop a repo. Get a live URL."
        subhead="Paste a GitHub repo and your internal user ID. Xerant wipes any previous deployment for that repo + user, then launches a fresh container and returns the URL."
      />

      <FadeIn>
        <div className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
          <form
            onSubmit={onSubmit}
            className="border border-[var(--color-border)] bg-[var(--color-surface-1)] p-8 md:p-10"
          >
            <div className="grid gap-6">
              <label className="grid gap-2 text-sm text-[var(--color-fg-muted)]">
                Repository (owner/repo)
                <input
                  value={repository}
                  onChange={(event) => setRepository(event.target.value)}
                  placeholder="acme/app"
                  required
                  className="w-full border border-[var(--color-border-strong)] bg-black/40 px-4 py-3 font-mono text-sm text-[var(--color-fg)] outline-none focus:border-[var(--color-accent)]"
                />
              </label>

              <label className="grid gap-2 text-sm text-[var(--color-fg-muted)]">
                User ID (internal)
                <input
                  value={userId}
                  onChange={(event) => setUserId(event.target.value)}
                  placeholder="user-123"
                  required
                  className="w-full border border-[var(--color-border-strong)] bg-black/40 px-4 py-3 font-mono text-sm text-[var(--color-fg)] outline-none focus:border-[var(--color-accent)]"
                />
              </label>

              <label className="grid gap-2 text-sm text-[var(--color-fg-muted)]">
                Branch
                <select
                  value={branch}
                  onChange={(event) => setBranch(event.target.value)}
                  className="w-full border border-[var(--color-border-strong)] bg-black/40 px-4 py-3 font-mono text-sm text-[var(--color-fg)] outline-none focus:border-[var(--color-accent)]"
                >
                  <option value="main">main</option>
                  <option value="master">master</option>
                </select>
              </label>

              <label className="grid gap-2 text-sm text-[var(--color-fg-muted)]">
                GitHub Token (optional)
                <input
                  value={token}
                  onChange={(event) => setToken(event.target.value)}
                  placeholder="ghp_..."
                  className="w-full border border-[var(--color-border-strong)] bg-black/40 px-4 py-3 font-mono text-sm text-[var(--color-fg)] outline-none focus:border-[var(--color-accent)]"
                />
              </label>
            </div>

            <div className="mt-8 flex flex-wrap items-center gap-4">
              <button
                type="submit"
                disabled={loading}
                className="bg-[var(--color-accent)] px-6 py-3 text-xs uppercase tracking-[0.2em] text-black transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? "Deploying..." : "Deploy Now"}
              </button>
              <p className="text-xs text-[var(--color-fg-dim)]">
                API: {apiBase}
              </p>
            </div>

            {error && (
              <p className="mt-6 border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                {error}
              </p>
            )}
          </form>

          <div className="border border-[var(--color-border)] bg-[var(--color-surface-1)] p-8 md:p-10">
            <p className="font-mono text-xs uppercase tracking-[0.14em] text-[var(--color-fg-dim)]">
              Latest deployment
            </p>
            {result ? (
              <div className="mt-6 grid gap-6 text-sm text-[var(--color-fg-muted)]">
                <div>
                  <p className="text-xs uppercase tracking-[0.12em] text-[var(--color-fg-dim)]">ID</p>
                  <p className="mt-2 font-mono text-[var(--color-fg)]">{result.id}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.12em] text-[var(--color-fg-dim)]">Status</p>
                  <p className="mt-2 font-mono text-[var(--color-fg)]">
                    {result.status}
                    {polling && <span className="ml-2 text-[var(--color-fg-dim)]">(live)</span>}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.12em] text-[var(--color-fg-dim)]">URL</p>
                  <a
                    href={result.url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-2 inline-block break-all font-mono text-[var(--color-accent)]"
                  >
                    {result.url}
                  </a>
                </div>
                <div>
                  <div className="flex items-center justify-between">
                    <p className="text-xs uppercase tracking-[0.12em] text-[var(--color-fg-dim)]">
                      Logs (tail)
                    </p>
                    <button
                      type="button"
                      onClick={() => setPolling(true)}
                      className="text-xs uppercase tracking-[0.18em] text-[var(--color-fg-dim)] hover:text-[var(--color-accent)]"
                    >
                      Refresh
                    </button>
                  </div>
                  <pre className="mt-3 max-h-64 overflow-auto border border-[var(--color-border-strong)] bg-black/40 p-3 text-[12px] text-[var(--color-fg)]">
                    {logs || "No logs yet."}
                  </pre>
                </div>
              </div>
            ) : (
              <p className="mt-6 text-sm text-[var(--color-fg-muted)]">
                Submit a repo to see the deployment ID and URL.
              </p>
            )}
          </div>
        </div>
      </FadeIn>
    </Section>
  );
}
