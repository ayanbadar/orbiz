import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { PasswordInput } from "@/components/password-input";

describe("password input", () => {
  it("shows and hides the typed password", async () => {
    const user = userEvent.setup();
    render(<PasswordInput id="password" aria-label="Password" />);

    const field = screen.getByLabelText("Password");
    await user.type(field, "secret");

    expect(field).toHaveAttribute("type", "password");

    await user.click(screen.getByRole("button", { name: "Show password" }));

    expect(field).toHaveAttribute("type", "text");
    expect(field).toHaveValue("secret");
    expect(
      screen.getByRole("button", { name: "Hide password" }),
    ).toHaveAttribute("aria-pressed", "true");

    await user.click(screen.getByRole("button", { name: "Hide password" }));

    expect(field).toHaveAttribute("type", "password");
  });
});
