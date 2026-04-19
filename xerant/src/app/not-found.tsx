import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-6 text-center">
      <p className="font-mono text-xs uppercase tracking-[0.08em] text-[var(--color-fg-dim)]">
        404
      </p>
      <h1 className="mt-6 text-[clamp(2.5rem,6vw,4.5rem)] font-semibold leading-[1.02] tracking-[-0.04em] text-[var(--color-fg)]">
        Route not deployed.
      </h1>
      <p className="mt-6 max-w-[480px] text-[17px] leading-[1.55] text-[var(--color-fg-muted)]">
        The page you are looking for does not exist. Sentry would have caught
        this in production.
      </p>
      <Link
        href="/"
        className="mt-10 inline-flex items-center gap-2 rounded-md border border-[var(--color-border-strong)] px-6 py-[14px] text-[15px] text-[var(--color-fg)] transition-colors hover:border-[var(--color-fg-muted)] hover:bg-[var(--color-surface-1)]"
      >
        Return home
      </Link>
    </main>
  );
}
