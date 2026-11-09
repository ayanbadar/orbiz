import { describe, expect, it } from "vitest";

import { formatMoney, getDelta } from "@/features/dashboard/utils/format";

describe("getDelta", () => {
  it("reports growth and decline as whole percentages", () => {
    expect(getDelta("150.00", "100.00")).toEqual({
      direction: "up",
      label: "+50%",
    });
    expect(getDelta(5, 10)).toEqual({ direction: "down", label: "-50%" });
  });

  it("handles an empty previous period", () => {
    expect(getDelta(4, 0)).toEqual({ direction: "up", label: "New" });
    expect(getDelta(0, 0)).toEqual({ direction: "flat", label: "No change" });
  });

  it("treats equal values as flat", () => {
    expect(getDelta(10, 10).direction).toBe("flat");
  });
});

describe("formatMoney", () => {
  it("formats with the currency code", () => {
    expect(formatMoney("1234.5", "USD")).toContain("1,234.50");
  });

  it("does not throw on an invalid currency", () => {
    expect(formatMoney("5", "??")).toContain("5.00");
  });
});
