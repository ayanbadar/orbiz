import type { Order } from "@/features/orders/types";
import type {
  EmailLinkRequest,
  InvoiceRequest,
  PaymentCheckout,
  PaymentCheckoutDetailResponse,
  RefundRequest,
} from "@/features/payments/types";
import { api } from "@/lib/api";

const ROOT = "/api/v1/payments";

export class PaymentService {
  static async getCheckout(
    orderId: number,
  ): Promise<PaymentCheckoutDetailResponse> {
    const response = await api.get<PaymentCheckoutDetailResponse>(
      `${ROOT}/orders/${orderId}/`,
    );
    return response.data;
  }

  static async createCheckout(orderId: number): Promise<PaymentCheckout> {
    const response = await api.post<PaymentCheckout>(
      `${ROOT}/orders/${orderId}/checkout/`,
      {},
    );
    return response.data;
  }

  static async captureCheckout(orderId: number): Promise<Order> {
    const response = await api.post<Order>(
      `${ROOT}/orders/${orderId}/capture/`,
      {},
    );
    return response.data;
  }

  static async refundOrder(
    orderId: number,
    body: RefundRequest,
  ): Promise<Order> {
    const response = await api.post<Order>(
      `${ROOT}/orders/${orderId}/refund/`,
      body,
    );
    return response.data;
  }

  static async sendInvoice(
    orderId: number,
    body: InvoiceRequest,
  ): Promise<Order> {
    const response = await api.post<Order>(
      `${ROOT}/orders/${orderId}/invoice/`,
      body,
    );
    return response.data;
  }

  static async emailLink(
    orderId: number,
    body: EmailLinkRequest,
  ): Promise<Order> {
    const response = await api.post<Order>(
      `${ROOT}/orders/${orderId}/email-link/`,
      body,
    );
    return response.data;
  }

  static async cancelInvoice(orderId: number): Promise<Order> {
    const response = await api.post<Order>(
      `${ROOT}/orders/${orderId}/invoice/cancel/`,
      {},
    );
    return response.data;
  }
}
