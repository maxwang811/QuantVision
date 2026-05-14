import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { TopNav } from "@/components/nav/TopNav";
import { QueryProvider } from "@/components/providers/QueryProvider";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "QuantVision",
  description: "Portfolio forecasting and strategy simulation platform",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#fafaf9" },
    { media: "(prefers-color-scheme: dark)", color: "#0a0a0a" },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable} bg-bg`}>
      <body className="min-h-screen bg-bg font-sans text-fg antialiased">
        <QueryProvider>
          <div className="flex min-h-screen flex-col">
            <TopNav />
            <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6 lg:px-8 lg:py-12">
              {children}
            </main>
            <footer className="mt-auto border-t border-border bg-surface/50">
              <div className="mx-auto flex w-full max-w-7xl flex-col items-start justify-between gap-3 px-4 py-6 text-xs text-muted sm:flex-row sm:items-center sm:px-6 lg:px-8">
                <span>
                  QuantVision · Portfolio forecasting & strategy simulation
                </span>
                <span className="font-mono text-muted/70">Built with Next.js + FastAPI</span>
              </div>
            </footer>
          </div>
        </QueryProvider>
      </body>
    </html>
  );
}
