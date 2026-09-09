import type { Metadata, Viewport } from "next";
import { MsalClientProvider } from "@/components/layout/MsalClientProvider";
import { ServiceWorkerRegistration } from "@/components/pwa/ServiceWorkerRegistration";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "FinanceAI — Your AI Finance Manager for Business Growth",
  description: "AI-powered finance and business management for small and medium businesses",
  manifest: "/manifest.webmanifest",
};

export const viewport: Viewport = {
  themeColor: "#264dc0",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <ServiceWorkerRegistration />
        <MsalClientProvider>{children}</MsalClientProvider>
      </body>
    </html>
  );
}
