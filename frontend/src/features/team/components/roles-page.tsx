import { Pencil, Plus, Trash2 } from "lucide-react";
import { useState } from "react";

import { useConfirmDialog } from "@/components/confirm-dialog";
import { QueryState } from "@/components/query-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { toast } from "@/components/ui/sonner";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getErrorMessage } from "@/features/auth/utils/form-errors";
import {
  useDeleteRole,
  usePermissionCatalog,
  useRoles,
} from "@/features/team/api/team.api";
import { RoleDialog } from "@/features/team/components/role-dialog";
import type { PermissionCatalog, Role } from "@/features/team/types";

function summarize(role: Role, catalog: PermissionCatalog | undefined): string {
  if (!catalog) return `${role.permissions.length} permissions`;
  const parts = catalog.resources
    .map((resource) => {
      const actions = catalog.actions
        .filter((action) =>
          role.permissions.includes(`${resource.key}.${action.key}`),
        )
        .map((action) => action.label.toLowerCase());
      return actions.length ? `${resource.label}: ${actions.join(", ")}` : null;
    })
    .filter(Boolean);
  return parts.join(" · ") || "No access";
}

export function RolesPage() {
  const roles = useRoles();
  const catalog = usePermissionCatalog();
  const remove = useDeleteRole();
  const { confirm, dialog } = useConfirmDialog();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Role | null>(null);

  const openCreate = () => {
    setEditing(null);
    setDialogOpen(true);
  };
  const openEdit = (role: Role) => {
    setEditing(role);
    setDialogOpen(true);
  };

  const onDelete = async (role: Role) => {
    const ok = await confirm({
      title: `Delete the ${role.name} role?`,
      description: "Roles that are still assigned to people can't be deleted.",
      confirmLabel: "Delete",
      variant: "destructive",
    });
    if (!ok) return;
    try {
      await remove.mutateAsync(role.id);
      toast.success("Role deleted.");
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not delete the role."));
    }
  };

  const rows = roles.data ?? [];

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-[28px] font-semibold tracking-tight sm:text-[32px]">
            Roles
          </h1>
          <p className="text-body">
            Roles decide what your team can view, create, edit and delete.
          </p>
        </div>
        <Button
          className="h-12 rounded-[24px] px-6 font-semibold"
          onClick={openCreate}
        >
          <Plus aria-hidden /> New role
        </Button>
      </header>

      <QueryState
        isLoading={roles.isLoading}
        isError={roles.isError}
        errorMessage="Could not load roles."
        onRetry={() => void roles.refetch()}
      >
        <Card className="gap-0 overflow-hidden rounded-[24px] py-0 ring-0">
          <CardContent className="p-0">
            {rows.length === 0 ? (
              <div className="space-y-3 px-6 py-12 text-center">
                <p className="font-semibold">No roles yet</p>
                <p className="text-sm text-body">
                  Create a role, then assign it when you invite someone.
                </p>
                <Button className="rounded-[24px]" onClick={openCreate}>
                  Create your first role
                </Button>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead>Role</TableHead>
                    <TableHead>Access</TableHead>
                    <TableHead>People</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((role) => (
                    <TableRow key={role.id}>
                      <TableCell>
                        <p className="font-semibold">{role.name}</p>
                        {role.description ? (
                          <p className="text-xs text-muted-foreground">
                            {role.description}
                          </p>
                        ) : null}
                      </TableCell>
                      <TableCell className="max-w-md text-body">
                        {summarize(role, catalog.data)}
                      </TableCell>
                      <TableCell>{role.member_count}</TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon-lg"
                            aria-label={`Edit ${role.name}`}
                            onClick={() => openEdit(role)}
                          >
                            <Pencil />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon-lg"
                            aria-label={`Delete ${role.name}`}
                            onClick={() => void onDelete(role)}
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
      </QueryState>

      <RoleDialog
        open={dialogOpen}
        role={editing}
        onClose={() => setDialogOpen(false)}
      />
      {dialog}
    </div>
  );
}
