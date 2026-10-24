export type Product = {
  id: number;
  name: string;
  sku: string;
  description: string;
  price: string;
  currency: string;
  stock_quantity: number;
  low_stock_threshold: number;
  is_active: boolean;
  is_low_stock: boolean;
  image_url: string;
  channel3_product_id: string;
  created_at: string;
  updated_at: string;
};

export type ProductCreateRequest = {
  name: string;
  sku: string;
  description?: string;
  price: string;
  stock_quantity?: number;
  low_stock_threshold?: number;
  is_active?: boolean;
  image_url?: string;
};

export type ProductUpdateRequest = {
  name?: string;
  sku?: string;
  description?: string;
  price?: string;
  low_stock_threshold?: number;
  is_active?: boolean;
  image_url?: string;
};

/** Matches ProductListCreateView allowed `ordering` values. */
export type ProductListOrdering =
  | "name"
  | "-name"
  | "price"
  | "-price"
  | "stock_quantity"
  | "-stock_quantity"
  | "updated_at"
  | "-updated_at";

export type ProductListParams = {
  q?: string;
  low_stock?: boolean;
  out_of_stock?: boolean;
  is_active?: boolean;
  page?: number;
  page_size?: number;
  ordering?: ProductListOrdering;
};

export type InventoryAdjustment = {
  id: number;
  delta: number;
  quantity_before: number;
  quantity_after: number;
  reason: string;
  created_by_email: string | null;
  created_at: string;
};

export type StockCheckResult = {
  product_id: number;
  sku: string;
  requested_quantity: number;
  stock_quantity: number;
  available: boolean;
};

export type ProductOrderUsage = {
  order_id: number;
  order_number: string;
  quantity: number;
  line_total: string;
  fulfilment_status: string;
  created_at: string;
};

export type Channel3Result = {
  channel3_product_id: string;
  title: string;
  description: string;
  image_url: string;
  suggested_price: string | null;
  currency: string;
  brand: string | null;
  availability: string | null;
};

export type Channel3SearchResponse = {
  results: Channel3Result[];
  next_page_token: string | null;
};

export type { Paginated } from "@/lib/api/types";
