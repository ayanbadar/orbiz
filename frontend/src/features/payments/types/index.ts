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

export type PaymentRefundStatus =
  | "pending"
  | "completed"
  | "failed"
  | "cancelled";

export type PaymentRefund = {
  id: number;
  paypal_refund_id: string | null;
  status: PaymentRefundStatus;
  source: "orbiz" | "paypal";
  amount: string;
  currency: string;
  note_to_payer: string;
  last_error: string;
  created_at: string;
};

export type PaymentInvoiceStatus =
  | "draft"
  | "sent"
  | "shared"
  | "paid"
  | "partially_refunded"
  | "refunded"
  | "cancelled"
  | "failed";

export type PaymentInvoiceDelivery = "paypal" | "orbiz" | "none";

export type PaymentInvoice = {
  id: number;
  paypal_invoice_id: string | null;
  invoice_number: string;
  status: PaymentInvoiceStatus;
  recipient_email: string;
  delivered_via: PaymentInvoiceDelivery;
  recipient_view_url: string;
  amount: string;
  currency: string;
  is_sandbox: boolean;
  last_error: string;
  sent_at: string | null;
  paid_at: string | null;
  created_at: string;
};

export type EmailDeliveryStatus = "queued" | "sent" | "failed";

/** The one open PayPal payment request on an order (invoice or checkout link). */
export type PaymentRequestSummary = {
  kind: "invoice" | "checkout" | "none";
  status: string;
  url: string;
  recipient_email: string;
  delivered_via: PaymentInvoiceDelivery | "";
  last_emailed_at: string | null;
  last_email_status: EmailDeliveryStatus | "";
  last_email_error: string;
  can_email: boolean;
  /** Who emails a new invoice: Orbiz (our SMTP) or PayPal itself. */
  delivery_mode: "orbiz" | "paypal";
};

export type EmailLinkKind = "request" | "reminder";

export type EmailLinkRequest = {
  recipient_email?: string;
  kind?: EmailLinkKind;
};

export type RefundRequest = {
  amount?: string;
  note_to_payer?: string;
};

export type InvoiceRequest = {
  recipient_email?: string;
};

export type PaymentCheckoutDetailResponse = {
  paypal_configured: boolean;
  paypal_sandbox: boolean;
  checkout: PaymentCheckout | null;
};
