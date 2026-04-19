import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { signIn } from "@/auth";

function IconGithub({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className}
      aria-hidden="true"
    >
      <path d="M12 .5C5.37.5 0 5.78 0 12.292c0 5.211 3.438 9.63 8.205 11.188.6.111.82-.254.82-.567 0-.28-.01-1.022-.015-2.005-3.338.711-4.042-1.582-4.042-1.582-.546-1.361-1.335-1.725-1.335-1.725-1.087-.731.084-.716.084-.716 1.205.082 1.838 1.215 1.838 1.215 1.07 1.803 2.809 1.282 3.495.981.108-.763.417-1.282.76-1.577-2.665-.295-5.466-1.309-5.466-5.827 0-1.287.465-2.339 1.235-3.164-.135-.298-.54-1.497.105-3.121 0 0 1.005-.316 3.3 1.209.96-.262 1.98-.392 3-.398 1.02.006 2.04.136 3 .398 2.28-1.525 3.285-1.209 3.285-1.209.645 1.624.24 2.823.12 3.121.765.825 1.23 1.877 1.23 3.164 0 4.53-2.805 5.527-5.475 5.817.42.354.81 1.077.81 2.182 0 1.578-.015 2.846-.015 3.229 0 .309.21.678.825.56C20.565 21.917 24 17.5 24 12.292 24 5.78 18.627.5 12 .5z" />
    </svg>
  );
}

function IconGoogle({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true">
      <path
        fill="#EA4335"
        d="M12 10.2v3.87h5.52c-.24 1.4-1.68 4.11-5.52 4.11-3.32 0-6.03-2.75-6.03-6.13S8.68 5.92 12 5.92c1.89 0 3.15.8 3.87 1.49l2.64-2.54C16.86 3.27 14.65 2.3 12 2.3 6.5 2.3 2.05 6.75 2.05 12.25S6.5 22.2 12 22.2c6.14 0 10.2-4.31 10.2-10.38 0-.7-.08-1.24-.17-1.77H12z"
      />
      <path
        fill="#34A853"
        d="M3.88 7.5l3.17 2.33c.86-1.62 2.47-2.75 4.95-2.75 1.89 0 3.15.8 3.87 1.49l2.64-2.54C16.86 3.27 14.65 2.3 12 2.3 7.84 2.3 4.26 4.67 2.55 8.1l1.33-.6z"
      />
      <path
        fill="#FBBC05"
        d="M12 22.2c2.64 0 4.85-.87 6.47-2.36l-3.17-2.45c-.86.6-2.02.97-3.3.97-2.54 0-4.7-1.7-5.47-4.04l-3.17 2.44C4.24 19.77 7.8 22.2 12 22.2z"
      />
      <path
        fill="#4285F4"
        d="M22.2 12.25c0-.7-.08-1.24-.17-1.77H12v3.87h5.73c-.24 1.05-.94 2.42-2.71 3.37l3.17 2.45c1.85-1.7 3.01-4.21 3.01-7.92z"
      />
    </svg>
  );
}

export default function SignInPage() {
  const ghConfigured = Boolean(
    process.env.AUTH_GITHUB_ID && process.env.AUTH_GITHUB_SECRET,
  );
  const googleConfigured = Boolean(
    process.env.AUTH_GOOGLE_ID && process.env.AUTH_GOOGLE_SECRET,
  );
  const noneConfigured = !ghConfigured && !googleConfigured;

  return (
    <main className="min-h-screen bg-[var(--color-bg)]">
      <div className="mx-auto flex min-h-screen max-w-[1440px] flex-col px-6 py-8 md:px-10 lg:px-20">
        <div>
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-[14px] text-[var(--color-fg-muted)] transition-colors hover:text-[var(--color-fg)]"
          >
            <ArrowLeft className="size-4" aria-hidden="true" />
            Back
          </Link>
        </div>

        <div className="flex flex-1 items-center justify-center py-16">
          <div className="w-full max-w-[440px]">
            <div className="mb-10 text-center">
              <p className="font-mono text-xs uppercase tracking-[0.1em] text-[var(--color-accent)]">
                SIGN IN
              </p>
              <h1 className="mt-4 text-[36px] font-semibold tracking-[-0.03em] text-[var(--color-fg)]">
                Welcome to Xerant.
              </h1>
              <p className="mt-3 text-[15px] leading-[1.55] text-[var(--color-fg-muted)]">
                Free while we&apos;re in beta. No card required.
              </p>
            </div>

            <div className="flex flex-col gap-3">
              {ghConfigured && (
                <form
                  action={async () => {
                    "use server";
                    await signIn("github", { redirectTo: "/" });
                  }}
                >
                  <button
                    type="submit"
                    className="group flex w-full items-center justify-center gap-3 rounded-md border border-[var(--color-border-strong)] bg-[var(--color-fg)] px-6 py-[14px] text-[15px] font-medium text-[var(--color-bg)] transition-colors duration-200 hover:bg-[var(--color-accent)] active:scale-[0.98]"
                  >
                    <IconGithub className="size-[18px]" />
                    <span>Continue with GitHub</span>
                  </button>
                </form>
              )}

              {googleConfigured && (
                <form
                  action={async () => {
                    "use server";
                    await signIn("google", { redirectTo: "/" });
                  }}
                >
                  <button
                    type="submit"
                    className="flex w-full items-center justify-center gap-3 rounded-md border border-[var(--color-border-strong)] bg-transparent px-6 py-[14px] text-[15px] font-medium text-[var(--color-fg)] transition-colors duration-200 hover:border-[var(--color-fg-muted)] hover:bg-[var(--color-surface-1)] active:scale-[0.98]"
                  >
                    <IconGoogle className="size-[18px]" />
                    <span>Continue with Google</span>
                  </button>
                </form>
              )}
            </div>

            {noneConfigured && (
              <div className="mt-8 border border-[var(--color-border)] bg-[var(--color-surface-1)] p-4">
                <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-[var(--color-accent)]">
                  Setup required
                </p>
                <p className="mt-2 text-[13px] leading-[1.6] text-[var(--color-fg-muted)]">
                  Set at least one provider (
                  <code className="font-mono text-[var(--color-fg)]">
                    AUTH_GITHUB_ID
                  </code>
                  {" + "}
                  <code className="font-mono text-[var(--color-fg)]">
                    AUTH_GITHUB_SECRET
                  </code>
                  {" or "}
                  <code className="font-mono text-[var(--color-fg)]">
                    AUTH_GOOGLE_ID
                  </code>
                  {" + "}
                  <code className="font-mono text-[var(--color-fg)]">
                    AUTH_GOOGLE_SECRET
                  </code>
                  ) plus{" "}
                  <code className="font-mono text-[var(--color-fg)]">
                    AUTH_SECRET
                  </code>{" "}
                  in{" "}
                  <code className="font-mono text-[var(--color-fg)]">
                    .env.local
                  </code>{" "}
                  to enable sign-in.
                </p>
              </div>
            )}

            <p className="mt-10 text-center text-[12px] text-[var(--color-fg-dim)]">
              By continuing, you agree to the Terms and Privacy policy.
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
