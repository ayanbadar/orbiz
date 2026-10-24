export type Customer = {
  id: number;
  name: string;
  email: string;
  phone: string;
  notes: string;
  created_at: string;
  updated_at: string;
};

export type CustomerCreateRequest = {
  name: string;
  email?: string;
  phone?: string;
  notes?: string;
};

export type CustomerListParams = {
  q?: string;
  page?: number;
  page_size?: number;
};

export type { Paginated } from "@/lib/api/types";
