import type {
  FulfilmentStatus,
  Order,
  OrderCreateRequest,
  OrderListItem,
  OrderListParams,
  OrderUpdateRequest,
  Paginated,
} from "@/features/orders/types";
import { api } from "@/lib/api";

const ROOT = "/api/v1/orders";

export class OrderService {
  static async list(params: OrderListParams = {}): Promise<Paginated<OrderListItem>> {
    const response = await api.get<Paginated<OrderListItem>>(`${ROOT}/`, {
      params: {
        q: params.q || undefined,
        fulfilment_status: params.fulfilment_status || undefined,
        payment_status: params.payment_status || undefined,
        page: params.page,
        page_size: params.page_size,
        ordering: params.ordering,
      },
    });
    return response.data;
  }

  static async get(id: number): Promise<Order> {
    const response = await api.get<Order>(`${ROOT}/${id}/`);
    return response.data;
  }

  static async create(body: OrderCreateRequest): Promise<Order> {
    const response = await api.post<Order>(`${ROOT}/`, body);
    return response.data;
  }

  static async update(id: number, body: OrderUpdateRequest): Promise<Order> {
    const response = await api.patch<Order>(`${ROOT}/${id}/`, body);
    return response.data;
  }

  static async confirm(id: number): Promise<Order> {
    const response = await api.post<Order>(`${ROOT}/${id}/confirm/`, {});
    return response.data;
  }

  static async cancel(id: number): Promise<Order> {
    const response = await api.post<Order>(`${ROOT}/${id}/cancel/`, {});
    return response.data;
  }

  static async transition(
    id: number,
    fulfilment_status: FulfilmentStatus,
    options?: { allow_unpaid?: boolean },
  ): Promise<Order> {
    const response = await api.post<Order>(`${ROOT}/${id}/transition/`, {
      fulfilment_status,
      allow_unpaid: options?.allow_unpaid ?? false,
    });
    return response.data;
  }

  static async markPaid(id: number): Promise<Order> {
    const response = await api.post<Order>(`${ROOT}/${id}/mark-paid/`, {});
    return response.data;
  }

  static async abandonPayment(id: number): Promise<Order> {
    const response = await api.post<Order>(`${ROOT}/${id}/abandon-payment/`, {});
    return response.data;
  }
}
