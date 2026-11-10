export type BusinessType = "social" | "storefront" | "wholesale" | "other";

export type StoreStatus = "pending_payment" | "active" | "suspended";

export type Store = {
  id: number;
  name: string;
  currency: string;
  timezone: string;
  business_type: BusinessType;
  status: StoreStatus;
  is_store_admin: boolean;
  role_name: string | null;
  /** Permission codes like "products.read"; store admins hold every code. */
  permissions: string[];
  created_at: string;
  updated_at: string;
};

export type StoreCreateRequest = {
  name: string;
  currency: string;
  timezone: string;
  business_type: BusinessType;
};

export type StoreUpdateRequest = {
  name?: string;
  currency?: string;
  timezone?: string;
  business_type?: BusinessType;
};

export type { Paginated } from "@/lib/api/types";

/** A store as the platform admin sees it. */
export type AdminStore = {
  id: number;
  name: string;
  status: StoreStatus;
  admin_email: string | null;
  admin_name: string | null;
  admin_is_active: boolean | null;
  user_count: number;
  subscription_status: "active" | "past_due" | "canceled" | null;
  current_period_end: string | null;
  created_at: string;
};

export type AdminStoreListParams = {
  page: number;
  search?: string;
  status?: StoreStatus;
};

export type AdminStoreUpdateRequest = { name?: string; suspended?: boolean };
