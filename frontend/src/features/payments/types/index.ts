export type PaymentCheckoutStatus =
  | "created"
  | "approved"
  | "captured"
  | "failed"
  | "cancelled";

export type PaymentCheckout = {
  id: number;
  order?: number;
  paypal_order_id: string;
  status: PaymentCheckoutStatus;
  approve_url: string;
  capture_id: string;
  amount: string;
  currency: string;
  is_sandbox: boolean;
  last_error: string;
  created_at: string;
  updated_at: string;
};

export type PaymentCheckoutDetailResponse = {
  paypal_configured: boolean;
  paypal_sandbox: boolean;
  checkout: PaymentCheckout | null;
};
