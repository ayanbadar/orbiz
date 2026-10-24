import type {
  Customer,
  CustomerCreateRequest,
  CustomerListParams,
  Paginated,
} from "@/features/customers/types";
import { api } from "@/lib/api";

const ROOT = "/api/v1/customers";

export class CustomerService {
  static async list(params: CustomerListParams = {}): Promise<Paginated<Customer>> {
    const response = await api.get<Paginated<Customer>>(`${ROOT}/`, {
      params: {
        q: params.q || undefined,
        page: params.page,
        page_size: params.page_size,
      },
    });
    return response.data;
  }

  static async get(id: number): Promise<Customer> {
    const response = await api.get<Customer>(`${ROOT}/${id}/`);
    return response.data;
  }

  static async create(body: CustomerCreateRequest): Promise<Customer> {
    const response = await api.post<Customer>(`${ROOT}/`, body);
    return response.data;
  }
}
