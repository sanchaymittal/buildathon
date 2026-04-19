import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

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
  title: "Xerant · A specialized DevOps team, sandboxed and on-call",
  description:
    "Five specialized agents handle the full deploy lifecycle — plan, code, security review, deploy, observe. Each in its own gVisor sandbox. Ship 60% cheaper than a 3-engineer rotation.",
  metadataBase: new URL("https://xerant.cloud"),
  openGraph: {
    title: "Xerant",
    description: "A specialized DevOps team, sandboxed and on-call.",
    url: "https://xerant.cloud",
    siteName: "Xerant",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Xerant",
    description: "A specialized DevOps team, sandboxed and on-call.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${sans.variable} ${mono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
