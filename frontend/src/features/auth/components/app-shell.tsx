import type { ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Logo } from "@/components/logo";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/sonner";
import { ROUTES } from "@/constants/routes";
import { useLogout } from "@/features/auth/api/auth.api";
import { useAuth } from "@/features/auth/context/use-auth";
import { displayName } from "@/features/auth/utils/display-name";

export function AppShell({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const logout = useLogout();
  const navigate = useNavigate();

  const onSignOut = async () => {
    await logout.mutateAsync();
    toast.success("Signed out.");
    navigate(ROUTES.signIn(), { replace: true });
  };

  return (
    <div className="min-h-dvh bg-background text-foreground">
      <header className="bg-card">
        <div className="mx-auto flex w-full max-w-[1200px] flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <Link to={ROUTES.account()} className="inline-flex">
            <Logo />
          </Link>
          <nav className="flex flex-wrap items-center gap-2 sm:gap-4">
            {user ? (
              <span className="hidden text-sm text-body sm:inline">
                {displayName(user)}
              </span>
            ) : null}
            <Link
              to={ROUTES.products.root()}
              className="text-sm font-semibold underline-offset-4 hover:underline"
            >
              Products
            </Link>
            <Link
              to={ROUTES.account()}
              className="text-sm font-semibold underline-offset-4 hover:underline"
            >
              Account
            </Link>
            <Button
              type="button"
              variant="secondary"
              disabled={logout.isPending}
              onClick={() => {
                void onSignOut();
              }}
              className="h-10 rounded-[24px] px-4 text-sm font-semibold"
            >
              {logout.isPending ? "Signing out…" : "Sign out"}
            </Button>
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-[1200px] px-4 py-6 sm:px-6 sm:py-8">
        {children}
      </main>
    </div>
  );
}
