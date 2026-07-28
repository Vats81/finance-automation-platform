export type ImportDataType = "customers" | "vendors" | "products" | "expenses";

export const IMPORT_DATA_TYPES: { value: ImportDataType; label: string }[] = [
  { value: "customers", label: "Customers" },
  { value: "vendors", label: "Vendors" },
  { value: "products", label: "Products" },
  { value: "expenses", label: "Expenses" },
];

export interface PreviewResponse {
  headers: string[];
  sample_rows: Record<string, string>[];
  canonical_fields: string[];
  required_fields: string[];
  row_count: number;
}

export interface ImportRowErrorResponse {
  row_number: number;
  message: string;
}

export interface ImportSummaryResponse {
  total_rows: number;
  created: number;
  skipped_duplicates: number;
  errors: ImportRowErrorResponse[];
}

export type ColumnMapping = Record<string, string>;
