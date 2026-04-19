import Link from "next/link";
import { cn } from "@/lib/utils";
import type { ComponentPropsWithoutRef, ReactNode } from "react";

type Variant = "primary" | "ghost";

type Props = {
  variant?: Variant;
  href?: string;
  children: ReactNode;
  className?: string;
} & Omit<ComponentPropsWithoutRef<"a">, "href" | "className">;

const base =
  "inline-flex items-center justify-center gap-2 rounded-md px-6 py-[14px] text-[15px] font-medium tracking-[-0.005em] transition-colors duration-200 active:scale-[0.98] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[var(--color-accent)]";

const variants: Record<Variant, string> = {
  primary:
    "bg-[var(--color-fg)] text-[var(--color-bg)] hover:bg-[var(--color-accent)]",
  ghost:
    "bg-transparent text-[var(--color-fg)] border border-[var(--color-border-strong)] hover:border-[var(--color-fg-muted)] hover:bg-[var(--color-surface-1)]",
};

export function CtaButton({
  variant = "primary",
  href = "#pricing",
  children,
  className,
  ...rest
}: Props) {
  return (
    <Link href={href} className={cn(base, variants[variant], className)} {...rest}>
      {children}
    </Link>
  );
}
