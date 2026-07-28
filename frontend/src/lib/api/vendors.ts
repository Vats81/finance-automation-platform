import { apiFetch } from "@/lib/api/client";
import { CreateVendorRequest, PagedVendorsResponse, VendorResponse } from "@/types/vendor";

export function listVendors(token: string | null): Promise<PagedVendorsResponse> {
  return apiFetch<PagedVendorsResponse>("/vendors", token);
}

export function getVendor(token: string | null, vendorId: string): Promise<VendorResponse> {
  return apiFetch<VendorResponse>(`/vendors/${vendorId}`, token);
}

export function createVendor(token: string | null, body: CreateVendorRequest): Promise<VendorResponse> {
  return apiFetch<VendorResponse>("/vendors", token, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function activateVendor(token: string | null, vendorId: string): Promise<VendorResponse> {
  return apiFetch<VendorResponse>(`/vendors/${vendorId}/activate`, token, { method: "POST" });
}

export async function uploadW9Document(
  token: string | null,
  vendorId: string,
  file: File
): Promise<VendorResponse> {
  const formData = new FormData();
  formData.append("file", file);
  // apiFetch always sets Content-Type: application/json, which is wrong for
  // multipart uploads — the browser needs to set its own boundary — so this
  // call bypasses it and constructs the request directly.
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_BASE_URL}/api/v1/vendors/${vendorId}/w9-document`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!response.ok) {
    const problem = await response.json().catch(() => null);
    throw new Error(problem?.detail ?? response.statusText);
  }
  return (await response.json()) as VendorResponse;
}
