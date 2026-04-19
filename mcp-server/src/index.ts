#!/usr/bin/env node
/**
 * Xerant MCP server.
 *
 * Runs over stdio so it can be spawned by OpenCode (see opencode.json).
 *
 * Environment:
 *   XERANT_API_URL  Base URL of the internal DevOps API. Default http://localhost:8000
 *   XERANT_API_KEY  Optional bearer token sent on every request.
 *
 * Tool naming: `xerant_*` so they don't collide with other MCP servers in a session.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

import { XerantApiError, XerantClient } from "./client.js";

const baseUrl = process.env.XERANT_API_URL ?? "http://localhost:8000";
const apiKey = process.env.XERANT_API_KEY;
const timeoutMs = Number(process.env.XERANT_API_TIMEOUT_MS ?? "60000");

const client = new XerantClient({ baseUrl, apiKey, timeoutMs });

const server = new McpServer(
  { name: "xerant", version: "0.1.0" },
  {
    capabilities: { tools: {} },
    instructions:
      "Xerant is an internal Docker-based deploy platform. Use these tools to deploy GitHub " +
      "repositories, inspect containers, and query GitHub metadata. Deploy targets a 'tier' by " +
      "convention via the DEPLOY_ENV env var and the deployment name suffix.",
  },
);

// ---------- helpers ----------

/**
 * Wrap a handler so any thrown error becomes an MCP-friendly error response
 * instead of crashing the transport. MCP expects either a success content array
 * or { isError: true, content: [...] }.
 */
function safe<T>(fn: () => Promise<T>): Promise<{ content: Array<{ type: "text"; text: string }>; isError?: true }> {
  return fn()
    .then((value) => ({ content: [{ type: "text" as const, text: toPrettyJson(value) }] }))
    .catch((err: unknown) => ({
      isError: true as const,
      content: [{ type: "text" as const, text: formatError(err) }],
    }));
}

