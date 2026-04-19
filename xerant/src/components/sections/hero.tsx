"use client";

import { useEffect, useRef } from "react";
import gsap from "gsap";
import { AGENTS } from "@/lib/agents";
import { CtaButton } from "@/components/cta-button";

const COLOR = {
  bg: "#000000",
  fg: "#F5F5F5",
  fgDim: "#5A5A5E",
  borderStrong: "#2A2A2E",
  accent: "#FFB800",
} as const;

const ALL_LINES = AGENTS.flatMap((a) => a.stage.lines);
const AGENT_NAMES = AGENTS.map((a) => a.name);
const LONGEST_AGENT = AGENT_NAMES.reduce(
  (a, b) => (b.length > a.length ? b : a),
  "",
);

export function Hero() {
  const rootRef = useRef<HTMLElement | null>(null);
  const nodeRefs = useRef<(HTMLDivElement | null)[]>([]);
  const labelRefs = useRef<(HTMLSpanElement | null)[]>([]);
  const connectorRefs = useRef<(HTMLDivElement | null)[]>([]);
  const lineRefs = useRef<(HTMLParagraphElement | null)[]>([]);
  const rotatorRef = useRef<HTMLSpanElement | null>(null);

  useEffect(() => {
    if (!rootRef.current) return;

    const mm = gsap.matchMedia();

    mm.add(
      "(min-width: 768px) and (prefers-reduced-motion: no-preference)",
      async () => {
        const [{ ScrollTrigger }, { TextPlugin }] = await Promise.all([
          import("gsap/ScrollTrigger"),
          import("gsap/TextPlugin"),
        ]);
        gsap.registerPlugin(ScrollTrigger, TextPlugin);

        const nodes = nodeRefs.current.filter(Boolean) as HTMLDivElement[];
        const labels = labelRefs.current.filter(Boolean) as HTMLSpanElement[];
        const connectors = connectorRefs.current.filter(
          Boolean,
        ) as HTMLDivElement[];
        const lines = lineRefs.current.filter(
          Boolean,
        ) as HTMLParagraphElement[];

        if (
          nodes.length !== AGENTS.length ||
          connectors.length !== AGENTS.length - 1 ||
          lines.length !== ALL_LINES.length
        ) {
          return;
        }

        gsap.set(nodes, {
          backgroundColor: "transparent",
          borderColor: COLOR.borderStrong,
          scale: 1,
        });
        gsap.set(nodes[0], {
          backgroundColor: COLOR.accent,
          borderColor: COLOR.accent,
          scale: 1.15,
        });
        gsap.set(labels, { color: COLOR.fgDim });
        gsap.set(labels[0], { color: COLOR.accent });
        gsap.set(connectors, {
          scaleX: 0,
          transformOrigin: "left center",
        });
        gsap.set(lines, { text: "" });

        const tl = gsap.timeline({
          scrollTrigger: {
            trigger: rootRef.current!,
            start: "top top",
            end: "+=220%",
            pin: true,
            pinSpacing: true,
            scrub: 0.6,
            anticipatePin: 1,
            invalidateOnRefresh: true,
          },
        });

        for (let i = 0; i < AGENTS.length; i++) {
          for (let j = 0; j < 3; j++) {
            const idx = i * 3 + j;
            tl.to(
              lines[idx],
              {
                text: { value: ALL_LINES[idx], delimiter: "" },
                duration: 0.18,
                ease: "none",
              },
              ">",
            );
          }

          if (i < AGENTS.length - 1) {
            const nextI = i + 1;
            const label = `transition-${i}`;
            tl.addLabel(label);
            tl.to(
              nodes[i],
              {
                backgroundColor: "transparent",
                borderColor: COLOR.fg,
                scale: 1,
                duration: 0.2,
                ease: "power1.inOut",
              },
              label,
            );
            tl.to(
              labels[i],
              { color: COLOR.fg, duration: 0.2, ease: "power1.inOut" },
              label,
            );
            tl.to(
              connectors[i],
              {
                scaleX: 1,
                duration: 0.25,
                ease: "power1.inOut",
              },
              label,
            );
            tl.to(
              nodes[nextI],
              {
                backgroundColor: COLOR.accent,
                borderColor: COLOR.accent,
                scale: 1.15,
                duration: 0.2,
                ease: "power1.inOut",
              },
              `${label}+=0.1`,
            );
            tl.to(
              labels[nextI],
              { color: COLOR.accent, duration: 0.2, ease: "power1.inOut" },
              `${label}+=0.1`,
            );
          } else {
            tl.to(
              nodes[i],
              {
                backgroundColor: "transparent",
                borderColor: COLOR.fg,
                scale: 1,
                duration: 0.2,
                ease: "power1.inOut",
              },
              ">",
            );
            tl.to(
              labels[i],
              { color: COLOR.fg, duration: 0.2, ease: "power1.inOut" },
              "<",
            );
          }
        }

        if (typeof document !== "undefined" && document.fonts?.ready) {
          document.fonts.ready.then(() => ScrollTrigger.refresh());
        }

        return () => {
          tl.scrollTrigger?.kill();
          tl.kill();
        };
      },
    );

    return () => mm.revert();
  }, []);

  useEffect(() => {
    const el = rotatorRef.current;
    if (!el) return;
    const reduced =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduced) {
      el.textContent = AGENT_NAMES[0];
      return;
    }

    const ctx = gsap.context(() => {
      const tl = gsap.timeline({ repeat: -1 });
      AGENT_NAMES.forEach((name) => {
        tl.to(el, {
          duration: 0.3,
          opacity: 0,
          y: -6,
          ease: "power2.in",
          onComplete: () => {
            el.textContent = name;
          },
        });
        tl.to(el, {
          duration: 0.35,
          opacity: 1,
          y: 0,
          ease: "power2.out",
        });
        tl.to(el, { duration: 1.1, opacity: 1 });
      });
    }, el);

    return () => ctx.revert();
  }, []);

  return (
    <section
      ref={rootRef}
      className="relative border-b border-[var(--color-border)] md:h-screen md:overflow-hidden"
      aria-label="Deploy lifecycle simulation"
    >
      <div className="mx-auto flex h-full max-w-[1440px] flex-col justify-between gap-12 px-6 pt-20 pb-16 md:gap-8 md:px-10 md:pt-24 md:pb-10 lg:px-20 lg:pt-28 lg:pb-14">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.08em] text-[var(--color-fg-dim)]">
            DEPLOY LIFECYCLE / LIVE SIMULATION
          </p>
          <h1 className="mt-5 text-[clamp(2.5rem,min(7.5vw,8vh),6rem)] leading-[1.02] tracking-[-0.045em] font-semibold text-[var(--color-fg)]">
            Save 60% on hosting and
            <br />
            military-grade security.
          </h1>
          <p className="mt-6 max-w-[720px] text-[18px] leading-[1.45] text-[var(--color-fg-muted)] md:text-[22px]">
            And your{" "}
            <span className="relative inline-block align-baseline">
              <span
                aria-hidden="true"
                className="invisible font-semibold tracking-[-0.01em] text-[var(--color-accent)]"
              >
                {LONGEST_AGENT}
              </span>
              <span
                ref={rotatorRef}
                className="absolute inset-0 font-semibold tracking-[-0.01em] text-[var(--color-accent)]"
                aria-hidden="true"
              >
                {AGENT_NAMES[0]}
              </span>
              <span className="sr-only">five-agent</span>
            </span>{" "}
            DevOps team. Sandboxed. On-call. Yours.
          </p>
          <div className="mt-7 flex flex-wrap items-center gap-3 md:gap-4">
            <CtaButton variant="primary" href="/signin">
              Sign in
            </CtaButton>
            <CtaButton variant="ghost" href="#team">
              See the team →
            </CtaButton>
          </div>
        </div>

        <div className="border-t border-[var(--color-border)] pt-8 md:pt-10">
          <div className="flex flex-col gap-0 md:flex-row md:items-center md:gap-4">
            {AGENTS.map((a, i) => (
              <div
                key={a.name}
                className="flex flex-col gap-0 md:flex-1 md:flex-row md:items-center md:gap-4"
              >
                <div className="flex flex-row items-center gap-4 md:flex-col md:gap-0">
                  <div
                    ref={(el) => {
                      nodeRefs.current[i] = el;
                    }}
                    className="size-3.5 shrink-0 rounded-full border-2 md:size-4"
                    style={{
                      borderColor: COLOR.fg,
                      backgroundColor: "transparent",
                    }}
                    aria-hidden="true"
                  />
                  <span
                    ref={(el) => {
                      labelRefs.current[i] = el;
                    }}
                    className="font-mono text-[11px] uppercase tracking-[0.12em] md:mt-3"
                    style={{ color: COLOR.fg }}
                  >
                    {a.name}
                  </span>
                </div>
                {i < AGENTS.length - 1 && (
                  <div
                    className="relative ml-[7px] my-2 h-6 w-px bg-[var(--color-border-strong)] md:ml-0 md:my-0 md:h-px md:w-auto md:flex-1"
                    aria-hidden="true"
                  >
                    <div
                      ref={(el) => {
                        connectorRefs.current[i] = el;
                      }}
                      className="absolute inset-0 bg-[var(--color-accent)]"
                    />
                  </div>
                )}
              </div>
            ))}
          </div>

          <div
            className="mt-8 border border-[var(--color-border)] bg-[var(--color-surface-1)] p-5 font-mono text-[12px] leading-[1.7] text-[var(--color-fg-muted)] md:mt-8 md:p-6 md:text-[13px]"
            aria-hidden="true"
          >
            {ALL_LINES.map((line, i) => (
              <p
                key={i}
                ref={(el) => {
                  lineRefs.current[i] = el;
                }}
                className="min-h-[1.7em]"
              >
                {line}
              </p>
            ))}
          </div>
        </div>
      </div>

      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 bottom-0 h-48 bg-[radial-gradient(60%_120%_at_50%_100%,rgba(255,184,0,0.04),transparent_60%)]"
      />
    </section>
  );
}
