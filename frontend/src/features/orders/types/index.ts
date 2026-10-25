import type { Customer } from "@/features/customers/types";

export type FulfilmentStatus =
  | "draft"
  | "unfulfilled"
  | "processing"
  | "shipped"
  | "completed"
  | "cancelled";

export type PaymentStatus =
  | "unpaid"
  | "pending"
  | "paid"
  | "failed"
  | "cancelled";

export type OrderLine = {
  id: number;
  product_id: number;
  product_name: string;
  sku: string;
  unit_price: string;
  quantity: number;
  line_total: string;
};

export type OrderEvent = {
  id: number;
  event_type: string;
  from_value: string;
  to_value: string;
  message: string;
  actor: number | null;
  created_at: string;
};

export type Order = {
  id: number;
  number: string;
  customer: Customer;
  fulfilment_status: FulfilmentStatus;
  payment_status: PaymentStatus;
  currency: string;
  subtotal: string;
  total: string;
  delivery_notes: string;
  internal_notes: string;
  source_message: string;
  stock_deducted: boolean;
  confirmed_at: string | null;
  cancelled_at: string | null;
  lines: OrderLine[];
  events: OrderEvent[];
  created_at: string;
  updated_at: string;
};

export type OrderListItem = {
  id: number;
  number: string;
  customer_name: string;
  fulfilment_status: FulfilmentStatus;
  payment_status: PaymentStatus;
  currency: string;
  total: string;
  created_at: string;
  updated_at: string;
};

export type OrderListOrdering =
  | "created_at"
  | "-created_at"
  | "total"
  | "-total"
  | "number"
  | "-number"
  | "customer__name"
  | "-customer__name"
  | "updated_at"
  | "-updated_at";

export type OrderListParams = {
  q?: string;
  number?: string;
  customer_name?: string;
  fulfilment_status?: FulfilmentStatus;
  payment_status?: PaymentStatus;
  total_min?: string;
  total_max?: string;
  created_after?: string;
  created_before?: string;
  page?: number;
  page_size?: number;
  ordering?: OrderListOrdering;
};

export type OrderLineInput = {
  product_id: number;
  quantity: number;
};

export type OrderCreateRequest = {
  customer_id: number;
  delivery_notes?: string;
  internal_notes?: string;
  source_message?: string;
  lines: OrderLineInput[];
};

export type OrderUpdateRequest = {
  customer_id?: number;
  delivery_notes?: string;
  internal_notes?: string;
  source_message?: string;
  lines?: OrderLineInput[];
};

export type { Paginated } from "@/lib/api/types";
