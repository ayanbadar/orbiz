import {
  ClipboardList,
  CreditCard,
  LayoutDashboard,
  Package,
  ShieldCheck,
  Store as StoreIcon,
  UserRound,
  Users,
  X,
  type LucideIcon,
} from "lucide-react";
import { NavLink } from "react-router-dom";

import { Logo } from "@/components/logo";
import { Button } from "@/components/ui/button";
import { ROUTES } from "@/constants/routes";
import { SHELL_TOP_BAR_CLASS } from "@/features/auth/components/shell-layout";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { cn } from "cn";

type NavItem = {
  to: string;
  label: string;
  icon: LucideIcon;
  end?: boolean;
  /** Hidden unless the user holds this permission. */
  permission?: string;
  storeAdminOnly?: boolean;
};

const STORE_NAV_ITEMS: NavItem[] = [
  {
    to: ROUTES.dashboard(),
    label: "Dashboard",
    icon: LayoutDashboard,
    permission: "orders.read",
  },
  {
    to: ROUTES.orders.root(),
    label: "Orders",
    icon: ClipboardList,
    permission: "orders.read",
  },
  {
    to: ROUTES.customers.root(),
    label: "Customers",
    icon: Users,
    permission: "customers.read",
  },
  {
    to: ROUTES.products.root(),
    label: "Products",
    icon: Package,
    permission: "products.read",
  },
  {
    to: ROUTES.team.users(),
    label: "Team",
    icon: Users,
    permission: "users.read",
    end: true,
  },
  {
    to: ROUTES.team.roles(),
    label: "Roles",
    icon: ShieldCheck,
    storeAdminOnly: true,
  },
  {
    to: ROUTES.billing(),
    label: "Billing",
    icon: CreditCard,
    storeAdminOnly: true,
  },
];

const PLATFORM_NAV_ITEMS: NavItem[] = [
  { to: ROUTES.admin.dashboard(), label: "Dashboard", icon: LayoutDashboard },
  { to: ROUTES.admin.stores(), label: "Stores", icon: StoreIcon },
  { to: ROUTES.admin.users(), label: "All users", icon: Users },
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
  const { store, can, isStoreAdmin, isPlatformAdmin } = usePermissions();
  const navItems = isPlatformAdmin
    ? PLATFORM_NAV_ITEMS
    : STORE_NAV_ITEMS.filter((item) => {
        if (item.storeAdminOnly) return isStoreAdmin;
        return item.permission ? can(item.permission) : true;
      });

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
          to={ROUTES.root()}
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

      {isPlatformAdmin ? (
        <div className="space-y-0.5 px-4 pb-3">
          <p className="text-sm font-semibold text-foreground">
            Platform admin
          </p>
          <p className="text-xs text-muted-foreground">All stores</p>
        </div>
      ) : store ? (
        <div className="space-y-0.5 px-4 pb-3">
          <p
            className="truncate text-sm font-semibold text-foreground"
            title={store.name}
          >
            {store.name}
          </p>
          <p className="truncate text-xs text-muted-foreground">
            {store.is_store_admin
              ? "Store admin"
              : (store.role_name ?? "Staff")}{" "}
            · {store.currency}
          </p>
        </div>
      ) : null}

      <nav className="flex flex-1 flex-col gap-1 px-3 py-3">
        {navItems.map((item) => (
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
