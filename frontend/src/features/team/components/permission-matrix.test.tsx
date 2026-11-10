import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { PermissionMatrix } from "@/features/team/components/permission-matrix";
import type { PermissionCatalog } from "@/features/team/types";

const catalog: PermissionCatalog = {
  resources: [{ key: "products", label: "Products" }],
  actions: [
    { key: "read", label: "View" },
    { key: "create", label: "Create" },
    { key: "update", label: "Edit" },
    { key: "delete", label: "Delete" },
  ],
  permissions: [
    "products.read",
    "products.create",
    "products.update",
    "products.delete",
  ],
};

describe("PermissionMatrix", () => {
  it("granting an action also grants view", async () => {
    const onChange = vi.fn();
    render(
      <PermissionMatrix catalog={catalog} value={[]} onChange={onChange} />,
    );
    await userEvent.click(
      screen.getByRole("checkbox", { name: "Products: Edit" }),
    );
    expect(onChange).toHaveBeenCalledWith(["products.read", "products.update"]);
  });

  it("removing view removes every action for that area", async () => {
    const onChange = vi.fn();
    render(
      <PermissionMatrix
        catalog={catalog}
        value={["products.read", "products.create"]}
        onChange={onChange}
      />,
    );
    await userEvent.click(
      screen.getByRole("checkbox", { name: "Products: View" }),
    );
    expect(onChange).toHaveBeenCalledWith([]);
  });
});
