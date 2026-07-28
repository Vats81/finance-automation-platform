import { apiFetch } from "@/lib/api/client";
import { CreateVendorRequest, PagedVendorsResponse, UpdateVendorRequest, VendorResponse } from "@/types/vendor";

// Hits the SMB product's tenant-scoped /businesses/{businessId}/vendors
// routes (backend/app/vendors/api/business_routes.py) — same VendorResponse
// wire shape as the AP-automation product's vendors.ts, since both share
// the same Vendor aggregate/schema; only the path and auth differ.

export function listBusinessVendors(token: string | null, businessId: string): Promise<PagedVendorsResponse> {
  return apiFetch<PagedVendorsResponse>(`/businesses/${businessId}/vendors`, token);
}

export function getBusinessVendor(
  token: string | null,
  businessId: string,
  vendorId: string
): Promise<VendorResponse> {
  return apiFetch<VendorResponse>(`/businesses/${businessId}/vendors/${vendorId}`, token);
}

export function createBusinessVendor(
  token: string | null,
  businessId: string,
  body: CreateVendorRequest
): Promise<VendorResponse> {
  return apiFetch<VendorResponse>(`/businesses/${businessId}/vendors`, token, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateBusinessVendor(
  token: string | null,
  businessId: string,
  vendorId: string,
  body: UpdateVendorRequest
): Promise<VendorResponse> {
  return apiFetch<VendorResponse>(`/businesses/${businessId}/vendors/${vendorId}`, token, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}
