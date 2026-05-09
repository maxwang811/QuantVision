import type { Metadata } from "next";
import "./globals.css";
import { TopNav } from "@/components/nav/TopNav";
import { QueryProvider } from "@/components/providers/QueryProvider";

export const metadata: Metadata = {
  title: "QuantVision",
  description: "Portfolio forecasting and strategy simulation platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen font-sans antialiased">
        <QueryProvider>
          <TopNav />
          <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
        </QueryProvider>
      </body>
    </html>
  );
}
