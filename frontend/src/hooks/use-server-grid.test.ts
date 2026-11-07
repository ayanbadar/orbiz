import { describe, expect, it } from "vitest";

import { parseServerOrdering, toServerOrdering } from "@/hooks/use-server-grid";

describe("server grid ordering", () => {
  it("splits an ascending ordering into column and direction", () => {
    expect(parseServerOrdering("name")).toEqual({ colId: "name", sort: "asc" });
  });

  it("splits a descending ordering, keeping Django paths intact", () => {
    expect(parseServerOrdering("-customer__name")).toEqual({
      colId: "customer__name",
      sort: "desc",
    });
  });

  it("round-trips through toServerOrdering", () => {
    for (const ordering of ["name", "-order_count", "-last_order_at"]) {
      const { colId, sort } = parseServerOrdering(ordering);
      expect(toServerOrdering(colId, sort)).toBe(ordering);
    }
  });
});
