"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Menu, X } from "lucide-react";
import { CtaButton } from "./cta-button";

const LINKS = [
  { label: "Team", href: "#team" },
  { label: "Compare", href: "#compare" },
  { label: "Pricing", href: "#pricing" },
];

export function Nav() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <>
      <nav
        className="fixed top-0 inset-x-0 z-50 h-16 border-b border-[var(--color-border)] bg-[color-mix(in_srgb,var(--color-bg)_70%,transparent)] backdrop-blur-md"
        aria-label="Primary"
      >
        <div className="mx-auto flex h-full max-w-[1440px] items-center justify-between px-6 md:px-10 lg:px-20">
          <Link
            href="/"
            className="text-[18px] font-medium tracking-[-0.02em] text-[var(--color-fg)]"
            aria-label="Xerant home"
          >
            XERANT
          </Link>

          <div className="hidden items-center gap-10 md:flex">
            <ul className="flex items-center gap-8">
              {LINKS.map((l) => (
                <li key={l.href}>
                  <Link
                    href={l.href}
                    className="text-[15px] text-[var(--color-fg-muted)] transition-colors duration-200 hover:text-[var(--color-fg)]"
                  >
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
            <CtaButton variant="primary" href="/signin" className="px-5 py-2.5 text-[14px]">
              Sign in
            </CtaButton>
          </div>

          <button
            type="button"
            onClick={() => setOpen(true)}
            className="md:hidden p-2 -mr-2 text-[var(--color-fg)]"
            aria-label="Open menu"
            aria-expanded={open}
            aria-controls="mobile-menu"
          >
            <Menu className="size-5" />
          </button>
        </div>
      </nav>

      {open && (
        <div
          id="mobile-menu"
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-[60] flex flex-col bg-[var(--color-bg)]"
        >
          <div className="flex h-16 items-center justify-between border-b border-[var(--color-border)] px-6">
            <Link
              href="/"
              onClick={() => setOpen(false)}
              className="text-[18px] font-medium tracking-[-0.02em]"
            >
              XERANT
            </Link>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="p-2 -mr-2"
              aria-label="Close menu"
            >
              <X className="size-5" />
            </button>
          </div>
          <ul className="flex flex-1 flex-col gap-10 px-6 pt-16">
            {LINKS.map((l) => (
              <li key={l.href}>
                <Link
                  href={l.href}
                  onClick={() => setOpen(false)}
                  className="text-[48px] font-semibold tracking-[-0.035em] leading-[1.02]"
                >
                  {l.label}
                </Link>
              </li>
            ))}
          </ul>
          <div className="px-6 pb-10">
            <CtaButton
              variant="primary"
              href="/signin"
              onClick={() => setOpen(false)}
              className="w-full"
            >
              Sign in
            </CtaButton>
          </div>
        </div>
      )}
    </>
  );
}
