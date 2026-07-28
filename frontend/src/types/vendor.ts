export type VendorStatus = "pending_review" | "active" | "inactive";

export interface Address {
  street: string;
  city: string;
  state: string;
  postal_code: string;
  country: string;
}

export interface VendorResponse {
  id: string;
  legal_name: string;
  contact_email: string;
  tax_id_masked: string;
  address: Address;
  status: VendorStatus;
  has_w9_on_file: boolean;
  created_at: string;
}

export interface PagedVendorsResponse {
  items: VendorResponse[];
  total: number;
  offset: number;
  limit: number;
}

export interface CreateVendorRequest {
  legal_name: string;
  contact_email: string;
  tax_id: string;
  address: Address;
}

export interface UpdateVendorRequest {
  legal_name?: string;
  contact_email?: string;
  address?: Address;
}
