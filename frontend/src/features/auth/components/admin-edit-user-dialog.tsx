import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
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
import { useUpdateAdminUser } from "@/features/auth/api/admin-users.api";
import {
  applyFieldErrors,
  getErrorMessage,
} from "@/features/auth/utils/form-errors";
import type { Member } from "@/features/team/types";

const schema = z.object({
  firstName: z.string().trim().min(1, "Enter a first name"),
  lastName: z.string().trim(),
});
type Values = z.infer<typeof schema>;

export function AdminEditUserDialog({
  user,
  onClose,
}: {
  user: Member | null;
  onClose: () => void;
}) {
  const update = useUpdateAdminUser();
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { firstName: "", lastName: "" },
  });

  useEffect(() => {
    if (user)
      form.reset({ firstName: user.first_name, lastName: user.last_name });
  }, [user, form]);

  const onSubmit = form.handleSubmit(async (values) => {
    if (!user) return;
    try {
      await update.mutateAsync({
        id: user.id,
        body: {
          first_name: values.firstName.trim(),
          last_name: values.lastName.trim(),
        },
      });
      toast.success("User updated.");
      onClose();
    } catch (error) {
      if (!applyFieldErrors(error, form.setError)) {
        toast.error(getErrorMessage(error, "Could not update the user."));
      }
    }
  });

  return (
    <Dialog open={user != null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Edit user</DialogTitle>
          <DialogDescription>{user?.email}</DialogDescription>
        </DialogHeader>
        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              id="admin-first"
              label="First name"
              error={form.formState.errors.firstName?.message}
            >
              <Input
                className="h-12 rounded-xl border-foreground bg-card px-4 text-base"
                {...form.register("firstName")}
              />
            </FormField>
            <FormField
              id="admin-last"
              label="Last name"
              error={form.formState.errors.lastName?.message}
            >
              <Input
                className="h-12 rounded-xl border-foreground bg-card px-4 text-base"
                {...form.register("lastName")}
              />
            </FormField>
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
