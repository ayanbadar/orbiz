import { Menu } from "lucide-react";
import { useEffect, useId, useState, type ReactNode } from "react";
import { useLocation } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { ROUTES } from "@/constants/routes";
import { AppSidebar } from "@/features/auth/components/app-sidebar";
import { cn } from "cn";

// Pages that manage their own internal scrolling (a chat-style layout with a sidebar + a
// pinned composer, like Orbiz AI) need their own full remaining height instead of the normal
// padded, max-width, page-scrolls layout every other route uses.
const FULL_BLEED_ROUTES = [ROUTES.assistant.root()];

export function AppShell({ children }: { children: ReactNode }) {
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem("orbiz.sidebar.collapsed") === "1";
    } catch {
      return false;
    }
  });
  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem("orbiz.sidebar.collapsed", next ? "1" : "0");
      } catch {
        // ignore storage failures
      }
      return next;
    });
  };
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
        <AppSidebar collapsed={collapsed} onToggleCollapse={toggleCollapsed} />
      </div>

      <div className="flex min-w-0 flex-1 flex-col">
        <Button
          type="button"
          variant="secondary"
          size="icon"
          className="fixed top-3 left-3 z-20 size-10 rounded-full shadow-sm lg:hidden"
          aria-label="Open menu"
          aria-expanded={mobileOpen}
          aria-controls={drawerTitleId}
          onClick={() => setMobileOpen(true)}
        >
          <Menu className="size-5" />
        </Button>

        <main
          className={cn(
            isFullBleed
              ? "min-h-0 flex-1 overflow-hidden"
              : "mx-auto w-full max-w-[1200px] flex-1 px-4 pt-16 pb-8 sm:px-6 sm:py-10 lg:pt-10",
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
