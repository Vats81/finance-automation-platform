// GST state and union territory codes (the first two digits of a GSTIN). Mirrors
// backend/app/business/domain/gst.py; the server is what validates.
export const GST_STATES: { code: string; name: string }[] = [
  { code: "01", name: "Jammu and Kashmir" },
  { code: "02", name: "Himachal Pradesh" },
  { code: "03", name: "Punjab" },
  { code: "04", name: "Chandigarh" },
  { code: "05", name: "Uttarakhand" },
  { code: "06", name: "Haryana" },
  { code: "07", name: "Delhi" },
  { code: "08", name: "Rajasthan" },
  { code: "09", name: "Uttar Pradesh" },
  { code: "10", name: "Bihar" },
  { code: "11", name: "Sikkim" },
  { code: "12", name: "Arunachal Pradesh" },
  { code: "13", name: "Nagaland" },
  { code: "14", name: "Manipur" },
  { code: "15", name: "Mizoram" },
  { code: "16", name: "Tripura" },
  { code: "17", name: "Meghalaya" },
  { code: "18", name: "Assam" },
  { code: "19", name: "West Bengal" },
  { code: "20", name: "Jharkhand" },
  { code: "21", name: "Odisha" },
  { code: "22", name: "Chhattisgarh" },
  { code: "23", name: "Madhya Pradesh" },
  { code: "24", name: "Gujarat" },
  { code: "26", name: "Dadra and Nagar Haveli and Daman and Diu" },
  { code: "27", name: "Maharashtra" },
  { code: "29", name: "Karnataka" },
  { code: "30", name: "Goa" },
  { code: "31", name: "Lakshadweep" },
  { code: "32", name: "Kerala" },
  { code: "33", name: "Tamil Nadu" },
  { code: "34", name: "Puducherry" },
  { code: "35", name: "Andaman and Nicobar Islands" },
  { code: "36", name: "Telangana" },
  { code: "37", name: "Andhra Pradesh" },
  { code: "38", name: "Ladakh" },
  { code: "97", name: "Other Territory" },
  { code: "99", name: "Centre Jurisdiction" },
];

const GST_STATE_NAMES_HI: Record<string, string> = {
  "01": "जम्मू और कश्मीर",
  "02": "हिमाचल प्रदेश",
  "03": "पंजाब",
  "04": "चंडीगढ़",
  "05": "उत्तराखंड",
  "06": "हरियाणा",
  "07": "दिल्ली",
  "08": "राजस्थान",
  "09": "उत्तर प्रदेश",
  "10": "बिहार",
  "11": "सिक्किम",
  "12": "अरुणाचल प्रदेश",
  "13": "नागालैंड",
  "14": "मणिपुर",
  "15": "मिज़ोरम",
  "16": "त्रिपुरा",
  "17": "मेघालय",
  "18": "असम",
  "19": "पश्चिम बंगाल",
  "20": "झारखंड",
  "21": "ओडिशा",
  "22": "छत्तीसगढ़",
  "23": "मध्य प्रदेश",
  "24": "गुजरात",
  "26": "दादरा और नगर हवेली तथा दमन और दीव",
  "27": "महाराष्ट्र",
  "29": "कर्नाटक",
  "30": "गोवा",
  "31": "लक्षद्वीप",
  "32": "केरल",
  "33": "तमिलनाडु",
  "34": "पुडुचेरी",
  "35": "अंडमान और निकोबार द्वीप समूह",
  "36": "तेलंगाना",
  "37": "आंध्र प्रदेश",
  "38": "लद्दाख",
  "97": "अन्य क्षेत्र",
  "99": "केंद्र का क्षेत्राधिकार",
};

/** A state's name in the chosen language ("hi" or English). Empty when the code is unknown. */
export function stateName(code: string | null | undefined, lang: "en" | "hi" = "en"): string {
  const state = GST_STATES.find((s) => s.code === code);
  if (!state) return "";
  return lang === "hi" ? (GST_STATE_NAMES_HI[state.code] ?? state.name) : state.name;
}

/** The state a GSTIN belongs to (its first two digits), or "" while it is still being typed. */
export function stateCodeFromGstin(gstin: string): string {
  const code = gstin.trim().slice(0, 2);
  return GST_STATES.some((s) => s.code === code) ? code : "";
}

// ---------------------------------------------------------------------------------------------
// GST rates and the tax preview on the sale form. The server works the real figures out when the
// sale is saved (backend app/sales/domain/entities.py compute_gst); this mirrors it for display.

export const GST_RATES = ["0", "0.25", "3", "5", "12", "18", "28"];

/** "18.00" and "18" are the same rate: the form's rate list uses the plain form. */
export function normalizeRate(rate: string | null | undefined): string {
  if (rate === null || rate === undefined || rate === "") return "";
  const n = Number(rate);
  return Number.isFinite(n) ? String(n) : "";
}

export interface PreviewLine {
  quantity: string;
  unit_price: string;
  gst_rate?: string;
}

export interface GstPreviewGroup {
  rate: number;
  taxableCents: number;
  taxCents: number;
  cgstCents: number;
  sgstCents: number;
  igstCents: number;
}

/** Within one state tax is split into CGST and SGST halves (the odd paisa goes to SGST); between states it is IGST. */
export function splitTaxCents(taxCents: number, interState: boolean): { cgst: number; sgst: number; igst: number } {
  if (interState) return { cgst: 0, sgst: 0, igst: taxCents };
  let cgst = Math.round(taxCents / 2);
  if (cgst * 2 > taxCents) cgst -= 1;
  return { cgst, sgst: taxCents - cgst, igst: 0 };
}

export function previewGst(lines: PreviewLine[], discount: number, interState: boolean) {
  const lineCents = lines.map((l) => Math.round(Number(l.quantity || 0) * Number(l.unit_price || 0) * 100));
  const subtotalCents = lineCents.reduce((a, b) => a + b, 0);
  const discountCents = Math.round(discount * 100);
  const taxableByRate = new Map<number, number>();
  lines.forEach((l, i) => {
    const lineCentsValue = lineCents[i] ?? 0;
    const share = subtotalCents > 0 ? (discountCents * lineCentsValue) / subtotalCents : 0;
    const rate = l.gst_rate ? Number(l.gst_rate) : 0;
    taxableByRate.set(rate, (taxableByRate.get(rate) ?? 0) + lineCentsValue - share);
  });
  const groups: GstPreviewGroup[] = [...taxableByRate.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([rate, taxable]) => {
      const taxableCents = Math.round(taxable);
      const taxCents = Math.round((taxable * rate) / 100);
      const { cgst, sgst, igst } = splitTaxCents(taxCents, interState);
      return { rate, taxableCents, taxCents, cgstCents: cgst, sgstCents: sgst, igstCents: igst };
    });
  const taxCents = groups.reduce((sum, g) => sum + g.taxCents, 0);
  return { subtotalCents, discountCents, groups, taxCents, totalCents: subtotalCents - discountCents + taxCents };
}

/** Whether a sale is between two different states (IGST). Unknown on either side counts as within the state. */
export function isInterState(sellerState: string | null | undefined, placeOfSupply: string | null | undefined): boolean {
  return Boolean(sellerState && placeOfSupply && sellerState !== placeOfSupply);
}
