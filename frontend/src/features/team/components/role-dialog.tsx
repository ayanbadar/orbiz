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
import {
  usePermissionCatalog,
  useSaveRole,
} from "@/features/team/api/team.api";
import { PermissionMatrix } from "@/features/team/components/permission-matrix";
import type { Role } from "@/features/team/types";

const schema = z.object({
  name: z.string().trim().min(1, "Enter a role name").max(60),
  description: z.string().trim().max(200),
  permissions: z.array(z.string()).min(1, "Pick at least one permission"),
});
type Values = z.infer<typeof schema>;

/** Create (role === null && open) or edit a role. */
export function RoleDialog({
  open,
  role,
  onClose,
}: {
  open: boolean;
  role: Role | null;
  onClose: () => void;
}) {
  const catalog = usePermissionCatalog();
  const save = useSaveRole();
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", description: "", permissions: [] },
  });

  useEffect(() => {
    if (open) {
      form.reset({
        name: role?.name ?? "",
        description: role?.description ?? "",
        permissions: role?.permissions ?? [],
      });
    }
  }, [open, role, form]);

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      await save.mutateAsync({
        id: role?.id,
        body: {
          name: values.name.trim(),
          description: values.description.trim(),
          permissions: values.permissions,
        },
      });
      toast.success(role ? "Role updated." : "Role created.");
      onClose();
    } catch (error) {
      if (!applyFieldErrors(error, form.setError)) {
        toast.error(getErrorMessage(error, "Could not save the role."));
      }
    }
  });

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{role ? `Edit ${role.name}` : "New role"}</DialogTitle>
          <DialogDescription>
            Choose what people with this role can see and do. Changes apply
            immediately to everyone who has it.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          <FormField
            id="role-name"
            label="Name"
            error={form.formState.errors.name?.message}
          >
            <Input
              placeholder="e.g. Order packer"
              className="h-12 rounded-xl border-foreground bg-card px-4 text-base"
              {...form.register("name")}
            />
          </FormField>
          <FormField
            id="role-description"
            label="Description (optional)"
            error={form.formState.errors.description?.message}
          >
            <Input
              className="h-12 rounded-xl border-foreground bg-card px-4 text-base"
              {...form.register("description")}
            />
          </FormField>
          <div className="space-y-2">
            <p className="text-sm font-semibold">Permissions</p>
            {catalog.data ? (
              <Controller
                control={form.control}
                name="permissions"
                render={({ field }) => (
                  <PermissionMatrix
                    catalog={catalog.data}
                    value={field.value}
                    onChange={field.onChange}
                  />
                )}
              />
            ) : (
              <p className="text-sm text-muted-foreground" role="status">
                {catalog.isError ? "Could not load permissions." : "Loading…"}
              </p>
            )}
            {form.formState.errors.permissions ? (
              <p className="text-sm text-destructive" role="alert">
                {form.formState.errors.permissions.message}
              </p>
            ) : null}
          </div>
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
              disabled={save.isPending || !catalog.data}
              className="rounded-[24px] font-semibold"
            >
              {save.isPending ? "Saving…" : role ? "Save role" : "Create role"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
