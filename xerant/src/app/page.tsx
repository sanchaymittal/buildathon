import { Nav } from "@/components/nav";
import { Footer } from "@/components/footer";
import { Hero } from "@/components/sections/hero";
import { TeamSection } from "@/components/sections/team";
import { SandboxSection } from "@/components/sections/sandbox";
import { IntegrationSection } from "@/components/sections/integration";
import { CompareSection } from "@/components/sections/compare";
import { PricingSection } from "@/components/sections/pricing";
import { FaqSection } from "@/components/sections/faq";

export default function Home() {
  return (
    <>
      <Nav />
      <main className="pt-16">
        <Hero />
        <TeamSection />
        <SandboxSection />
        <IntegrationSection />
        <CompareSection />
        <PricingSection />
        <FaqSection />
      </main>
      <Footer />
    </>
  );
}
