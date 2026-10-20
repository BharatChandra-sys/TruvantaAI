import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import "./globals.css";
import StructuredData from "@/components/StructuredData";

export const metadata: Metadata = {
  metadataBase: new URL('https://truvantaai.tech'),
  title: {
    default: "TruvantaAI - AI-Powered Fact Verification Extension | Stop Misinformation",
    template: "%s | TruvantaAI"
  },
  description: "TruvantaAI is a powerful browser extension that verifies claims in real-time using advanced AI models. Detect fake news, misinformation, and false claims instantly while browsing. Free fact-checking tool with evidence-based verification.",
  keywords: [
    "fact check",
    "fact checker",
    "truvanta ai",
    "truvantaai",
    "fact checking",
    "ai fact checker",
    "fake news detector",
    "misinformation detector",
    "truth verification",
    "claim verification",
    "browser extension",
    "chrome extension",
    "edge extension",
    "real-time fact checking",
    "ai verification",
    "fake news",
    "disinformation",
    "media literacy",
    "source verification",
    "evidence based",
    "credibility assessment"
  ],
  authors: [{ name: "TruvantaAI Team", url: "https://truvantaai.tech" }],
  creator: "TruvantaAI",
  publisher: "TruvantaAI",
  applicationName: "TruvantaAI",
  category: "productivity",
  classification: "Browser Extension",
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://truvantaai.tech",
    siteName: "TruvantaAI",
    title: "TruvantaAI - AI-Powered Fact Verification Extension",
    description: "Verify claims instantly with our AI-powered browser extension. Stop misinformation before it spreads. Evidence-based fact-checking at your fingertips.",
    images: [
      {
        url: '/truvanta-logo-transparent.png',
        width: 1200,
        height: 630,
        alt: 'TruvantaAI - AI-Powered Fact Verification',
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "TruvantaAI - AI-Powered Fact Verification",
    description: "Verify claims instantly. Stop misinformation. Free AI-powered browser extension.",
    images: ['/truvanta-logo-transparent.png'],
  },
  icons: {
    icon: [
      { url: '/favicon.ico', sizes: 'any' },
      { url: '/icon.svg', type: 'image/svg+xml' },
      { url: '/icon-192.png', sizes: '192x192', type: 'image/png' },
      { url: '/icon-512.png', sizes: '512x512', type: 'image/png' },
    ],
    apple: [
      { url: '/icon-192.png', sizes: '192x192', type: 'image/png' },
    ],
  },
  manifest: '/manifest.json',
  alternates: {
    canonical: 'https://truvantaai.tech',
  },
  other: {
    'google-site-verification': 'google5834a36d31acb362',
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${GeistSans.variable} ${GeistMono.variable}`}>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=5" />
        
        {/* Theme color for mobile browsers */}
        <meta name="theme-color" content="#0a0a0b" media="(prefers-color-scheme: dark)" />
        <meta name="theme-color" content="#0a0a0b" media="(prefers-color-scheme: light)" />
        
        {/* Apple mobile web app */}
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="apple-mobile-web-app-title" content="TruvantaAI" />
        
        {/* Microsoft application */}
        <meta name="msapplication-TileColor" content="#0a0a0b" />
        <meta name="msapplication-config" content="/browserconfig.xml" />
      </head>
      <body className="font-sans min-h-screen bg-canvas text-fg">
        <StructuredData />
        {children}
      </body>
    </html>
  );
}
