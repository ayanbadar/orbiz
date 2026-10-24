import { describe, expect, it } from "vitest";

import {
  isGenericHttpErrorMessage,
  readApiErrorMessage,
} from "@/lib/api/errors";

describe("readApiErrorMessage", () => {
  it("prefers detail", () => {
    expect(readApiErrorMessage({ detail: "Only drafts can be confirmed." })).toBe(
      "Only drafts can be confirmed.",
    );
  });

  it("reads DRF field errors", () => {
    expect(
      readApiErrorMessage({
        quantity: ["Insufficient stock. Only 2 available."],
      }),
    ).toBe("Insufficient stock. Only 2 available.");
  });

  it("reads list payloads", () => {
    expect(readApiErrorMessage(["Add at least one line."])).toBe(
      "Add at least one line.",
    );
  });
});

describe("isGenericHttpErrorMessage", () => {
  it("detects axios status fallbacks", () => {
    expect(isGenericHttpErrorMessage("Request failed with status code 400")).toBe(
      true,
    );
    expect(isGenericHttpErrorMessage("Insufficient stock.")).toBe(false);
  });
});
