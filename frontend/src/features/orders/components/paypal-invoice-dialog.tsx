import { zodResolver } from "@hookform/resolvers/zod";
import { useForm, useWatch } from "react-hook-form";
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
import { useSendPaypalInvoice } from "@/features/payments/api/payments.api";

const invoiceSchema = z.object({
  recipient_email: z
    .string()
    .trim()
    .refine(
      (value) => value === "" || z.email().safeParse(value).success,
      "Enter a valid email address.",
    ),
});

type InvoiceValues = z.infer<typeof invoiceSchema>;

type FormProps = {
  order: Order;
  onDone: () => void;
};

function InvoiceForm({ order, onDone }: FormProps) {
  const sendInvoice = useSendPaypalInvoice(order.id);
  const form = useForm<InvoiceValues>({
    resolver: zodResolver(invoiceSchema),
    defaultValues: { recipient_email: order.customer.email ?? "" },
  });
  const email = useWatch({ control: form.control, name: "recipient_email" }).trim();

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      await sendInvoice.mutateAsync({ recipient_email: values.recipient_email });
      toast.success(
        values.recipient_email
          ? `PayPal Sandbox invoice sent to ${values.recipient_email}.`
          : "PayPal Sandbox invoice link created.",
      );
      onDone();
    } catch (error) {
      if (!applyFieldErrors(error, form.setError)) {
        toast.error(getErrorMessage(error, "Could not send the PayPal invoice."));
      }
    }
  });

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <FormField
        id="invoice-email"
        label="Send invoice to"
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
        {email
          ? "PayPal emails the buyer an invoice they can pay on PayPal."
          : "No email: PayPal creates a payable link and nothing is emailed. You can copy and share it."}{" "}
        In Sandbox, PayPal never sends real email — use a Sandbox buyer email
        (sb-…@personal.example.com). The email may not show in PayPal&apos;s
        Sandbox Notifications; the invoice link always works.
      </p>
      <div className="flex justify-end gap-2">
        <DialogClose asChild>
          <Button type="button" variant="outline" className="rounded-[24px]">
            Cancel
          </Button>
        </DialogClose>
        <Button
          type="submit"
          disabled={sendInvoice.isPending}
          className="rounded-[24px]"
        >
          {sendInvoice.isPending
            ? "Sending…"
            : email
              ? "Send invoice"
              : "Create invoice link"}
        </Button>
      </div>
    </form>
  );
}

type Props = {
  order: Order;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export function PaypalInvoiceDialog({ order, open, onOpenChange }: Props) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Send PayPal Sandbox invoice</DialogTitle>
          <DialogDescription>
            Invoices {order.currency} {order.total} for {order.number}. Starting
            an invoice cancels any open checkout link for this order.
          </DialogDescription>
        </DialogHeader>
        <InvoiceForm order={order} onDone={() => onOpenChange(false)} />
      </DialogContent>
    </Dialog>
  );
}
