import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { SignInPage } from "@/features/auth/components/sign-in-page";
import { AuthProvider } from "@/features/auth/context/auth-context";

function renderSignIn() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <AuthProvider>{children}</AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>
    );
  }

  return render(<SignInPage />, { wrapper: Wrapper });
}

describe("sign in", () => {
  it("asks for an email before calling the API", async () => {
    const user = userEvent.setup();
    renderSignIn();

    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(
      await screen.findByText("Enter a valid email address"),
    ).toBeInTheDocument();
  });
});
