import { Pencil, Power, Trash2, X } from "lucide-react";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";

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
import {
  useAdminUsers,
  useDeleteAdminUser,
  useUpdateAdminUser,
} from "@/features/auth/api/admin-users.api";
import { AdminEditUserDialog } from "@/features/auth/components/admin-edit-user-dialog";
import { StoreStatusBadge } from "@/features/stores/components/store-status-badge";
import { getErrorMessage } from "@/features/auth/utils/form-errors";
import { MemberStatusBadge } from "@/features/team/components/member-status-badge";
import type { Member } from "@/features/team/types";
import { memberName, memberRoleLabel } from "@/features/team/utils/member";
import { useDebouncedValue } from "@/hooks/use-debounced-value";

export function AdminUsersPage() {
  const [params, setParams] = useSearchParams();
  const storeId = params.get("store") ? Number(params.get("store")) : undefined;
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<Member | null>(null);
  const debouncedSearch = useDebouncedValue(search.trim());
  const users = useAdminUsers({
    page,
    search: debouncedSearch,
    store: storeId,
  });
  const update = useUpdateAdminUser();
  const remove = useDeleteAdminUser();
  const { confirm, dialog } = useConfirmDialog();
  const rows = users.data?.results ?? [];
  const filteredStoreName = storeId ? rows[0]?.store.name : undefined;

  const toggleActive = async (user: Member) => {
    const deactivating = user.is_active;
    if (deactivating) {
      const ok = await confirm({
        title: `Deactivate ${memberName(user)}?`,
        description: user.is_store_admin
          ? `${user.store.name} will be suspended: its admin and every staff member lose access until you reactivate them.`
          : "They'll be signed out and can't use the store until reactivated.",
        confirmLabel: "Deactivate",
        variant: "destructive",
      });
      if (!ok) return;
    }
    try {
      await update.mutateAsync({
        id: user.id,
        body: { is_active: !deactivating },
      });
      toast.success(deactivating ? "User deactivated." : "User reactivated.");
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not update the user."));
    }
  };

  const onDelete = async (user: Member) => {
    const ok = await confirm({
      title: `Delete ${memberName(user)}?`,
      description: user.is_store_admin
        ? `${user.store.name} is deleted with them: its products, orders and every user account. This can't be undone.`
        : "This permanently removes their account. This can't be undone.",
      confirmLabel: "Delete",
      variant: "destructive",
    });
    if (!ok) return;
    try {
      await remove.mutateAsync(user.id);
      toast.success("Deleted.");
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not delete the user."));
    }
  };

  return (
    <div className="space-y-5">
      <header className="space-y-1">
        <h1 className="text-[28px] font-semibold tracking-tight sm:text-[32px]">
          All users
        </h1>
        <p className="text-body">Every account across every store.</p>
      </header>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <Input
          value={search}
          placeholder="Search by name or email"
          className="h-9 w-full max-w-sm rounded-lg bg-card"
          onChange={(event) => {
            setSearch(event.target.value);
            setPage(1);
          }}
        />
        {storeId ? (
          <button
            type="button"
            onClick={() => {
              setParams({});
              setPage(1);
            }}
            className="inline-flex items-center gap-1.5 rounded-full bg-foreground px-3 py-1.5 text-sm font-semibold text-background"
          >
            Store: {filteredStoreName ?? `#${storeId}`}{" "}
            <X className="size-3.5" aria-hidden />
            <span className="sr-only">Clear store filter</span>
          </button>
        ) : null}
      </div>

      <QueryState
        isLoading={users.isLoading}
        isError={users.isError}
        errorMessage="Could not load users."
        onRetry={() => void users.refetch()}
      >
        <Card className="gap-0 overflow-hidden rounded-[24px] py-0 ring-0">
          <CardContent className="p-0">
            {rows.length === 0 ? (
              <p className="px-6 py-10 text-center text-sm text-muted-foreground">
                No users found.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead>User</TableHead>
                    <TableHead>Store</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Last sign-in</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((user) => (
                    <TableRow key={user.id}>
                      <TableCell>
                        <p className="font-semibold">{memberName(user)}</p>
                        <p className="text-xs text-muted-foreground">
                          {user.email}
                        </p>
                      </TableCell>
                      <TableCell>
                        <p>{user.store.name}</p>
                        <StoreStatusBadge status={user.store.status} />
                      </TableCell>
                      <TableCell>{memberRoleLabel(user)}</TableCell>
                      <TableCell>
                        <MemberStatusBadge isActive={user.is_active} />
                      </TableCell>
                      <TableCell className="text-body">
                        {user.last_login ? (
                          <FormattedTime value={user.last_login} />
                        ) : (
                          "Never"
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon-lg"
                            aria-label={`Edit ${memberName(user)}`}
                            onClick={() => setEditing(user)}
                          >
                            <Pencil />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon-lg"
                            aria-label={`${user.is_active ? "Deactivate" : "Reactivate"} ${memberName(user)}`}
                            title={user.is_active ? "Deactivate" : "Reactivate"}
                            onClick={() => void toggleActive(user)}
                          >
                            <Power />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon-lg"
                            aria-label={`Delete ${memberName(user)}`}
                            onClick={() => void onDelete(user)}
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
          totalCount={users.data?.count ?? 0}
          onPageChange={setPage}
          className="mt-4"
        />
      </QueryState>

      <AdminEditUserDialog user={editing} onClose={() => setEditing(null)} />
      {dialog}
    </div>
  );
}
