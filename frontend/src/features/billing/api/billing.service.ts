import type { Billing, CheckoutRequest } from "@/features/billing/types";
import { api } from "@/lib/api";

const ROOT = "/api/v1/billing";

export class BillingService {
  static async get(): Promise<Billing> {
    const response = await api.get<Billing>(`${ROOT}/`);
    return response.data;
  }

  static async checkout(body: CheckoutRequest): Promise<Billing> {
    const response = await api.post<Billing>(`${ROOT}/checkout/`, body);
    return response.data;
  }

  static async cancel(): Promise<Billing> {
    const response = await api.post<Billing>(`${ROOT}/cancel/`);
    return response.data;
  }
}
