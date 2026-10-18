export type BusinessType = "social" | "storefront" | "wholesale" | "other";

export type Store = {
  id: number;
  name: string;
  currency: string;
  timezone: string;
  business_type: BusinessType;
  role: "owner" | "member" | null;
  is_default: boolean;
  created_at: string;
  updated_at: string;
};

export type StoreCreateRequest = {
  name: string;
  currency: string;
  timezone: string;
  business_type: BusinessType;
};

export type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};
