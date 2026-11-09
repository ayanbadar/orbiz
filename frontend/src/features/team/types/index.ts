export type { Paginated } from "@/lib/api/types";

export type StoreRef = {
  id: number;
  name: string;
  status: "pending_payment" | "active" | "suspended";
};

/** A person in a store: team page and super admin user lists share this shape. */
export type Member = {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  is_store_admin: boolean;
  role: { id: number; name: string } | null;
  store: StoreRef;
  date_joined: string;
  last_login: string | null;
};

export type Role = {
  id: number;
  name: string;
  description: string;
  permissions: string[];
  member_count: number;
  created_at: string;
};

export type RoleRequest = {
  name: string;
  description: string;
  permissions: string[];
};

export type UpdateMemberRequest = {
  first_name?: string;
  last_name?: string;
  is_active?: boolean;
  role_id?: number;
};

export type PermissionCatalog = {
  resources: { key: string; label: string }[];
  actions: { key: string; label: string }[];
  permissions: string[];
};

export type MemberListParams = {
  page: number;
  search?: string;
  is_active?: boolean;
  store?: number;
};
