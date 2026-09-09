"use client";

import { useEffect } from "react";

/**
 * Registers public/sw.js — required (alongside the manifest) for the
 * browser to consider this app installable. Renders nothing; mounted once
 * in the root layout.
 */
export function ServiceWorkerRegistration() {
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => {
        // Installability is a progressive enhancement — nothing to show
        // the user if this fails (e.g. unsupported browser).
      });
    }
  }, []);

  return null;
}
