/** Customer as embedded in an order (`OrderSerializer.customer`). */
export type Customer = {
  id: number;
  name: string;
  email: string;
  phone: string;
  notes: string;
  created_at: string;
  updated_at: string;
};

/** Customer with order stats — every `/api/v1/customers/` response. */
export type CustomerSummary = Customer & {
  /** All of the customer's orders, drafts and cancelled included. */
  order_count: number;
  /** Orders not yet completed or cancelled (draft/unfulfilled/processing/shipped). */
  open_order_count: number;
  /** Latest order's `created_at`; null when the customer has no orders. */
  last_order_at: string | null;
};

export type CustomerCreateRequest = {
  name: string;
  email?: string;
  phone?: string;
  notes?: string;
};

export type CustomerUpdateRequest = Partial<CustomerCreateRequest>;

export type CustomerListOrdering =
  | "name"
  | "-name"
  | "order_count"
  | "-order_count"
  | "open_order_count"
  | "-open_order_count"
  | "last_order_at"
  | "-last_order_at"
  | "created_at"
  | "-created_at";

export type CustomerListParams = {
  q?: string;
  name?: string;
  email?: string;
  phone?: string;
  orders_min?: string;
  orders_max?: string;
  /** Only customers with at least one open order. */
  needs_attention?: boolean;
  page?: number;
  page_size?: number;
  ordering?: CustomerListOrdering;
};

export type { Paginated } from "@/lib/api/types";
