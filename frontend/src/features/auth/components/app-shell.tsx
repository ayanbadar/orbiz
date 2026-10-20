import { Menu } from "lucide-react";
import { useEffect, useId, useState, type ReactNode } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { Logo } from "@/components/logo";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/sonner";
import { ROUTES } from "@/constants/routes";
import { useLogout } from "@/features/auth/api/auth.api";
import { AppSidebar } from "@/features/auth/components/app-sidebar";
import { SHELL_TOP_BAR_CLASS } from "@/features/auth/components/shell-layout";
import { useAuth } from "@/features/auth/context/use-auth";
import { displayName } from "@/features/auth/utils/display-name";
import { cn } from "cn";

export function AppShell({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const logout = useLogout();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const drawerTitleId = useId();

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!mobileOpen) {
      return;
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMobileOpen(false);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [mobileOpen]);

  const onSignOut = async () => {
    await logout.mutateAsync();
    toast.success("Signed out.");
    navigate(ROUTES.signIn(), { replace: true });
  };

  return (
    <div className="flex min-h-dvh bg-background text-foreground">
      <div className="sticky top-0 hidden h-dvh lg:block">
        <AppSidebar />
      </div>

      <div className="flex min-w-0 flex-1 flex-col">
        <header
          className={cn(
            SHELL_TOP_BAR_CLASS,
            "sticky top-0 z-20 justify-between gap-3 bg-card px-4 sm:px-6",
          )}
        >
          <div className="flex items-center gap-2 lg:invisible lg:w-0 lg:overflow-hidden">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="size-10 rounded-full"
              aria-label="Open menu"
              aria-expanded={mobileOpen}
              aria-controls={drawerTitleId}
              onClick={() => setMobileOpen(true)}
            >
              <Menu className="size-5" />
            </Button>
            <Link to={ROUTES.products.root()} className="inline-flex">
              <Logo className="h-9 w-9" />
            </Link>
          </div>

          <nav className="ml-auto flex flex-wrap items-center gap-2 sm:gap-4">
            {user ? (
              <span className="hidden text-sm text-body sm:inline">
                {displayName(user)}
              </span>
            ) : null}
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
        </header>

        <main className="mx-auto w-full max-w-[1200px] flex-1 px-4 py-8 sm:px-6 sm:py-10">
          {children}
        </main>
      </div>

      {mobileOpen ? (
        <div className="fixed inset-0 z-40 lg:hidden" role="presentation">
          <button
            type="button"
            className="absolute inset-0 bg-foreground/30"
            aria-label="Close menu"
            onClick={() => setMobileOpen(false)}
          />
          <div
            id={drawerTitleId}
            role="dialog"
            aria-modal="true"
            aria-label="Workspace navigation"
            className="absolute inset-y-0 left-0 shadow-lg"
          >
            <AppSidebar
              mobile
              onClose={() => setMobileOpen(false)}
              onNavigate={() => setMobileOpen(false)}
            />
          </div>
        </div>
      ) : null}
    </div>
  );
}
