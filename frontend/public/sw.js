// Minimal service worker — exists purely to satisfy the browser's PWA
// installability criteria (a manifest + a registered service worker +
// HTTPS) alongside manifest.webmanifest. Deliberately no offline caching
// strategy: this is an "install as an app shortcut" feature, not an
// offline-first rebuild of the app.
self.addEventListener("fetch", () => {
  // Pass-through — let every request go to the network as normal.
});
