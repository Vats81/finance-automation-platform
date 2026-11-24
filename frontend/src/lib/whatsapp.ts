import { MessageKey } from "@/lib/i18n/messages";

type T = (key: MessageKey, vars?: Record<string, string | number>) => string;

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

/** The message that goes with an invoice link, in the language of the person sending it. */
export function invoiceMessage(
  t: T,
  args: {
    customerName?: string | null;
    businessName: string;
    invoiceNumber: string;
    invoiceDate: string;
    total: string;
    balance: string;
    url: string;
  }
): string {
  const greeting = args.customerName ? t("wa.hello", { name: args.customerName }) : t("wa.helloPlain");
  const body = t("wa.invoiceBody", {
    number: args.invoiceNumber,
    business: args.businessName,
    date: args.invoiceDate,
    total: args.total,
  });
  const owing = args.balance !== args.total ? ` ${t("wa.balance", { balance: args.balance })}` : "";
  return `${greeting} ${body}${owing}\n\n${t("wa.viewLink", { url: args.url })}`;
}

/** A polite payment reminder for what a customer owes (the udhaar list). */
export function reminderMessage(
  t: T,
  args: {
    customerName: string;
    businessName: string;
    amount: string;
    invoiceNumbers: string[];
    upiId?: string | null;
  }
): string {
  const shown = args.invoiceNumbers.slice(0, 3).join(", ");
  const invoices =
    args.invoiceNumbers.length > 3 ? t("wa.reminderMore", { shown, n: args.invoiceNumbers.length - 3 }) : shown;
  const body = t("wa.reminderBody", { business: args.businessName, amount: args.amount, invoices });
  const pay = args.upiId ? ` ${t("wa.reminderUpi", { upi: args.upiId })}` : "";
  return `${t("wa.hello", { name: args.customerName })} ${body}${pay} ${t("wa.reminderThanks")}`;
}
