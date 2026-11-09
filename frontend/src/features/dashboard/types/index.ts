import type { FulfilmentStatus, PaymentStatus } from "@/features/orders/types";

export type DashboardRange = "7d" | "30d" | "90d";

/** Money is sent as a decimal string; counts as numbers. */
export type MoneyKpi = { value: string; previous: string };
export type CountKpi = { value: number; previous: number };

export type StatusCount<S extends string> = { status: S; count: number };

export type StoreDashboard = {
  range: DashboardRange;
  currency: string;
  kpis: {
    revenue: MoneyKpi;
    orders: CountKpi;
    average_order_value: MoneyKpi;
    new_customers: CountKpi;
  };
  open_orders: number;
  orders_by_fulfilment: StatusCount<FulfilmentStatus>[];
  orders_by_payment: StatusCount<PaymentStatus>[];
  series: { date: string; orders: number; revenue: string }[];
  top_products: {
    product_id: number;
    name: string;
    sku: string;
    quantity: number;
    revenue: string;
  }[];
  low_stock: {
    id: number;
    name: string;
    sku: string;
    stock_quantity: number;
    low_stock_threshold: number;
  }[];
  recent_orders: {
    id: number;
    number: string;
    customer_name: string;
    total: string;
    currency: string;
    fulfilment_status: FulfilmentStatus;
    payment_status: PaymentStatus;
    created_at: string;
  }[];
};

export type PlatformDashboard = {
  range: DashboardRange;
  kpis: {
    stores: CountKpi;
    subscription_revenue_cents: CountKpi;
  };
  totals: { stores: number; users: number; active_users: number };
  stores_by_status: StatusCount<string>[];
  subscriptions_by_status: StatusCount<string>[];
  series: {
    date: string;
    new_stores: number;
    subscription_revenue_cents: number;
  }[];
  orders_by_currency: {
    currency: string;
    orders: number;
    stores: number;
    revenue: string | null;
  }[];
  top_stores: {
    store_id: number;
    name: string;
    currency: string;
    orders: number;
    revenue: string;
  }[];
};
