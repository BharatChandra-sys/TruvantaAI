import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import "./globals.css";
import StructuredData from "@/components/StructuredData";

export const metadata: Metadata = {
  metadataBase: new URL('https://truvantaai.tech'),
  title: {
    default: "Truvanta AI - Real-Time Fact Checker Extension | Stop Fake News & Misinformation",
    template: "%s | Truvanta AI"
  },
  description: "Truvanta AI verifies claims instantly using advanced machine learning and real-time evidence retrieval. Detect fake news, misinformation, and false claims with AI-powered fact-checking. Free browser extension for Chrome, Edge & Brave with source-grounded verdicts.",
  keywords: [
    // Core product terms
    "fact check",
    "fact checker",
    "truvanta ai",
    "truvantaai",
    "fact checking extension",
    "ai fact checker",
    "real-time fact checking",
    
    // Problem & solution
    "fake news detector",
    "misinformation detector",
    "disinformation detection",
    "false claim detector",
    "truth verification",
    "claim verification",
    "verify news",
    "stop fake news",
    
    // Technology terms
    "ai verification",
    "machine learning fact check",
    "nlp fact checking",
    "automated fact checking",
    "source grounded verification",
    "evidence based fact checking",
    "rag fact checker",
    "hybrid retrieval",
    
    // Browser & platform
    "browser extension",
    "chrome extension fact check",
    "edge extension",
    "brave browser extension",
    "chromium extension",
    
    // Use cases & domains
    "media literacy",
    "news verification",
    "social media fact check",
    "health misinformation",
    "political fact check",
    "scientific claim verification",
    "covid fact check",
    "climate fact check",
    
    // Features
    "source verification",
    "credibility assessment",
    "citation validation",
    "evidence retrieval",
    "confidence scoring",
    "transparency fact checking",
    
    // Geographic relevance
    "fact checker india",
    "fact check tool usa",
    "global fact checking",
    "multilingual fact check",
    "international news verification",
    
    // Competition & alternatives
    "snopes alternative",
    "politifact extension",
    "factcheck.org alternative",
    "open source fact checker",
    "free fact checking tool"
  ],
  authors: [{ name: "Truvanta AI Team", url: "https://truvantaai.tech" }],
  creator: "Truvanta AI",
  publisher: "Truvanta AI",
  applicationName: "Truvanta AI",
  category: "productivity",
  classification: "Browser Extension - AI Fact Verification",
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
    siteName: "Truvanta AI",
    title: "Truvanta AI - Real-Time Fact Checker with Source-Grounded AI",
    description: "Verify claims instantly with AI-powered fact-checking. Stop misinformation before it spreads. Free browser extension with evidence-based verdicts you can trust.",
    images: [
      {
        url: '/truvanta-logo-transparent.png',
        width: 1200,
        height: 630,
        alt: 'Truvanta AI - AI-Powered Real-Time Fact Verification Extension',
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Truvanta AI - Stop Fake News with AI Fact-Checking",
    description: "Verify claims instantly. Stop misinformation. Free AI-powered browser extension with transparent, source-grounded verdicts.",
    images: ['/truvanta-logo-transparent.png'],
    creator: "@truvantaai",
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
    languages: {
      'en-US': 'https://truvantaai.tech',
      'en-GB': 'https://truvantaai.tech',
      'en-IN': 'https://truvantaai.tech',
    },
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
