import { Section, SectionHeader, FadeIn } from "@/components/section";
import { CtaButton } from "@/components/cta-button";
import { Check } from "lucide-react";

const FEATURES = [
  "Unlimited deploys",
  "Dedicated gVisor sandboxes per agent",
  "GitHub + Linear integrations",
  "Bring your own cluster",
  "Slack + email support",
  "Audit log export",
];

export function PricingSection() {
  return (
    <Section id="pricing">
      <div className="flex flex-col items-center text-center">
        <SectionHeader
          centered
          eyebrow="PRICING"
          headline="Free while we're in beta."
          subhead="No seats. No deploy caps. Sign in with GitHub or Google and start shipping."
        />

        <FadeIn className="w-full max-w-[520px]">
          <div className="relative border border-[var(--color-border)] bg-[var(--color-surface-1)] p-10 md:p-12 text-left">
            <div className="flex items-center justify-between">
              <p className="font-mono text-xs uppercase tracking-[0.1em] text-[var(--color-accent)]">
                FREE
              </p>
              <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-[var(--color-fg-dim)]">
                Beta
              </span>
            </div>

            <h3 className="mt-8 text-[32px] font-semibold tracking-[-0.025em] text-[var(--color-fg)]">
              Everything, $0
            </h3>
            <p className="mt-3 text-[15px] leading-[1.55] text-[var(--color-fg-muted)]">
              Five agents. Unlimited seats. Nothing to pay while the beta is
              open.
            </p>

            <div className="my-10 h-px w-full bg-[var(--color-border)]" />

            <ul className="space-y-4">
              {FEATURES.map((f) => (
                <li
                  key={f}
                  className="flex items-start gap-3 text-[15px] text-[var(--color-fg)]"
                >
                  <Check
                    className="mt-[3px] size-4 shrink-0 text-[var(--color-accent)]"
                    strokeWidth={2}
                    aria-hidden="true"
                  />
                  <span>{f}</span>
                </li>
              ))}
            </ul>

            <div className="mt-10 flex flex-col gap-3">
              <CtaButton variant="primary" href="/signin" className="w-full">
                Sign in with GitHub
              </CtaButton>
              <CtaButton variant="ghost" href="/signin" className="w-full">
                Sign in with Google
              </CtaButton>
            </div>

            <p className="mt-6 text-center text-[12px] text-[var(--color-fg-dim)]">
              No credit card. Cancel anytime, because there&apos;s nothing to
              cancel.
            </p>
          </div>
        </FadeIn>
      </div>
    </Section>
  );
}
