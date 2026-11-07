import { zodResolver } from "@hookform/resolvers/zod";
import { useMemo } from "react";
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
import { useRefundPaypalOrder } from "@/features/payments/api/payments.api";

const MONEY_PATTERN = /^\d+(\.\d{1,2})?$/;

function toCents(value: string): number {
  return Math.round(Number(value) * 100);
}

function createRefundSchema(refundable: string, currency: string) {
  const maxCents = toCents(refundable);
  return z
    .object({
      mode: z.enum(["full", "partial"]),
      amount: z.string().trim(),
      note_to_payer: z
        .string()
        .trim()
        .max(255, "Keep the note under 255 characters."),
    })
    .refine(
      (values) =>
        values.mode === "full" ||
        (MONEY_PATTERN.test(values.amount) && toCents(values.amount) > 0),
      { path: ["amount"], message: "Enter a valid amount." },
    )
    .refine(
      (values) =>
        values.mode === "full" ||
        !MONEY_PATTERN.test(values.amount) ||
        toCents(values.amount) <= maxCents,
      {
        path: ["amount"],
        message: `You can refund up to ${currency} ${refundable}.`,
      },
    );
}

type RefundValues = z.infer<ReturnType<typeof createRefundSchema>>;

type FormProps = {
  order: Order;
  onDone: () => void;
};

function RefundForm({ order, onDone }: FormProps) {
  const refundOrder = useRefundPaypalOrder(order.id);
  const refundable = order.paypal_refundable_amount ?? "0.00";
  const schema = useMemo(
    () => createRefundSchema(refundable, order.currency),
    [refundable, order.currency],
  );
  const form = useForm<RefundValues>({
    resolver: zodResolver(schema),
    defaultValues: { mode: "full", amount: "", note_to_payer: "" },
  });
  const mode = useWatch({ control: form.control, name: "mode" });
  const amount = useWatch({ control: form.control, name: "amount" });
  const submitAmount =
    mode === "full"
      ? refundable
      : MONEY_PATTERN.test(amount.trim())
        ? Number(amount).toFixed(2)
        : "";

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      await refundOrder.mutateAsync({
        ...(values.mode === "partial" ? { amount: values.amount } : {}),
        note_to_payer: values.note_to_payer,
      });
      toast.success(
        `Refunded ${order.currency} ${submitAmount} via PayPal Sandbox.`,
      );
      onDone();
    } catch (error) {
      if (!applyFieldErrors(error, form.setError)) {
        toast.error(getErrorMessage(error, "Could not refund the payment."));
      }
    }
  });

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div className="flex flex-wrap gap-2" role="group" aria-label="Refund type">
        <Button
          type="button"
          variant={mode === "full" ? "default" : "outline"}
          aria-pressed={mode === "full"}
          className="rounded-[24px]"
          onClick={() => form.setValue("mode", "full", { shouldValidate: true })}
        >
          Full ({order.currency} {refundable})
        </Button>
        <Button
          type="button"
          variant={mode === "partial" ? "default" : "outline"}
          aria-pressed={mode === "partial"}
          className="rounded-[24px]"
          onClick={() =>
            form.setValue("mode", "partial", { shouldValidate: true })
          }
        >
          Partial
        </Button>
      </div>

      {mode === "partial" ? (
        <FormField
          id="refund-amount"
          label={`Amount (${order.currency})`}
          error={form.formState.errors.amount?.message}
        >
          <Input
            inputMode="decimal"
            placeholder="0.00"
            className={DIALOG_INPUT_CLASS}
            {...form.register("amount")}
          />
        </FormField>
      ) : null}

      <FormField
        id="refund-note"
        label="Note to buyer (optional)"
        error={form.formState.errors.note_to_payer?.message}
      >
        <Input
          placeholder="e.g. Item out of stock"
          className={DIALOG_INPUT_CLASS}
          {...form.register("note_to_payer")}
        />
      </FormField>

      <div className="flex justify-end gap-2">
        <DialogClose asChild>
          <Button type="button" variant="outline" className="rounded-[24px]">
            Cancel
          </Button>
        </DialogClose>
        <Button
          type="submit"
          disabled={refundOrder.isPending || !submitAmount}
          className="rounded-[24px]"
        >
          {refundOrder.isPending
            ? "Refunding…"
            : `Refund ${order.currency} ${submitAmount || "…"}`}
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

export function PaypalRefundDialog({ order, open, onOpenChange }: Props) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Refund via PayPal Sandbox</DialogTitle>
          <DialogDescription>
            Returns money to the buyer&apos;s Sandbox account. Fulfilment and
            stock are not changed — cancel the order separately if needed.
          </DialogDescription>
        </DialogHeader>
        <RefundForm order={order} onDone={() => onOpenChange(false)} />
      </DialogContent>
    </Dialog>
  );
}
