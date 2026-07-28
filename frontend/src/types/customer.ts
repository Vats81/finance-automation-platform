export type CustomerStatus = "active" | "inactive";

export interface CustomerAddress {
  street: string;
  city: string;
  state: string;
  postal_code: string;
  country: string;
}

export interface CustomerResponse {
  id: string;
  business_id: string;
  name: string;
  phone: string | null;
  email: string | null;
  address: CustomerAddress | null;
  gst_number: string | null;
  status: CustomerStatus;
  created_at: string;
}

export interface PagedCustomersResponse {
  items: CustomerResponse[];
  total: number;
  offset: number;
  limit: number;
}

export interface CreateCustomerRequest {
  name: string;
  phone?: string;
  email?: string;
  address?: CustomerAddress;
  gst_number?: string;
}

export interface UpdateCustomerRequest {
  name?: string;
  phone?: string;
  email?: string;
  address?: CustomerAddress;
  gst_number?: string;
}
