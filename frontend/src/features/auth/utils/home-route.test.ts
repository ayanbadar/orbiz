import { describe, expect, it } from "vitest";

import { ROUTES } from "@/constants/routes";
import { getHomeRoute } from "@/features/auth/utils/home-route";
import type { Store } from "@/features/stores/types";

function store(overrides: Partial<Store>): Store {
  return {
    id: 1,
    name: "Shop",
    currency: "USD",
    timezone: "UTC",
    business_type: "social",
    status: "active",
    is_store_admin: false,
    role_name: "Staff",
    permissions: [],
    created_at: "",
    updated_at: "",
    ...overrides,
  };
}

describe("getHomeRoute", () => {
  it("sends platform admins to the stores list", () => {
    expect(getHomeRoute({ isPlatformAdmin: true })).toBe(ROUTES.admin.stores());
  });

  it("sends unpaid store admins to billing", () => {
    expect(
      getHomeRoute({
        store: store({ status: "pending_payment", is_store_admin: true }),
      }),
    ).toBe(ROUTES.billing());
  });

  it("sends staff to the first area their role can read", () => {
    expect(
      getHomeRoute({ store: store({ permissions: ["orders.read"] }) }),
    ).toBe(ROUTES.orders.root());
    expect(
      getHomeRoute({
        store: store({ permissions: ["products.read", "orders.read"] }),
      }),
    ).toBe(ROUTES.products.root());
  });

  it("falls back to the account page for a role with no readable area", () => {
    expect(getHomeRoute({ store: store({ permissions: [] }) })).toBe(
      ROUTES.account(),
    );
  });
});
