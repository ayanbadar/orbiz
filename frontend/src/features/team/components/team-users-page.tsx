import { Pencil, Power, Trash2, UserPlus } from "lucide-react";
import { useState } from "react";

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
import { Can } from "@/features/auth/components/can";
import { useAuth } from "@/features/auth/context/use-auth";
import { getErrorMessage } from "@/features/auth/utils/form-errors";
import {
  useRevokeStaffInvitation,
  useStaffInvitations,
} from "@/features/invitations/api/invitations.api";
import { InviteMemberDialog } from "@/features/invitations/components/invite-member-dialog";
import { PendingInvitationsCard } from "@/features/invitations/components/pending-invitations-card";
import {
  useDeleteMember,
  useTeamUsers,
  useUpdateMember,
} from "@/features/team/api/team.api";
import { EditMemberDialog } from "@/features/team/components/edit-member-dialog";
import { MemberStatusBadge } from "@/features/team/components/member-status-badge";
import type { Member } from "@/features/team/types";
import { memberName, memberRoleLabel } from "@/features/team/utils/member";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { usePermissions } from "@/features/auth/hooks/use-permissions";

export function TeamUsersPage() {
  const { user } = useAuth();
  const { can } = usePermissions();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [editing, setEditing] = useState<Member | null>(null);
  const debouncedSearch = useDebouncedValue(search.trim());
  const users = useTeamUsers({ page, search: debouncedSearch });
  const invitations = useStaffInvitations({ enabled: can("users.read") });
  const update = useUpdateMember();
  const remove = useDeleteMember();
  const revoke = useRevokeStaffInvitation();
  const { confirm, dialog } = useConfirmDialog();

  const rows = users.data?.results ?? [];

  const toggleActive = async (member: Member) => {
    const deactivating = member.is_active;
    if (deactivating) {
      const ok = await confirm({
        title: `Deactivate ${memberName(member)}?`,
        description:
          "They'll be signed out and won't be able to use the store until you reactivate them.",
        confirmLabel: "Deactivate",
        variant: "destructive",
      });
      if (!ok) return;
    }
    try {
      await update.mutateAsync({
        id: member.id,
        body: { is_active: !deactivating },
      });
      toast.success(
        deactivating ? "Member deactivated." : "Member reactivated.",
      );
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not update the member."));
    }
  };

  const onDelete = async (member: Member) => {
    const ok = await confirm({
      title: `Delete ${memberName(member)}?`,
      description:
        "This permanently removes their account. This can't be undone.",
      confirmLabel: "Delete",
      variant: "destructive",
    });
    if (!ok) return;
    try {
      await remove.mutateAsync(member.id);
      toast.success("Member deleted.");
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not delete the member."));
    }
  };

  const onRevoke = async (id: number) => {
    try {
      await revoke.mutateAsync(id);
      toast.success("Invitation revoked.");
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not revoke the invitation."));
    }
  };

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-[28px] font-semibold tracking-tight sm:text-[32px]">
            Team
          </h1>
          <p className="text-body">
            People who can sign in to this store, and what they can do.
          </p>
        </div>
        <Can permission="users.create">
          <Button
            className="h-12 rounded-[24px] px-6 font-semibold"
            onClick={() => setInviteOpen(true)}
          >
            <UserPlus aria-hidden /> Invite member
          </Button>
        </Can>
      </header>

      <Input
        value={search}
        placeholder="Search by name or email"
        className="h-9 w-full max-w-sm rounded-lg bg-card"
        onChange={(event) => {
          setSearch(event.target.value);
          setPage(1);
        }}
      />

      <QueryState
        isLoading={users.isLoading}
        isError={users.isError}
        errorMessage="Could not load the team."
        onRetry={() => void users.refetch()}
      >
        <Card className="gap-0 overflow-hidden rounded-[24px] py-0 ring-0">
          <CardContent className="p-0">
            {rows.length === 0 ? (
              <p className="px-6 py-10 text-center text-sm text-muted-foreground">
                {debouncedSearch
                  ? "No one matches that search."
                  : "No team members yet."}
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead>Member</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Last sign-in</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((member) => {
                    const locked =
                      member.is_store_admin || member.id === user?.id;
                    return (
                      <TableRow key={member.id}>
                        <TableCell>
                          <p className="font-semibold">{memberName(member)}</p>
                          <p className="text-xs text-muted-foreground">
                            {member.email}
                          </p>
                        </TableCell>
                        <TableCell>{memberRoleLabel(member)}</TableCell>
                        <TableCell>
                          <MemberStatusBadge isActive={member.is_active} />
                        </TableCell>
                        <TableCell className="text-body">
                          {member.last_login ? (
                            <FormattedTime value={member.last_login} />
                          ) : (
                            "Never"
                          )}
                        </TableCell>
                        <TableCell>
                          <div className="flex justify-end gap-1">
                            {locked ? (
                              <span className="px-2 text-xs text-muted-foreground">
                                {member.id === user?.id ? "You" : "Owner"}
                              </span>
                            ) : (
                              <>
                                <Can permission="users.update">
                                  <Button
                                    variant="ghost"
                                    size="icon-lg"
                                    aria-label={`Edit ${memberName(member)}`}
                                    onClick={() => setEditing(member)}
                                  >
                                    <Pencil />
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="icon-lg"
                                    aria-label={`${member.is_active ? "Deactivate" : "Reactivate"} ${memberName(member)}`}
                                    title={
                                      member.is_active
                                        ? "Deactivate"
                                        : "Reactivate"
                                    }
                                    onClick={() => void toggleActive(member)}
                                  >
                                    <Power />
                                  </Button>
                                </Can>
                                <Can permission="users.delete">
                                  <Button
                                    variant="ghost"
                                    size="icon-lg"
                                    aria-label={`Delete ${memberName(member)}`}
                                    onClick={() => void onDelete(member)}
                                  >
                                    <Trash2 />
                                  </Button>
                                </Can>
                              </>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
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

      <PendingInvitationsCard
        title="Pending invitations"
        invitations={invitations.data ?? []}
        badge={(invitation) => invitation.role_name ?? "Invited"}
        onRevoke={
          can("users.delete")
            ? (invitation) => void onRevoke(invitation.id)
            : undefined
        }
      />

      <InviteMemberDialog open={inviteOpen} onOpenChange={setInviteOpen} />
      <EditMemberDialog member={editing} onClose={() => setEditing(null)} />
      {dialog}
    </div>
  );
}
