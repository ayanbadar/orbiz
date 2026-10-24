import { ClipboardList, Package, UserRound, X, type LucideIcon } from "lucide-react";
import { NavLink } from "react-router-dom";

import { Logo } from "@/components/logo";
import { Button } from "@/components/ui/button";
import { ROUTES } from "@/constants/routes";
import { SHELL_TOP_BAR_CLASS } from "@/features/auth/components/shell-layout";
import { useCurrentStore } from "@/features/stores/api/stores.api";
import { cn } from "cn";

type NavItem = {
  to: string;
  label: string;
  icon: LucideIcon;
  end?: boolean;
};

const NAV_ITEMS: NavItem[] = [
  {
    to: ROUTES.orders.root(),
    label: "Orders",
    icon: ClipboardList,
  },
  {
    to: ROUTES.products.root(),
    label: "Products",
    icon: Package,
  },
];

function SidebarNavLink({
  item,
  onNavigate,
}: {
  item: NavItem;
  onNavigate?: () => void;
}) {
  return (
    <NavLink
      to={item.to}
      end={item.end}
      onClick={onNavigate}
      className={({ isActive }) =>
        cn(
          "relative flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-semibold transition-colors",
          isActive
            ? "bg-muted text-foreground"
            : "text-body hover:bg-secondary hover:text-foreground",
        )
      }
    >
      {({ isActive }) => (
        <>
          {isActive ? (
            <span
              aria-hidden
              className="absolute top-2 bottom-2 left-0 w-1 rounded-full bg-primary"
            />
          ) : null}
          <item.icon className="size-4 shrink-0" aria-hidden />
          {item.label}
        </>
      )}
    </NavLink>
  );
}

type AppSidebarProps = {
  mobile?: boolean;
  onClose?: () => void;
  onNavigate?: () => void;
  className?: string;
};

export function AppSidebar({
  mobile = false,
  onClose,
  onNavigate,
  className,
}: AppSidebarProps) {
  const storeQuery = useCurrentStore();
  const store = storeQuery.data;

  return (
    <aside
      className={cn(
        "flex h-full w-[15.5rem] shrink-0 flex-col border-r border-border bg-card text-foreground",
        className,
      )}
      aria-label="Workspace"
    >
      <div className={cn(SHELL_TOP_BAR_CLASS, "justify-between gap-2 px-4")}>
        <NavLink
          to={ROUTES.products.root()}
          className="inline-flex"
          onClick={onNavigate}
        >
          <Logo className="h-9 w-9" />
        </NavLink>
        {mobile ? (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="size-10 rounded-full"
            aria-label="Close menu"
            onClick={onClose}
          >
            <X className="size-5" />
          </Button>
        ) : null}
      </div>

      {store ? (
        <div className="space-y-0.5 px-4 pb-3">
          <p
            className="truncate text-sm font-semibold text-foreground"
            title={store.name}
          >
            {store.name}
          </p>
          <p className="truncate text-xs text-muted-foreground">
            {store.currency}
          </p>
        </div>
      ) : null}

      <nav className="flex flex-1 flex-col gap-1 px-3 py-3">
        {NAV_ITEMS.map((item) => (
          <SidebarNavLink key={item.to} item={item} onNavigate={onNavigate} />
        ))}
      </nav>

      <div className="mt-auto border-t border-border px-3 py-4">
        <SidebarNavLink
          item={{
            to: ROUTES.account(),
            label: "Account",
            icon: UserRound,
            end: true,
          }}
          onNavigate={onNavigate}
        />
      </div>
    </aside>
  );
}
