import { apiFetch } from "@/lib/api/client";
import {
  CreateProductRequest,
  PagedProductsResponse,
  ProductResponse,
  UpdateProductRequest,
} from "@/types/product";

export function listProducts(token: string | null, businessId: string): Promise<PagedProductsResponse> {
  return apiFetch<PagedProductsResponse>(`/businesses/${businessId}/products`, token);
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
  body: CreateProductRequest
): Promise<ProductResponse> {
  return apiFetch<ProductResponse>(`/businesses/${businessId}/products`, token, {
    method: "POST",
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
