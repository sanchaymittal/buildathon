/**
 * Thin HTTP client for the Xerant internal DevOps API.
 *
 * Uses the global `fetch` available in Node 20+. Sends `Authorization: Bearer`
 * when `XERANT_API_KEY` is set so the bridge is forward-compatible with a
 * server that eventually adds auth; the current server ignores it.
 */

export interface ClientConfig {
  baseUrl: string;
  apiKey?: string;
  /** Request timeout in ms. Default 60s. */
  timeoutMs?: number;
}

export class XerantApiError extends Error {
  readonly status: number;
  readonly body: unknown;
  constructor(status: number, body: unknown, message?: string) {
    super(message ?? `Xerant API error ${status}`);
    this.name = "XerantApiError";
    this.status = status;
    this.body = body;
  }
}

export class XerantClient {
  private readonly baseUrl: string;
  private readonly apiKey: string | undefined;
  private readonly timeoutMs: number;

  constructor(config: ClientConfig) {
    // Strip trailing slash so path joining is predictable.
    this.baseUrl = config.baseUrl.replace(/\/+$/, "");
    this.apiKey = config.apiKey;
    this.timeoutMs = config.timeoutMs ?? 60_000;
  }

  private async request<T>(
    method: string,
    path: string,
    init?: { body?: unknown; query?: Record<string, string | number | boolean | undefined> },
  ): Promise<T> {
    const url = new URL(this.baseUrl + path);
    if (init?.query) {
      for (const [k, v] of Object.entries(init.query)) {
        if (v !== undefined) url.searchParams.set(k, String(v));
      }
    }

    const headers: Record<string, string> = { accept: "application/json" };
    if (init?.body !== undefined) headers["content-type"] = "application/json";
    if (this.apiKey) headers["authorization"] = `Bearer ${this.apiKey}`;

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);
    let res: Response;
    try {
      res = await fetch(url, {
        method,
        headers,
        body: init?.body !== undefined ? JSON.stringify(init.body) : undefined,
        signal: controller.signal,
      });
    } catch (err) {
      if ((err as Error).name === "AbortError") {
        throw new XerantApiError(0, null, `Request timed out after ${this.timeoutMs}ms: ${method} ${path}`);
      }
      throw new XerantApiError(0, null, `Network error calling ${method} ${path}: ${(err as Error).message}`);
    } finally {
      clearTimeout(timer);
    }

    const text = await res.text();
    let parsed: unknown = text;
    if (text.length > 0 && res.headers.get("content-type")?.includes("application/json")) {
      try {
        parsed = JSON.parse(text);
      } catch {
        /* keep text */
      }
    }

    if (!res.ok) {
      const detail =
        typeof parsed === "object" && parsed !== null && "detail" in parsed
          ? (parsed as { detail: unknown }).detail
          : parsed;
      throw new XerantApiError(res.status, parsed, `${method} ${path} -> ${res.status}: ${stringifyDetail(detail)}`);
    }

    return parsed as T;
  }

  // ---------- health ----------
  health() {
    return this.request<{ status: string; service: string }>("GET", "/health");
  }

  dockerHealth() {
    return this.request<{ status: string; docker: string }>("GET", "/health/docker");
  }

  // ---------- deployments ----------
  createDeployment(body: {
    repository: string;
    branch?: string;
    container_port?: number;
    env?: Record<string, string>;
    build_args?: Record<string, string>;
    name?: string;
  }) {
    return this.request<Deployment>("POST", "/deployments", { body });
  }

  listDeployments() {
    return this.request<Deployment[]>("GET", "/deployments");
  }

  getDeployment(id: string) {
    return this.request<Deployment>("GET", `/deployments/${encodeURIComponent(id)}`);
  }

  deploymentLogs(id: string, tail = 100) {
    return this.request<{ deploy_id: string; logs: string }>(
      "GET",
      `/deployments/${encodeURIComponent(id)}/logs`,
      { query: { tail } },
    );
  }

  stopDeployment(id: string) {
    return this.request<Deployment>("POST", `/deployments/${encodeURIComponent(id)}/stop`);
  }

  startDeployment(id: string) {
    return this.request<Deployment>("POST", `/deployments/${encodeURIComponent(id)}/start`);
  }

  restartDeployment(id: string) {
    return this.request<Deployment>("POST", `/deployments/${encodeURIComponent(id)}/restart`);
  }

  redeployDeployment(id: string) {
    return this.request<Deployment>("POST", `/deployments/${encodeURIComponent(id)}/redeploy`);
  }

  removeDeployment(id: string) {
    return this.request<{ status: string; deploy_id?: string }>("DELETE", `/deployments/${encodeURIComponent(id)}`);
  }

  // ---------- containers ----------
  listContainers(params?: { all?: boolean; label_filter?: string }) {
    return this.request<Record<string, unknown>[]>("GET", "/containers", { query: params });
  }

  getContainer(id: string) {
    return this.request<Record<string, unknown>>("GET", `/containers/${encodeURIComponent(id)}`);
  }

  containerLogs(id: string, params?: { tail?: number; timestamps?: boolean }) {
    return this.request<{ container_id: string; logs: string }>(
      "GET",
      `/containers/${encodeURIComponent(id)}/logs`,
      { query: params },
    );
  }

  // ---------- github ----------
  getRepository(owner: string, repo: string) {
    return this.request<Record<string, unknown>>(
      "GET",
      `/github/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}`,
    );
  }

  listBranches(owner: string, repo: string) {
    return this.request<Record<string, unknown>[]>(
      "GET",
      `/github/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/branches`,
    );
  }

  /**
   * Fetch a file's contents from the repo. Requires the /contents route on the
   * internal server (see internal-server/src/api/routes/github.py).
   */
  getRepoFileContent(owner: string, repo: string, path: string, ref?: string) {
    return this.request<{ path: string; ref?: string; encoding?: string; content?: string; decoded_content?: string }>(
      "GET",
      `/github/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/contents/${encodePath(path)}`,
      { query: { ref } },
    );
  }
}

function encodePath(p: string): string {
  return p.split("/").map(encodeURIComponent).join("/");
}

function stringifyDetail(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

// ---------- shared types ----------
export interface Deployment {
  id: string;
  repository: string;
  branch: string;
  image: string;
  container_id: string;
  container_name: string;
  host_port: number;
  container_port: number;
  url: string;
  status: string;
  created_at: string;
  logs_tail?: string | null;
  env: Record<string, string>;
  labels: Record<string, string>;
}
