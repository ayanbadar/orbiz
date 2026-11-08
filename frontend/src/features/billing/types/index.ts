export type SubscriptionStatus = "active" | "past_due" | "canceled";

export type Payment = {
  id: number;
  amount_cents: number;
  status: "succeeded" | "failed";
  reference: string;
  created_at: string;
};

export type Billing = {
  plan_price_cents: number;
  plan_period_days: number;
  store_status: "pending_payment" | "active" | "suspended";
  subscription_status: SubscriptionStatus;
  current_period_end: string | null;
  payments: Payment[];
};

export type CheckoutRequest = {
  card_number?: string;
  simulate_failure?: boolean;
};
