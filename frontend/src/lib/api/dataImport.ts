import { ApiError } from "@/lib/api/client";
import { ColumnMapping, ImportDataType, ImportSummaryResponse, PreviewResponse } from "@/types/dataImport";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Multipart requests can't go through apiFetch (it hardcodes
// Content-Type: application/json) — same bypass used by uploadW9Document
// in lib/api/vendors.ts.
async function multipartFetch<T>(path: string, token: string | null, formData: FormData): Promise<T> {
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_BASE_URL}/api/v1${path}`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!response.ok) {
    const problem = await response.json().catch(() => null);
    throw new ApiError(
      problem?.detail ?? response.statusText,
      response.status,
      problem?.error_code ?? "unknown_error",
      problem?.details
    );
  }
  return (await response.json()) as T;
}

export function previewImport(
  token: string | null,
  businessId: string,
  dataType: ImportDataType,
  file: File
): Promise<PreviewResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return multipartFetch<PreviewResponse>(
    `/businesses/${businessId}/imports/${dataType}/preview`,
    token,
    formData
  );
}

export function runImport(
  token: string | null,
  businessId: string,
  dataType: ImportDataType,
  file: File,
  columnMapping: ColumnMapping
): Promise<ImportSummaryResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("column_mapping", JSON.stringify(columnMapping));
  return multipartFetch<ImportSummaryResponse>(
    `/businesses/${businessId}/imports/${dataType}`,
    token,
    formData
  );
}

export async function downloadImportTemplate(
  token: string | null,
  businessId: string,
  dataType: ImportDataType
): Promise<void> {
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(
    `${API_BASE_URL}/api/v1/businesses/${businessId}/imports/${dataType}/template`,
    { headers }
  );
  if (!response.ok) {
    throw new ApiError(response.statusText, response.status, "unknown_error");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${dataType}_template.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
