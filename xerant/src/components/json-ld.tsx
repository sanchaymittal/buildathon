import { AGENTS } from "@/lib/agents";
import { FAQ } from "@/content/faq";

const SITE_URL = "https://www.xerant.cloud";
const ORG_NAME = "Xerant";
const DESCRIPTION =
  "Five sandboxed AI agents run your deploy lifecycle: plan, code, security review, ship, observe. gVisor isolation per agent. Ship 60% cheaper than a 3-engineer rotation.";

function organizationSchema() {
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    "@id": `${SITE_URL}#organization`,
    name: "Xerant Labs",
    alternateName: "Xerant",
    url: SITE_URL,
    logo: `${SITE_URL}/icon`,
    description: DESCRIPTION,
    foundingDate: "2026",
    sameAs: [
      "https://x.com/xerant_cloud",
      "https://github.com/sanchaymittal/xerant",
      "https://t.me/sanchaymittal",
    ],
    contactPoint: {
      "@type": "ContactPoint",
      email: "hi@xerant.cloud",
      contactType: "customer support",
      availableLanguage: ["English"],
    },
  };
}

function websiteSchema() {
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "@id": `${SITE_URL}#website`,
    url: SITE_URL,
    name: ORG_NAME,
    description: DESCRIPTION,
    publisher: { "@id": `${SITE_URL}#organization` },
    inLanguage: "en-US",
  };
}

function softwareApplicationSchema() {
  return {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    "@id": `${SITE_URL}#software`,
    name: ORG_NAME,
    applicationCategory: "DeveloperApplication",
    applicationSubCategory: "DevOps automation",
    operatingSystem: "Web, Linux, Kubernetes",
    description: DESCRIPTION,
    url: SITE_URL,
    offers: {
      "@type": "Offer",
      price: "0",
      priceCurrency: "USD",
      availability: "https://schema.org/InStock",
      description: "Free while in beta — unlimited deploys, no seat caps.",
    },
    featureList: [
      "Sandboxed agent execution (gVisor isolation per agent)",
      "Multi-agent team: Axiom (orchestrator), Forge (staff engineer), Warden (security), Vector (deployer), Sentry (observer)",
      "GitHub and Linear integrations",
      "Bring-your-own Kubernetes cluster",
      "Role-scoped authority boundaries and mediated handoffs",
      "Audit log export",
    ],
    creator: { "@id": `${SITE_URL}#organization` },
    hasPart: AGENTS.map((a) => ({
      "@type": "SoftwareApplication",
      name: a.name,
      applicationCategory: "DeveloperApplication",
      applicationSubCategory: a.role,
      description: a.blurb,
    })),
  };
}

function faqSchema() {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "@id": `${SITE_URL}#faq`,
    mainEntity: FAQ.map((item) => ({
      "@type": "Question",
      name: item.q,
      acceptedAnswer: {
        "@type": "Answer",
        text: item.a,
      },
    })),
  };
}

function breadcrumbSchema() {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      {
        "@type": "ListItem",
        position: 1,
        name: "Home",
        item: SITE_URL,
      },
      {
        "@type": "ListItem",
        position: 2,
        name: "Pricing",
        item: `${SITE_URL}/#pricing`,
      },
      {
        "@type": "ListItem",
        position: 3,
        name: "Sign in",
        item: `${SITE_URL}/signin`,
      },
    ],
  };
}

export function JsonLd() {
  const graph = {
    "@context": "https://schema.org",
    "@graph": [
      organizationSchema(),
      websiteSchema(),
      softwareApplicationSchema(),
      faqSchema(),
      breadcrumbSchema(),
    ],
  };
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(graph) }}
    />
  );
}
