import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import { z } from "zod";

import { FormField } from "@/components/form-field";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { toast } from "@/components/ui/sonner";
import { ROUTES } from "@/constants/routes";
import {
  applyFieldErrors,
  getErrorMessage,
} from "@/features/auth/utils/form-errors";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { useInviteStaff } from "@/features/invitations/api/invitations.api";
import { useRoles } from "@/features/team/api/team.api";
import { DevInviteLink } from "@/features/invitations/components/dev-invite-link";
import { RoleSelect } from "@/features/team/components/role-select";

const schema = z.object({
  email: z.email("Enter a valid email address"),
  roleId: z.string().min(1, "Choose a role"),
});
type Values = z.infer<typeof schema>;

export function InviteMemberDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const roles = useRoles({ enabled: open });
  const invite = useInviteStaff();
  const { isStoreAdmin } = usePermissions();
  const [devLink, setDevLink] = useState<string | null>(null);
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", roleId: "" },
  });

  const close = (next: boolean) => {
    if (!next) {
      form.reset();
      setDevLink(null);
    }
    onOpenChange(next);
  };

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      const invitation = await invite.mutateAsync({
        email: values.email.trim().toLowerCase(),
        role_id: Number(values.roleId),
      });
      toast.success(`Invitation sent to ${invitation.email}.`);
      if (invitation.invite_url) {
        setDevLink(invitation.invite_url); // dev only: the console is the inbox
        form.reset();
      } else {
        close(false);
      }
    } catch (error) {
      if (!applyFieldErrors(error, form.setError)) {
        toast.error(getErrorMessage(error, "Could not send the invitation."));
      }
    }
  });

  const noRoles = roles.isSuccess && roles.data.length === 0;

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Invite a team member</DialogTitle>
          <DialogDescription>
            They get an email link to set a password. Their role decides what
            they can see and do.
          </DialogDescription>
        </DialogHeader>

        {devLink ? (
          <DevInviteLink url={devLink} onDone={() => close(false)} />
        ) : noRoles ? (
          <div className="space-y-3">
            <p className="text-sm text-body">
              {isStoreAdmin
                ? "Create at least one role before inviting people."
                : "There are no roles you can assign yet. Ask your store admin."}
            </p>
            {isStoreAdmin ? (
              <Button asChild className="rounded-[24px]">
                <Link to={ROUTES.team.roles()}>Create a role</Link>
              </Button>
            ) : null}
          </div>
        ) : (
          <form onSubmit={onSubmit} className="space-y-4" noValidate>
            <FormField
              id="invite-email"
              label="Email"
              error={form.formState.errors.email?.message}
            >
              <Input
                type="email"
                autoComplete="off"
                className="h-12 rounded-xl border-foreground bg-card px-4 text-base"
                {...form.register("email")}
              />
            </FormField>
            <FormField
              id="invite-role"
              label="Role"
              error={form.formState.errors.roleId?.message}
            >
              <Controller
                control={form.control}
                name="roleId"
                render={({ field }) => (
                  <RoleSelect
                    id="invite-role"
                    roles={roles.data ?? []}
                    value={field.value}
                    onChange={field.onChange}
                    invalid={Boolean(form.formState.errors.roleId)}
                  />
                )}
              />
            </FormField>
            <div className="flex justify-end gap-2">
              <Button
                type="button"
                variant="secondary"
                className="rounded-[24px]"
                onClick={() => close(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={invite.isPending || roles.isLoading}
                className="rounded-[24px] font-semibold"
              >
                {invite.isPending ? "Sending…" : "Send invitation"}
              </Button>
            </div>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
