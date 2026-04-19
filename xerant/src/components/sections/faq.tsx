"use client";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Section, SectionHeader } from "@/components/section";
import { FAQ } from "@/content/faq";

export function FaqSection() {
  return (
    <Section id="faq">
      <SectionHeader
        eyebrow="QUESTIONS"
        headline="The details."
      />

      <Accordion className="mx-auto max-w-[880px] border-t border-[var(--color-border)]">
        {FAQ.map((item, i) => (
          <AccordionItem
            key={i}
            value={`item-${i}`}
            className="border-b border-[var(--color-border)]"
          >
            <AccordionTrigger className="py-6 text-left text-[17px] md:text-[19px] font-medium text-[var(--color-fg)] hover:no-underline">
              {item.q}
            </AccordionTrigger>
            <AccordionContent className="pb-6 text-[15px] leading-[1.6] text-[var(--color-fg-muted)]">
              {item.a}
            </AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </Section>
  );
}
