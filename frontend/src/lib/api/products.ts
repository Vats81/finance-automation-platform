import { apiFetch } from "@/lib/api/client";
import { IdempotencyOptions, idempotencyHeaders } from "@/lib/idempotency";
import {
  CreateProductRequest,
  PagedProductsResponse,
  ProductResponse,
  UpdateProductRequest,
} from "@/types/product";

export function listProducts(
  token: string | null,
  businessId: string,
  options?: { limit?: number }
): Promise<PagedProductsResponse> {
  const query = options?.limit ? `?limit=${options.limit}` : "";
  return apiFetch<PagedProductsResponse>(`/businesses/${businessId}/products${query}`, token);
}

export function getProduct(
  token: string | null,
  businessId: string,
  productId: string
): Promise<ProductResponse> {
  return apiFetch<ProductResponse>(`/businesses/${businessId}/products/${productId}`, token);
}

export function createProduct(
  token: string | null,
  businessId: string,
  body: CreateProductRequest,
  options?: IdempotencyOptions
): Promise<ProductResponse> {
  return apiFetch<ProductResponse>(`/businesses/${businessId}/products`, token, {
    method: "POST",
    headers: idempotencyHeaders(options),
    body: JSON.stringify(body),
  });
}

export function updateProduct(
  token: string | null,
  businessId: string,
  productId: string,
  body: UpdateProductRequest
): Promise<ProductResponse> {
  return apiFetch<ProductResponse>(`/businesses/${businessId}/products/${productId}`, token, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function adjustStock(
  token: string | null,
  businessId: string,
  productId: string,
  delta: string,
  reason: string
): Promise<ProductResponse> {
  return apiFetch<ProductResponse>(`/businesses/${businessId}/products/${productId}/adjust-stock`, token, {
    method: "POST",
    body: JSON.stringify({ delta, reason }),
  });
}

export function deactivateProduct(
  token: string | null,
  businessId: string,
  productId: string
): Promise<ProductResponse> {
  return apiFetch<ProductResponse>(`/businesses/${businessId}/products/${productId}/deactivate`, token, {
    method: "POST",
  });
}

export function reactivateProduct(
  token: string | null,
  businessId: string,
  productId: string
): Promise<ProductResponse> {
  return apiFetch<ProductResponse>(`/businesses/${businessId}/products/${productId}/reactivate`, token, {
    method: "POST",
  });
}
