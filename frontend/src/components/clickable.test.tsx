import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Clickable } from "@/components/clickable";
import { Button } from "@/components/ui/button";

describe("clickable", () => {
  it("uses the hand cursor", () => {
    render(<Clickable>Save</Clickable>);

    expect(screen.getByRole("button", { name: "Save" })).toHaveClass(
      "cursor-pointer",
    );
  });

  it("gives buttons the hand cursor", () => {
    render(<Button>Sign in</Button>);

    expect(screen.getByRole("button", { name: "Sign in" })).toHaveClass(
      "cursor-pointer",
    );
  });
});
