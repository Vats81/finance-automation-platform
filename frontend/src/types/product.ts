export type ProductStatus = "active" | "inactive";

export interface ProductResponse {
  id: string;
  business_id: string;
  name: string;
  sku: string;
  category: string | null;
  selling_price: string;
  purchase_cost: string;
  current_quantity: string;
  minimum_stock_level: string;
  reorder_quantity: string;
  unit_of_measurement: string;
  vendor_id: string | null;
  stock_value: string;
  is_low_stock: boolean;
  is_out_of_stock: boolean;
  status: ProductStatus;
  created_at: string;
}

export interface PagedProductsResponse {
  items: ProductResponse[];
  total: number;
  offset: number;
  limit: number;
}

export interface CreateProductRequest {
  name: string;
  sku: string;
  selling_price: string;
  purchase_cost: string;
  category?: string;
  current_quantity?: string;
  minimum_stock_level?: string;
  reorder_quantity?: string;
  unit_of_measurement?: string;
}

export interface UpdateProductRequest {
  name?: string;
  category?: string;
  selling_price?: string;
  purchase_cost?: string;
  minimum_stock_level?: string;
  reorder_quantity?: string;
}
