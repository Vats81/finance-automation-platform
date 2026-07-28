import type { Metadata } from "next";
import { MsalClientProvider } from "@/components/layout/MsalClientProvider";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "FinanceAI — Your AI Finance Manager for Business Growth",
  description: "AI-powered finance and business management for small and medium businesses",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <MsalClientProvider>{children}</MsalClientProvider>
      </body>
    </html>
  );
}
