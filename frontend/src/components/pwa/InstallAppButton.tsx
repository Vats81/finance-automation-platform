"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";

// `beforeinstallprompt` is a real, widely-supported (Chrome/Edge/Android)
// event with no standard TS DOM typing — declared by hand here rather than
// pulling in a types package for one event shape.
interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

/**
 * Renders nothing until the browser actually fires `beforeinstallprompt`
 * (Chrome/Edge/Android — never fires on Safari/iOS, which has no
 * equivalent API), so this never shows a dead button on a browser that
 * can't install the app anyway.
 */
export function InstallAppButton({ className }: { className?: string }) {
  const [installEvent, setInstallEvent] = useState<BeforeInstallPromptEvent | null>(null);

  useEffect(() => {
    function handler(event: Event) {
      event.preventDefault();
      setInstallEvent(event as BeforeInstallPromptEvent);
    }
    window.addEventListener("beforeinstallprompt", handler);
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  if (!installEvent) return null;

  async function handleInstall() {
    if (!installEvent) return;
    await installEvent.prompt();
    await installEvent.userChoice;
    setInstallEvent(null);
  }

  return (
    <Button variant="secondary" className={className} onClick={handleInstall}>
      Install App
    </Button>
  );
}
