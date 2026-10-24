import type {
  Channel3SearchResponse,
  InventoryAdjustment,
  Paginated,
  Product,
  ProductCreateRequest,
  ProductListParams,
  ProductOrderUsage,
  ProductUpdateRequest,
  StockCheckResult,
} from "@/features/products/types";
import { api } from "@/lib/api";

const ROOT = "/api/v1/products";

export class ProductService {
  static async list(params: ProductListParams = {}): Promise<Paginated<Product>> {
    const response = await api.get<Paginated<Product>>(`${ROOT}/`, {
      params: {
        q: params.q || undefined,
        low_stock: params.low_stock ? "true" : undefined,
        out_of_stock: params.out_of_stock ? "true" : undefined,
        is_active:
          params.is_active === undefined
            ? undefined
            : params.is_active
              ? "true"
              : "false",
        page: params.page,
        page_size: params.page_size,
        ordering: params.ordering,
      },
    });
    return response.data;
  }

  static async get(id: number): Promise<Product> {
    const response = await api.get<Product>(`${ROOT}/${id}/`);
    return response.data;
  }

  static async create(body: ProductCreateRequest): Promise<Product> {
    const response = await api.post<Product>(`${ROOT}/`, body);
    return response.data;
  }

  static async update(id: number, body: ProductUpdateRequest): Promise<Product> {
    const response = await api.patch<Product>(`${ROOT}/${id}/`, body);
    return response.data;
  }

  static async deactivate(id: number): Promise<Product> {
    const response = await api.delete<Product>(`${ROOT}/${id}/`);
    return response.data;
  }

  static async adjustStock(
    id: number,
    body: { delta: number; reason: string },
  ): Promise<InventoryAdjustment> {
    const response = await api.post<InventoryAdjustment>(
      `${ROOT}/${id}/adjust-stock/`,
      body,
    );
    return response.data;
  }

  static async adjustments(id: number): Promise<InventoryAdjustment[]> {
    const response = await api.get<
      Paginated<InventoryAdjustment> | InventoryAdjustment[]
    >(`${ROOT}/${id}/adjustments/`);
    const data = response.data;
    return Array.isArray(data) ? data : data.results;
  }

  static async checkStock(
    id: number,
    quantity: number,
  ): Promise<StockCheckResult> {
    const response = await api.post<StockCheckResult>(
      `${ROOT}/${id}/check-stock/`,
      { quantity },
    );
    return response.data;
  }

  static async orderUsage(id: number): Promise<ProductOrderUsage[]> {
    const response = await api.get<ProductOrderUsage[]>(
      `${ROOT}/${id}/order-usage/`,
    );
    return response.data;
  }

  static async channel3Search(query: string): Promise<Channel3SearchResponse> {
    const response = await api.post<Channel3SearchResponse>(
      `${ROOT}/channel3/search/`,
      { query, limit: 10 },
    );
    return response.data;
  }

  static async importFromChannel3(body: {
    channel3_product_id: string;
    sku: string;
    price: string;
    stock_quantity: number;
    low_stock_threshold?: number;
  }): Promise<Product> {
    const response = await api.post<Product>(
      `${ROOT}/import-from-channel3/`,
      body,
    );
    return response.data;
  }
}
