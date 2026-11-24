/**
 * A phone number as WhatsApp's wa.me links want it: digits only, with the country code. A bare 10-digit
 * number gets the default country code (91, India), and a leading 0 (as people write local numbers) is
 * dropped. Returns "" when it does not look like a phone number, so the caller can let the user pick the
 * contact in WhatsApp instead.
 */
export function whatsappPhone(raw: string | null | undefined, defaultCountryCode = "91"): string {
  if (!raw) return "";
  const hadPlus = raw.trim().startsWith("+");
  let digits = raw.replace(/\D/g, "");
  if (!hadPlus) {
    digits = digits.replace(/^0+/, "");
    if (digits.length === 10) digits = defaultCountryCode + digits;
  }
  return digits.length >= 11 && digits.length <= 15 ? digits : "";
}

export function whatsappLink(phone: string, text: string): string {
  const base = phone ? `https://wa.me/${phone}` : "https://wa.me/";
  return `${base}?text=${encodeURIComponent(text)}`;
}

export function invoiceMessage(args: {
  customerName?: string | null;
  businessName: string;
  invoiceNumber: string;
  invoiceDate: string;
  total: string;
  balance: string;
  url: string;
}): string {
  const greeting = args.customerName ? `Hello ${args.customerName},` : "Hello,";
  const owing = args.balance !== args.total ? ` Balance due: ${args.balance}.` : "";
  return (
    `${greeting} here is your invoice ${args.invoiceNumber} from ${args.businessName} ` +
    `dated ${args.invoiceDate}. Total: ${args.total}.${owing}\n\nView or download it here: ${args.url}`
  );
}
