import type { Order } from "@/features/orders/types";

export type AssistantMessageRole = "user" | "assistant";

export type AssistantMessage = {
  id: number;
  role: AssistantMessageRole;
  content: string;
  created_at: string;
};

export type AssistantActionType = "refund" | "capture" | "import_product";
export type AssistantActionStatus = "pending" | "confirmed" | "rejected" | "expired";

export type AssistantActionOrderRef = {
  id: number;
  number: string;
};

export type AssistantActionPayload = {
  amount?: string | null;
  sku?: string;
  price?: string;
  stock_quantity?: number;
  low_stock_threshold?: number;
  channel3_payload?: {
    title?: string;
    image_url?: string;
    brand?: string;
    suggested_price?: string;
  };
};

export type AssistantAction = {
  id: number;
  action_type: AssistantActionType;
  status: AssistantActionStatus;
  order: AssistantActionOrderRef | null;
  payload: AssistantActionPayload;
  result_message: string;
  created_at: string;
  resolved_at: string | null;
};

export type AssistantConversation = {
  conversation_id: number;
  messages: AssistantMessage[];
  actions: AssistantAction[];
  orders: Order[];
};

export type AssistantConversationSummary = {
  id: number;
  preview: string;
  created_at: string;
  updated_at: string;
};

export type AssistantTurnResponse = {
  conversation_id: number;
  reply: string;
  created_orders: Order[];
  pending_actions: AssistantAction[];
};

export type AssistantDigestOrderRow = {
  order_id: number;
  order_number: string;
  customer_name: string;
  total: string;
  currency: string;
  payment_status: string;
  days_old: number;
};

export type AssistantDigestProductRow = {
  name: string;
  sku: string;
  stock_quantity: number;
  low_stock_threshold: number;
};

export type AssistantDigest = {
  stale_unpaid_orders: AssistantDigestOrderRow[];
  low_stock_products: AssistantDigestProductRow[];
};

export type AssistantActivityItem = {
  id: number;
  order_id: number;
  order_number: string;
  event_type: string;
  message: string;
  created_at: string;
};

export type ActionConfirmOverrides = {
  amount?: string;
  sku?: string;
  price?: string;
  stock_quantity?: number;
  low_stock_threshold?: number;
};

export type { Paginated } from "@/lib/api/types";
