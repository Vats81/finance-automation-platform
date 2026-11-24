import type { Metadata, Viewport } from "next";
import { MsalClientProvider } from "@/components/layout/MsalClientProvider";
import { ServiceWorkerRegistration } from "@/components/pwa/ServiceWorkerRegistration";
import { LanguageProvider } from "@/lib/i18n/LanguageProvider";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "Finverlo — Your AI Finance Manager for Business Growth",
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
        <LanguageProvider>
          <MsalClientProvider>{children}</MsalClientProvider>
        </LanguageProvider>
      </body>
    </html>
  );
}
