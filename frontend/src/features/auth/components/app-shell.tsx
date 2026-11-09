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

// Pages that manage their own internal scrolling (a chat-style layout with a sidebar + a
// pinned composer, like Orbiz AI) need their own full remaining height instead of the normal
// padded, max-width, page-scrolls layout every other route uses.
const FULL_BLEED_ROUTES = [ROUTES.assistant.root()];

export function AppShell({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const logout = useLogout();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const drawerTitleId = useId();
  const isFullBleed = FULL_BLEED_ROUTES.includes(location.pathname);

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
    <div
      className={cn(
        "flex bg-background text-foreground",
        // A normal page only needs a height FLOOR (min-h-dvh) — it's free to grow taller and let
        // the whole page scroll. A full-bleed page needs a height CEILING too: without an actual
        // h-dvh somewhere in the chain, flex-1/min-h-0 further down have nothing fixed to size
        // against, the tree grows to fit its content instead, and "internal scroll" silently
        // becomes "scroll the whole page" — which is why the composer stayed below the fold.
        isFullBleed ? "h-dvh overflow-hidden" : "min-h-dvh",
      )}
    >
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
            <Link to={ROUTES.root()} className="inline-flex">
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

        <main
          className={cn(
            isFullBleed
              ? "min-h-0 flex-1 overflow-hidden"
              : "mx-auto w-full max-w-[1200px] flex-1 px-4 py-8 sm:px-6 sm:py-10",
          )}
        >
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
