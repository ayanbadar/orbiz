import {
  Ban,
  CheckCircle2,
  Store,
  Trash2,
  UserPlus,
  Users,
} from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { useConfirmDialog } from "@/components/confirm-dialog";
import { FormattedTime } from "@/components/formatted-time";
import { Pagination } from "@/components/pagination";
import { QueryState } from "@/components/query-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { toast } from "@/components/ui/sonner";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ROUTES } from "@/constants/routes";
import {
  useRevokeStoreAdminInvitation,
  useStoreAdminInvitations,
} from "@/features/invitations/api/invitations.api";
import { InviteStoreAdminDialog } from "@/features/invitations/components/invite-store-admin-dialog";
import { PendingInvitationsCard } from "@/features/invitations/components/pending-invitations-card";
import {
  useAdminStores,
  useDeleteAdminStore,
  useUpdateAdminStore,
} from "@/features/stores/api/stores.api";
import { StoreStatusBadge } from "@/features/stores/components/store-status-badge";
import type { AdminStore, StoreStatus } from "@/features/stores/types";
import { getErrorMessage } from "@/features/auth/utils/form-errors";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { cn } from "cn";

const FILTERS: { label: string; value: StoreStatus | undefined }[] = [
  { label: "All", value: undefined },
  { label: "Active", value: "active" },
  { label: "Unpaid", value: "pending_payment" },
  { label: "Suspended", value: "suspended" },
];

export function AdminStoresPage() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<StoreStatus | undefined>(undefined);
  const [page, setPage] = useState(1);
  const [inviteOpen, setInviteOpen] = useState(false);
  const debouncedSearch = useDebouncedValue(search.trim());
  const stores = useAdminStores({ page, search: debouncedSearch, status });
  const invitations = useStoreAdminInvitations();
  const update = useUpdateAdminStore();
  const remove = useDeleteAdminStore();
  const revoke = useRevokeStoreAdminInvitation();
  const { confirm, dialog } = useConfirmDialog();
  const rows = stores.data?.results ?? [];

  const toggleSuspended = async (store: AdminStore) => {
    const suspending = store.status !== "suspended";
    if (suspending) {
      const ok = await confirm({
        title: `Suspend ${store.name}?`,
        description:
          "Everyone in this store loses access immediately until you reactivate it.",
        confirmLabel: "Suspend store",
        variant: "destructive",
      });
      if (!ok) return;
    }
    try {
      await update.mutateAsync({
        id: store.id,
        body: { suspended: suspending },
      });
      toast.success(suspending ? "Store suspended." : "Store reactivated.");
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not update the store."));
    }
  };

  const onDelete = async (store: AdminStore) => {
    const ok = await confirm({
      title: `Delete ${store.name}?`,
      description: `This permanently deletes the store, its products, orders and all ${store.user_count} user account(s). This can't be undone.`,
      confirmLabel: "Delete store",
      variant: "destructive",
    });
    if (!ok) return;
    try {
      await remove.mutateAsync(store.id);
      toast.success("Store deleted.");
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not delete the store."));
    }
  };

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-[28px] font-semibold tracking-tight sm:text-[32px]">
            Stores
          </h1>
          <p className="text-body">
            Every store on the platform, with its admin and plan status.
          </p>
        </div>
        <Button
          className="h-12 rounded-[24px] px-6 font-semibold"
          onClick={() => setInviteOpen(true)}
        >
          <UserPlus aria-hidden /> Invite store admin
        </Button>
      </header>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <Input
          value={search}
          placeholder="Search by store or admin email"
          className="h-9 w-full max-w-sm rounded-lg bg-card"
          onChange={(event) => {
            setSearch(event.target.value);
            setPage(1);
          }}
        />
        <div
          className="flex flex-wrap gap-2"
          role="group"
          aria-label="Filter by status"
        >
          {FILTERS.map((filter) => (
            <button
              key={filter.label}
              type="button"
              aria-pressed={status === filter.value}
              onClick={() => {
                setStatus(filter.value);
                setPage(1);
              }}
              className={cn(
                "rounded-full px-3 py-1.5 text-sm font-semibold transition-colors",
                status === filter.value
                  ? "bg-foreground text-background"
                  : "bg-card text-body hover:bg-secondary",
              )}
            >
              {filter.label}
            </button>
          ))}
        </div>
      </div>

      <QueryState
        isLoading={stores.isLoading}
        isError={stores.isError}
        errorMessage="Could not load stores."
        onRetry={() => void stores.refetch()}
      >
        <Card className="gap-0 overflow-hidden rounded-[24px] py-0 ring-0">
          <CardContent className="p-0">
            {rows.length === 0 ? (
              <div className="flex flex-col items-center gap-2 px-6 py-12 text-center">
                <Store className="size-8 text-muted-foreground" aria-hidden />
                <p className="font-semibold">No stores found</p>
                <p className="text-sm text-body">
                  Invite a store admin to get started.
                </p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead>Store</TableHead>
                    <TableHead>Admin</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Plan renews</TableHead>
                    <TableHead>Users</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((store) => (
                    <TableRow key={store.id}>
                      <TableCell className="font-semibold">
                        {store.name}
                      </TableCell>
                      <TableCell>
                        <p>{store.admin_name || "—"}</p>
                        <p className="text-xs text-muted-foreground">
                          {store.admin_email}
                          {store.admin_is_active === false
                            ? " · deactivated"
                            : ""}
                        </p>
                      </TableCell>
                      <TableCell>
                        <StoreStatusBadge status={store.status} />
                      </TableCell>
                      <TableCell className="text-body">
                        {store.current_period_end ? (
                          <FormattedTime
                            value={store.current_period_end}
                            variant="date"
                          />
                        ) : (
                          "—"
                        )}
                      </TableCell>
                      <TableCell>
                        <Link
                          to={`${ROUTES.admin.users()}?store=${store.id}`}
                          className="inline-flex items-center gap-1.5 font-semibold underline-offset-4 hover:underline"
                        >
                          <Users className="size-4" aria-hidden />{" "}
                          {store.user_count}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="rounded-lg"
                            onClick={() => void toggleSuspended(store)}
                          >
                            {store.status === "suspended" ? (
                              <>
                                <CheckCircle2 aria-hidden /> Reactivate
                              </>
                            ) : (
                              <>
                                <Ban aria-hidden /> Suspend
                              </>
                            )}
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon-lg"
                            aria-label={`Delete ${store.name}`}
                            onClick={() => void onDelete(store)}
                          >
                            <Trash2 />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
        <Pagination
          page={page}
          totalCount={stores.data?.count ?? 0}
          onPageChange={setPage}
          className="mt-4"
        />
      </QueryState>

      <PendingInvitationsCard
        title="Pending store-admin invitations"
        invitations={invitations.data ?? []}
        badge={(invitation) => invitation.store_name}
        onRevoke={(invitation) =>
          void revoke
            .mutateAsync(invitation.id)
            .then(() => toast.success("Invitation revoked."))
            .catch((error: unknown) =>
              toast.error(
                getErrorMessage(error, "Could not revoke the invitation."),
              ),
            )
        }
      />

      <InviteStoreAdminDialog open={inviteOpen} onOpenChange={setInviteOpen} />
      {dialog}
    </div>
  );
}
