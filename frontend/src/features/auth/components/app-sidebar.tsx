import {
  ClipboardList,
  CreditCard,
  LayoutDashboard,
  Package,
  ShieldCheck,
  Store as StoreIcon,
  Sparkles,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
  UserRound,
  Users,
  X,
  type LucideIcon,
} from "lucide-react";
import { NavLink, useNavigate } from "react-router-dom";

import { Logo } from "@/components/logo";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/sonner";
import { ROUTES } from "@/constants/routes";
import { useLogout } from "@/features/auth/api/auth.api";
import { useAuth } from "@/features/auth/context/use-auth";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { displayName } from "@/features/auth/utils/display-name";
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
  {
    to: ROUTES.assistant.root(),
    label: "Orbiz AI",
    icon: Sparkles,
    permission: "assistant.read",
  },
];

const ACCOUNT_NAV_ITEM: NavItem = {
  to: ROUTES.account(),
  label: "Account",
  icon: UserRound,
  end: true,
};

const PLATFORM_NAV_ITEMS: NavItem[] = [
  { to: ROUTES.admin.dashboard(), label: "Dashboard", icon: LayoutDashboard },
  { to: ROUTES.admin.stores(), label: "Stores", icon: StoreIcon },
  { to: ROUTES.admin.users(), label: "All users", icon: Users },
];

function SidebarNavLink({
  item,
  onNavigate,
  collapsed = false,
}: {
  item: NavItem;
  onNavigate?: () => void;
  collapsed?: boolean;
}) {
  return (
    <NavLink
      to={item.to}
      end={item.end}
      onClick={onNavigate}
      title={collapsed ? item.label : undefined}
      aria-label={collapsed ? item.label : undefined}
      className={({ isActive }) =>
        cn(
          "relative flex items-center gap-3 rounded-lg py-3 text-sm font-semibold transition-colors",
          collapsed ? "justify-center px-0" : "px-4",
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
          {collapsed ? null : item.label}
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
  /** Icon-only rail (desktop only). */
  collapsed?: boolean;
  onToggleCollapse?: () => void;
};

export function AppSidebar({
  mobile = false,
  onClose,
  onNavigate,
  className,
  collapsed: collapsedProp = false,
  onToggleCollapse,
}: AppSidebarProps) {
  const collapsed = collapsedProp && !mobile;
  const { user } = useAuth();
  const logout = useLogout();
  const navigate = useNavigate();
  const onSignOut = async () => {
    await logout.mutateAsync();
    toast.success("Signed out.");
    navigate(ROUTES.signIn(), { replace: true });
  };
  const { store, can, isStoreAdmin, isPlatformAdmin } = usePermissions();
  const navItems = [
    ...(isPlatformAdmin
      ? PLATFORM_NAV_ITEMS
      : STORE_NAV_ITEMS.filter((item) => {
          if (item.storeAdminOnly) return isStoreAdmin;
          return item.permission ? can(item.permission) : true;
        })),
    ACCOUNT_NAV_ITEM,
  ];

  return (
    <aside
      className={cn(
        "flex h-full shrink-0 flex-col border-r border-border bg-card text-foreground transition-[width] duration-200",
        collapsed ? "w-[4.5rem]" : "w-[15.5rem]",
        className,
      )}
      aria-label="Workspace"
    >
      <div
        className={cn(
          "flex h-16 shrink-0 items-center gap-2 px-4",
          collapsed ? "justify-center px-0" : "justify-between",
        )}
      >
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
        {!mobile && onToggleCollapse && !collapsed ? (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="size-9 rounded-full"
            aria-label="Collapse sidebar"
            onClick={onToggleCollapse}
          >
            <PanelLeftClose className="size-4" />
          </Button>
        ) : null}
      </div>

      {collapsed ? (
        onToggleCollapse ? (
          <div className="flex justify-center pb-2">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="size-9 rounded-full"
              aria-label="Expand sidebar"
              onClick={onToggleCollapse}
            >
              <PanelLeftOpen className="size-4" />
            </Button>
          </div>
        ) : null
      ) : isPlatformAdmin ? (
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
          <SidebarNavLink
            key={item.to}
            item={item}
            onNavigate={onNavigate}
            collapsed={collapsed}
          />
        ))}
      </nav>

      <div className="mt-auto border-t border-border px-3 py-4">
        {user && !collapsed ? (
          <p
            className="truncate px-4 pt-3 text-sm text-body"
            title={displayName(user)}
          >
            {displayName(user)}
          </p>
        ) : null}
        <Button
          type="button"
          variant="secondary"
          disabled={logout.isPending}
          onClick={() => {
            void onSignOut();
          }}
          title={collapsed ? "Sign out" : undefined}
          aria-label="Sign out"
          className="mt-2 h-10 w-full rounded-[24px] text-sm font-semibold"
        >
          <LogOut className="size-4" aria-hidden />
          {collapsed ? null : logout.isPending ? "Signing out…" : "Sign out"}
        </Button>
      </div>
    </aside>
  );
}
