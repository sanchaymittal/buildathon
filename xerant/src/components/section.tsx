import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export { FadeIn } from "@/components/fade-in";

export function Section({
  id,
  children,
  className,
  topBorder = true,
}: {
  id?: string;
  children: ReactNode;
  className?: string;
  topBorder?: boolean;
}) {
  return (
    <section
      id={id}
      className={cn(
        topBorder && "border-t border-[var(--color-border)]",
        className,
      )}
    >
      <div className="mx-auto max-w-[1440px] px-6 py-24 md:px-10 md:py-32 lg:px-20 lg:py-40">
        {children}
      </div>
    </section>
  );
}

export function SectionHeader({
  eyebrow,
  headline,
  subhead,
  centered = false,
  className,
}: {
  eyebrow: string;
  headline: string;
  subhead?: string;
  centered?: boolean;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "mb-16 md:mb-20",
        centered && "flex flex-col items-center text-center",
        className,
      )}
    >
      <p className="font-mono text-xs uppercase tracking-[0.08em] text-[var(--color-fg-dim)] mb-6">
        {eyebrow}
      </p>
      <h2 className="text-[44px] leading-[1.04] tracking-[-0.035em] font-semibold max-w-[18ch] md:text-[56px] md:leading-[1.03] md:tracking-[-0.04em] lg:text-[72px] lg:leading-[1.02]">
        {headline}
      </h2>
      {subhead && (
        <p className="mt-8 text-[17px] leading-[1.55] text-[var(--color-fg-muted)] max-w-[640px]">
          {subhead}
        </p>
      )}
    </div>
  );
}