function toPrettyJson(value: unknown): string {
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function formatError(err: unknown): string {
  if (err instanceof XerantApiError) {
    return `Xerant API error (${err.status}): ${err.message}\n${toPrettyJson(err.body)}`;
  }
  if (err instanceof Error) return `${err.name}: ${err.message}`;
  return String(err);
}

function canonicalEnvironment(env: string | undefined): string | undefined {
  if (!env) return undefined;
  const map: Record<string, string> = {
    prod: "production",
    production: "production",
    staging: "staging",
    preview: "preview",
    dev: "development",
    development: "development",
  };
  const normalized = map[env.toLowerCase()];
  if (!normalized) throw new Error(`Unknown environment '${env}'. Expected prod|staging|preview|dev.`);
  return normalized;
}

function deriveDeployName(repository: string, environment: string | undefined, explicit: string | undefined): string {
  if (explicit) return explicit;
  const repoName = repository.split("/").pop()?.replace(/\.git$/, "") ?? "app";
  const safeName = repoName.toLowerCase().replace(/[^a-z0-9_-]/g, "-");
  return environment ? `${safeName}-${environment}` : safeName;
}

// ---------- health ----------

server.registerTool(
  "xerant_health",
  {
    title: "Xerant API health",
    description: "Ping the internal server's /health endpoint. Returns service status.",
    inputSchema: {},
  },
  () => safe(() => client.health()),
);

server.registerTool(
  "xerant_docker_health",
  {
    title: "Xerant Docker health",
    description: "Check whether the Docker daemon the server uses is reachable.",
    inputSchema: {},
  },
  () => safe(() => client.dockerHealth()),
);

// ---------- deployments ----------

server.registerTool(
  "xerant_deploy",
  {
    title: "Deploy repository",
    description:
      "Deploy a GitHub repository to the Xerant Docker platform. " +
      "Accepts an optional `environment` (prod|staging|preview|dev) which is passed through as " +
      "the DEPLOY_ENV env var and appended to the deployment name unless `name` is explicit.",
    inputSchema: {
      repository: z
        .string()
        .min(1)
        .describe("GitHub repository in `owner/repo` form or a full URL."),
      branch: z.string().default("main").describe("Git branch to deploy."),
      environment: z
        .enum(["prod", "production", "staging", "preview", "dev", "development"])
        .optional()
        .describe("Environment tier. Mapped to DEPLOY_ENV and name suffix."),
      container_port: z.number().int().positive().default(80),
      env: z.record(z.string(), z.string()).default({}).describe("Runtime env vars for the container."),
      build_args: z.record(z.string(), z.string()).default({}).describe("Docker build args."),
      name: z.string().optional().describe("Explicit deployment name. Overrides auto-derived name."),
    },
  },
  (args) =>
    safe(async () => {
      const canonical = canonicalEnvironment(args.environment);
      const envVars = { ...args.env };
      if (canonical) envVars.DEPLOY_ENV = canonical;
      const name = deriveDeployName(args.repository, canonical, args.name);

      return client.createDeployment({
        repository: args.repository,
        branch: args.branch,
        container_port: args.container_port,
        env: envVars,
        build_args: args.build_args,
        name,
      });
    }),
);

server.registerTool(
  "xerant_list_deployments",
  {
    title: "List deployments",
    description: "List all known Xerant deployments.",
    inputSchema: {},
  },
  () => safe(() => client.listDeployments()),
);

server.registerTool(
  "xerant_get_deployment",
  {
    title: "Get deployment",
    description: "Fetch details for a single deployment by id.",
    inputSchema: { id: z.string().min(1) },
  },
  (args) => safe(() => client.getDeployment(args.id)),
);

server.registerTool(
  "xerant_deployment_logs",
  {
    title: "Deployment logs",
    description: "Get the tail of container logs for a deployment.",
    inputSchema: {
      id: z.string().min(1),
      tail: z.number().int().positive().default(100),
    },
  },
  (args) => safe(() => client.deploymentLogs(args.id, args.tail)),
);

server.registerTool(
  "xerant_stop_deployment",
  {
    title: "Stop deployment",
    description: "Stop a running deployment. Container persists and can be started again.",
    inputSchema: { id: z.string().min(1) },
  },
  (args) => safe(() => client.stopDeployment(args.id)),
);

server.registerTool(
  "xerant_start_deployment",
  {
    title: "Start deployment",
    description: "Start a previously stopped deployment.",
    inputSchema: { id: z.string().min(1) },
  },
  (args) => safe(() => client.startDeployment(args.id)),
);

server.registerTool(
  "xerant_restart_deployment",
  {
    title: "Restart deployment",
    description: "Restart a deployment's container.",
    inputSchema: { id: z.string().min(1) },
  },
  (args) => safe(() => client.restartDeployment(args.id)),
);

server.registerTool(
  "xerant_redeploy",
  {
    title: "Redeploy",
    description: "Rebuild and redeploy the latest branch code for a deployment.",
    inputSchema: { id: z.string().min(1) },
  },
  (args) => safe(() => client.redeployDeployment(args.id)),
);

server.registerTool(
  "xerant_remove_deployment",
  {
    title: "Remove deployment",
    description: "Permanently remove a deployment and its container. Irreversible.",
    inputSchema: { id: z.string().min(1) },
  },
  (args) => safe(() => client.removeDeployment(args.id)),
);

// ---------- containers ----------

server.registerTool(
  "xerant_list_containers",
  {
    title: "List containers",
    description: "List containers visible to the Xerant server's Docker daemon.",
    inputSchema: {
      all: z.boolean().default(false).describe("Include stopped containers."),
      label_filter: z
        .string()
        .optional()
        .describe("Filter `key=value`. Example: `xerant.managed=true`."),
    },
  },
  (args) => safe(() => client.listContainers({ all: args.all, label_filter: args.label_filter })),
);

server.registerTool(
  "xerant_get_container",
  {
    title: "Get container",
    description: "Fetch container details by id or name.",
    inputSchema: { id: z.string().min(1) },
  },
  (args) => safe(() => client.getContainer(args.id)),
);

server.registerTool(
  "xerant_container_logs",
  {
    title: "Container logs",
    description: "Tail container logs.",
    inputSchema: {
      id: z.string().min(1),
      tail: z.number().int().positive().default(100),
      timestamps: z.boolean().default(false),
    },
  },
  (args) =>
    safe(() => client.containerLogs(args.id, { tail: args.tail, timestamps: args.timestamps })),
);

// ---------- github ----------

server.registerTool(
  "xerant_github_get_repo",
  {
    title: "GitHub repository",
    description: "Look up a GitHub repository via the Xerant server (uses server-side GitHub token).",
    inputSchema: { owner: z.string().min(1), repo: z.string().min(1) },
  },
  (args) => safe(() => client.getRepository(args.owner, args.repo)),
);

server.registerTool(
  "xerant_github_list_branches",
  {
    title: "GitHub branches",
    description: "List branches of a GitHub repository via the Xerant server.",
    inputSchema: { owner: z.string().min(1), repo: z.string().min(1) },
  },
  (args) => safe(() => client.listBranches(args.owner, args.repo)),
);

server.registerTool(
  "xerant_github_get_file",
  {
    title: "GitHub file contents",
    description:
      "Fetch a single file's contents from a GitHub repo via the Xerant server. " +
      "Used by the /xerant skill to verify the remote Dockerfile matches the local one.",
    inputSchema: {
      owner: z.string().min(1),
      repo: z.string().min(1),
      path: z.string().min(1),
      ref: z.string().optional().describe("Branch, tag, or commit. Defaults to server-side default branch."),
    },
  },
  (args) => safe(() => client.getRepoFileContent(args.owner, args.repo, args.path, args.ref)),
);

// ---------- entry ----------

async function main(): Promise<void> {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  // Log via stderr so it doesn't pollute the MCP stdio channel.
  process.stderr.write(
    `xerant-mcp ready. baseUrl=${baseUrl} apiKey=${apiKey ? "[set]" : "[unset]"}\n`,
  );
}

main().catch((err: unknown) => {
  process.stderr.write(`xerant-mcp fatal: ${err instanceof Error ? err.stack ?? err.message : String(err)}\n`);
  process.exit(1);
});
