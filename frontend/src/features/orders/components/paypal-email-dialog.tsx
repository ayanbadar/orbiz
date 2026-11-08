import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { FormField } from "@/components/form-field";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
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
import { DIALOG_INPUT_CLASS } from "@/features/orders/components/paypal-card-styles";
import type { Order } from "@/features/orders/types";
import { useEmailPaymentLink } from "@/features/payments/api/payments.api";
import type { EmailLinkKind } from "@/features/payments/types";

const emailSchema = z.object({
  recipient_email: z
    .string()
    .trim()
    .min(1, "Enter an email address.")
    .refine(
      (value) => z.email().safeParse(value).success,
      "Enter a valid email address.",
    ),
});

type EmailValues = z.infer<typeof emailSchema>;

const COPY: Record<
  EmailLinkKind,
  { title: string; submit: string; queued: string }
> = {
  request: {
    title: "Email payment link",
    submit: "Send email",
    queued: "Payment email queued for",
  },
  reminder: {
    title: "Send payment reminder",
    submit: "Send reminder",
    queued: "Reminder queued for",
  },
};

type FormProps = {
  order: Order;
  kind: EmailLinkKind;
  onDone: () => void;
};

function EmailForm({ order, kind, onDone }: FormProps) {
  const emailLink = useEmailPaymentLink(order.id);
  const form = useForm<EmailValues>({
    resolver: zodResolver(emailSchema),
    defaultValues: {
      recipient_email:
        order.paypal_payment_request?.recipient_email ||
        order.customer.email ||
        "",
    },
  });
  const copy = COPY[kind];

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      await emailLink.mutateAsync({
        recipient_email: values.recipient_email,
        kind,
      });
      toast.success(`${copy.queued} ${values.recipient_email}.`);
      onDone();
    } catch (error) {
      if (!applyFieldErrors(error, form.setError)) {
        toast.error(getErrorMessage(error, "Could not send the email."));
      }
    }
  });

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <FormField
        id="payment-email"
        label="Send to"
        error={form.formState.errors.recipient_email?.message}
      >
        <Input
          type="email"
          autoComplete="off"
          placeholder="buyer@example.com"
          className={DIALOG_INPUT_CLASS}
          {...form.register("recipient_email")}
        />
      </FormField>
      <p className="text-sm text-muted-foreground">
        The buyer gets one email with a button to pay on PayPal. They don&apos;t
        need an Orbiz account, and replies come to you.
        {order.paypal_sandbox
          ? " The email says this is a PayPal Sandbox payment and no real money moves."
          : ""}
      </p>
      <div className="flex justify-end gap-2">
        <DialogClose asChild>
          <Button type="button" variant="outline" className="rounded-[24px]">
            Cancel
          </Button>
        </DialogClose>
        <Button
          type="submit"
          disabled={emailLink.isPending}
          className="rounded-[24px]"
        >
          {emailLink.isPending ? "Sending…" : copy.submit}
        </Button>
      </div>
    </form>
  );
}

type Props = {
  order: Order;
  kind: EmailLinkKind;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export function PaypalEmailDialog({ order, kind, open, onOpenChange }: Props) {
  const request = order.paypal_payment_request;
  const what =
    request?.kind === "invoice"
      ? "PayPal invoice link"
      : "PayPal checkout link";
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{COPY[kind].title}</DialogTitle>
          <DialogDescription>
            Emails the {what} for {order.number} ({order.currency} {order.total}
            ).
          </DialogDescription>
        </DialogHeader>
        <EmailForm
          order={order}
          kind={kind}
          onDone={() => onOpenChange(false)}
        />
      </DialogContent>
    </Dialog>
  );
}
