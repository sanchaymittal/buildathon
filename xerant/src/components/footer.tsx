import Link from "next/link";
import { Mail } from "lucide-react";

const CONTACT_EMAIL = "hi@xerant.cloud";
const TWITTER_URL = "https://x.com/xerant_cloud";
const TWITTER_HANDLE = "@xerant_cloud";
const TELEGRAM_URL = "https://t.me/sanchaymittal";
const TELEGRAM_HANDLE = "@sanchaymittal";

function IconX({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className}
      aria-hidden="true"
    >
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
    </svg>
  );
}

function IconTelegram({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className}
      aria-hidden="true"
    >
      <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.5.5 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z" />
    </svg>
  );
}

const COLS = [
  {
    label: "Product",
    links: [
      { label: "Team", href: "#team" },
      { label: "Compare", href: "#compare" },
      { label: "Pricing", href: "#pricing" },
      { label: "FAQ", href: "#faq" },
    ],
  },
  {
    label: "Contact",
    links: [
      { label: "Email", href: `mailto:${CONTACT_EMAIL}` },
      { label: TWITTER_HANDLE, href: TWITTER_URL, external: true },
      { label: `Telegram ${TELEGRAM_HANDLE}`, href: TELEGRAM_URL, external: true },
    ],
  },
] as const;

export function Footer() {
  return (
    <footer className="border-t border-[var(--color-border)]">
      <div className="mx-auto max-w-[1440px] px-6 pt-20 pb-10 md:px-10 lg:px-20">
        <div className="grid gap-12 md:grid-cols-[1fr_auto] md:gap-16">
          <div className="max-w-sm">
            <Link
              href="/"
              className="text-[18px] font-medium tracking-[-0.02em] text-[var(--color-fg)]"
            >
              XERANT
            </Link>
            <p className="mt-4 text-[15px] leading-[1.55] text-[var(--color-fg-muted)]">
              A specialized DevOps team. Sandboxed and on-call.
            </p>
            <p className="mt-6 text-[14px] text-[var(--color-fg-muted)]">
              Questions?{" "}
              <a
                href={`mailto:${CONTACT_EMAIL}`}
                className="text-[var(--color-fg)] underline decoration-[var(--color-border-strong)] underline-offset-4 transition-colors hover:decoration-[var(--color-accent)]"
              >
                {CONTACT_EMAIL}
              </a>
            </p>
          </div>

          <div className="grid grid-cols-3 gap-10 md:gap-16">
            {COLS.map((col) => (
              <div key={col.label}>
                <p className="font-mono text-xs uppercase tracking-[0.08em] text-[var(--color-fg-dim)]">
                  {col.label}
                </p>
                <ul className="mt-5 space-y-3">
                  {col.links.map((l) => {
                    const external =
                      "external" in l && l.external === true;
                    return (
                      <li key={l.label}>
                        <Link
                          href={l.href}
                          {...(external && {
                            target: "_blank",
                            rel: "noopener noreferrer",
                          })}
                          className="text-[15px] text-[var(--color-fg-muted)] transition-colors duration-200 hover:text-[var(--color-fg)]"
                        >
                          {l.label}
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-20 flex items-center justify-between border-t border-[var(--color-border)] pt-8">
          <p className="text-[13px] text-[var(--color-fg-dim)]">
            © 2026 Xerant Labs
          </p>
          <div className="flex items-center gap-5">
            <a
              href={`mailto:${CONTACT_EMAIL}`}
              aria-label={`Email Xerant at ${CONTACT_EMAIL}`}
              className="text-[var(--color-fg-muted)] transition-colors hover:text-[var(--color-fg)]"
            >
              <Mail className="size-4" strokeWidth={1.75} aria-hidden="true" />
            </a>
            <a
              href={TWITTER_URL}
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Xerant on X"
              className="text-[var(--color-fg-muted)] transition-colors hover:text-[var(--color-fg)]"
            >
              <IconX className="size-4" />
            </a>
            <a
              href={TELEGRAM_URL}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={`Xerant on Telegram · ${TELEGRAM_HANDLE}`}
              className="text-[var(--color-fg-muted)] transition-colors hover:text-[var(--color-fg)]"
            >
              <IconTelegram className="size-4" />
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
