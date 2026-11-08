import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { Controller, useForm } from "react-hook-form";
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
import {
  applyFieldErrors,
  getErrorMessage,
} from "@/features/auth/utils/form-errors";
import { useRoles, useUpdateMember } from "@/features/team/api/team.api";
import { RoleSelect } from "@/features/team/components/role-select";
import type { Member } from "@/features/team/types";

const schema = z.object({
  firstName: z.string().trim().min(1, "Enter a first name"),
  lastName: z.string().trim(),
  roleId: z.string().min(1, "Choose a role"),
});
type Values = z.infer<typeof schema>;

export function EditMemberDialog({
  member,
  onClose,
}: {
  member: Member | null;
  onClose: () => void;
}) {
  const roles = useRoles({ enabled: member != null });
  const update = useUpdateMember();
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { firstName: "", lastName: "", roleId: "" },
  });

  useEffect(() => {
    if (member) {
      form.reset({
        firstName: member.first_name,
        lastName: member.last_name,
        roleId: member.role ? String(member.role.id) : "",
      });
    }
  }, [member, form]);

  const onSubmit = form.handleSubmit(async (values) => {
    if (!member) return;
    try {
      await update.mutateAsync({
        id: member.id,
        body: {
          first_name: values.firstName.trim(),
          last_name: values.lastName.trim(),
          role_id: Number(values.roleId),
        },
      });
      toast.success("Member updated.");
      onClose();
    } catch (error) {
      if (!applyFieldErrors(error, form.setError)) {
        toast.error(getErrorMessage(error, "Could not update the member."));
      }
    }
  });

  return (
    <Dialog open={member != null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Edit member</DialogTitle>
          <DialogDescription>{member?.email}</DialogDescription>
        </DialogHeader>
        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              id="edit-first"
              label="First name"
              error={form.formState.errors.firstName?.message}
            >
              <Input
                className="h-12 rounded-xl border-foreground bg-card px-4 text-base"
                {...form.register("firstName")}
              />
            </FormField>
            <FormField
              id="edit-last"
              label="Last name"
              error={form.formState.errors.lastName?.message}
            >
              <Input
                className="h-12 rounded-xl border-foreground bg-card px-4 text-base"
                {...form.register("lastName")}
              />
            </FormField>
          </div>
          <FormField
            id="edit-role"
            label="Role"
            error={form.formState.errors.roleId?.message}
          >
            <Controller
              control={form.control}
              name="roleId"
              render={({ field }) => (
                <RoleSelect
                  id="edit-role"
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
              onClick={onClose}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={update.isPending}
              className="rounded-[24px] font-semibold"
            >
              {update.isPending ? "Saving…" : "Save changes"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
