import type {
  CustomerCreateRequest,
  CustomerListParams,
  CustomerSummary,
  CustomerUpdateRequest,
  Paginated,
} from "@/features/customers/types";
import { api } from "@/lib/api";

const ROOT = "/api/v1/customers";

export class CustomerService {
  static async list(
    params: CustomerListParams = {},
  ): Promise<Paginated<CustomerSummary>> {
    const response = await api.get<Paginated<CustomerSummary>>(`${ROOT}/`, {
      params: {
        q: params.q || undefined,
        name: params.name || undefined,
        email: params.email || undefined,
        phone: params.phone || undefined,
        orders_min: params.orders_min || undefined,
        orders_max: params.orders_max || undefined,
        needs_attention: params.needs_attention || undefined,
        page: params.page,
        page_size: params.page_size,
        ordering: params.ordering,
      },
    });
    return response.data;
  }

  static async get(id: number): Promise<CustomerSummary> {
    const response = await api.get<CustomerSummary>(`${ROOT}/${id}/`);
    return response.data;
  }

  static async create(body: CustomerCreateRequest): Promise<CustomerSummary> {
    const response = await api.post<CustomerSummary>(`${ROOT}/`, body);
    return response.data;
  }

  static async update(
    id: number,
    body: CustomerUpdateRequest,
  ): Promise<CustomerSummary> {
    const response = await api.patch<CustomerSummary>(`${ROOT}/${id}/`, body);
    return response.data;
  }
}
