import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { JsonLd } from "@/components/json-ld";

const SITE_URL = "https://www.xerant.cloud";
const SITE_NAME = "Xerant";
const TITLE = "Xerant — Sandboxed AI DevOps Team · Save 60% with Military-Grade Security";
const DESCRIPTION =
  "Five sandboxed AI agents run your deploy lifecycle: plan, code, security review, ship, observe. gVisor isolation per agent. Ship 60% cheaper than a 3-engineer rotation. Free while in beta.";

const sans = Geist({
  variable: "--font-sans-var",
  subsets: ["latin"],
  display: "swap",
});

const mono = Geist_Mono({
  variable: "--font-mono-var",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: TITLE,
    template: "%s · Xerant",
  },
  description: DESCRIPTION,
  applicationName: SITE_NAME,
  authors: [{ name: "Xerant Labs", url: SITE_URL }],
  creator: "Xerant Labs",
  publisher: "Xerant Labs",
  keywords: [
    "AI DevOps team",
    "sandboxed AI agents",
    "gVisor sandbox",
    "multi-agent DevOps platform",
    "autonomous deployment agents",
    "AI code review",
    "AI security agent",
    "AI deployer",
    "DevOps automation",
    "AI site reliability",
    "Axiom Forge Warden Vector Sentry",
    "alternative to Vercel",
    "alternative to Netlify",
    "self-hosted DevOps AI",
    "military-grade isolation",
    "prompt injection containment",
  ],
  category: "technology",
  alternates: {
    canonical: SITE_URL,
  },
  openGraph: {
    type: "website",
    url: SITE_URL,
    siteName: SITE_NAME,
    title: TITLE,
    description: DESCRIPTION,
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    site: "@xerant_cloud",
    creator: "@xerant_cloud",
    title: TITLE,
    description: DESCRIPTION,
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-snippet": -1,
      "max-image-preview": "large",
      "max-video-preview": -1,
    },
  },
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/favicon.svg", type: "image/svg+xml" },
      { url: "/icon", type: "image/png", sizes: "512x512" },
    ],
    apple: [{ url: "/apple-icon", sizes: "180x180", type: "image/png" }],
  },
  manifest: "/manifest.webmanifest",
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  other: {
    "msapplication-TileColor": "#000000",
  },
};

export const viewport: Viewport = {
  colorScheme: "dark",
  themeColor: "#000000",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${sans.variable} ${mono.variable}`}>
      <body>
        <JsonLd />
        {children}
      </body>
    </html>
  );
}
