import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Toaster, toast } from "@/components/ui/sonner";

describe("toast", () => {
  it("shows a success message", async () => {
    render(<Toaster />);

    toast.success("Profile saved.");

    expect(await screen.findByText("Profile saved.")).toBeInTheDocument();
    toast.dismiss();
  });
});
