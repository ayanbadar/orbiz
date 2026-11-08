import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
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
import { useInviteStoreAdmin } from "@/features/invitations/api/invitations.api";
import {
  applyFieldErrors,
  getErrorMessage,
} from "@/features/auth/utils/form-errors";
import { DevInviteLink } from "@/features/invitations/components/dev-invite-link";

const schema = z.object({
  email: z.email("Enter a valid email address"),
  storeName: z.string().trim().min(1, "Enter the store name"),
});
type Values = z.infer<typeof schema>;

export function InviteStoreAdminDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const invite = useInviteStoreAdmin();
  const [devLink, setDevLink] = useState<string | null>(null);
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", storeName: "" },
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
        store_name: values.storeName.trim(),
      });
      toast.success(`Invitation sent to ${invitation.email}.`);
      if (invitation.invite_url) {
        setDevLink(invitation.invite_url);
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

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Invite a store admin</DialogTitle>
          <DialogDescription>
            They&apos;ll set a password, set up the store, and pay the $5/month
            plan before it goes live.
          </DialogDescription>
        </DialogHeader>
        {devLink ? (
          <DevInviteLink url={devLink} onDone={() => close(false)} />
        ) : (
          <form onSubmit={onSubmit} className="space-y-4" noValidate>
            <FormField
              id="admin-email"
              label="Admin email"
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
              id="admin-store"
              label="Store name"
              error={form.formState.errors.storeName?.message}
            >
              <Input
                className="h-12 rounded-xl border-foreground bg-card px-4 text-base"
                {...form.register("storeName")}
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
                disabled={invite.isPending}
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
