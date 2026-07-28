import { apiFetch } from "@/lib/api/client";
import {
  CreateCustomerRequest,
  CustomerResponse,
  PagedCustomersResponse,
  UpdateCustomerRequest,
} from "@/types/customer";

export function listCustomers(token: string | null, businessId: string): Promise<PagedCustomersResponse> {
  return apiFetch<PagedCustomersResponse>(`/businesses/${businessId}/customers`, token);
}

export function getCustomer(
  token: string | null,
  businessId: string,
  customerId: string
): Promise<CustomerResponse> {
  return apiFetch<CustomerResponse>(`/businesses/${businessId}/customers/${customerId}`, token);
}

export function createCustomer(
  token: string | null,
  businessId: string,
  body: CreateCustomerRequest
): Promise<CustomerResponse> {
  return apiFetch<CustomerResponse>(`/businesses/${businessId}/customers`, token, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateCustomer(
  token: string | null,
  businessId: string,
  customerId: string,
  body: UpdateCustomerRequest
): Promise<CustomerResponse> {
  return apiFetch<CustomerResponse>(`/businesses/${businessId}/customers/${customerId}`, token, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function deactivateCustomer(
  token: string | null,
  businessId: string,
  customerId: string
): Promise<CustomerResponse> {
  return apiFetch<CustomerResponse>(`/businesses/${businessId}/customers/${customerId}/deactivate`, token, {
    method: "POST",
  });
}

export function reactivateCustomer(
  token: string | null,
  businessId: string,
  customerId: string
): Promise<CustomerResponse> {
  return apiFetch<CustomerResponse>(`/businesses/${businessId}/customers/${customerId}/reactivate`, token, {
    method: "POST",
  });
}
