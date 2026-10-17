import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Button } from "@/components/ui/button";

describe("foundation", () => {
  it("renders a shadcn button via path aliases", () => {
    render(<Button>Foundation ready</Button>);

    expect(
      screen.getByRole("button", { name: "Foundation ready" }),
    ).toBeInTheDocument();
  });
});
