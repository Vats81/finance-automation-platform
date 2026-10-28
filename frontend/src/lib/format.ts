export type DisplayCurrency = "USD" | "INR";

export const CURRENCY_OPTIONS: { code: DisplayCurrency; label: string }[] = [
  { code: "USD", label: "USD — US dollar ($)" },
  { code: "INR", label: "INR — Indian rupee (₹)" },
];

// Amounts are stored as plain numbers and never converted; the currency is only how they are
// written. CurrentBusinessProvider sets it from the current business, so every screen that
// calls formatCurrency follows that business.
let displayCurrency: DisplayCurrency = "USD";

export function setDisplayCurrency(code: string | null | undefined): void {
  displayCurrency = code === "INR" ? "INR" : "USD";
}

/** An amount in a specific currency, for screens that mix businesses (a firm's client list). */
export function formatMoney(value: string | number, code: string | null | undefined): string {
  const currency: DisplayCurrency = code === "INR" ? "INR" : "USD";
  return Number(value).toLocaleString(currency === "INR" ? "en-IN" : "en-US", { style: "currency", currency });
}

export function formatCurrency(value: string | number): string {
  return formatMoney(value, displayCurrency);
}

/**
 * Rupees for someone in India, dollars for everyone else. It reads the browser's time zone and
 * language, so no location is requested or sent anywhere. Call it in the browser only.
 */
export function detectCurrency(): DisplayCurrency {
  try {
    const zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (zone === "Asia/Kolkata" || zone === "Asia/Calcutta") return "INR";
    if (navigator.language?.toLowerCase().endsWith("-in")) return "INR";
  } catch {
    // fall through to dollars
  }
  return "USD";
}
