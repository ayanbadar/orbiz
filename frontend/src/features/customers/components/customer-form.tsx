import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import { FormField } from "@/components/form-field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "@/components/ui/sonner";
import { Textarea } from "@/components/ui/textarea";
import {
  applyFieldErrors,
  getErrorMessage,
} from "@/features/auth/utils/form-errors";
import {
  customerFormSchema,
  EMPTY_CUSTOMER_FORM,
  type CustomerFormValues,
} from "@/features/customers/utils/customer-form-schema";
import { DIALOG_INPUT_CLASS } from "@/features/orders/components/paypal-card-styles";

type Props = {
  defaultValues?: Partial<CustomerFormValues>;
  submitLabel: string;
  /** Persist the values; throw the API error to show it on the form. */
  onSubmit: (values: CustomerFormValues) => Promise<void>;
  /** Shown beside submit when set (e.g. Cancel inside a dialog). */
  onCancel?: () => void;
};

/**
 * Customer fields + validation + server-error handling. Values stay on the
 * form after a failed save so the seller can correct and retry.
 */
export function CustomerForm({
  defaultValues,
  submitLabel,
  onSubmit,
  onCancel,
}: Props) {
  const form = useForm<CustomerFormValues>({
    resolver: zodResolver(customerFormSchema),
    defaultValues: { ...EMPTY_CUSTOMER_FORM, ...defaultValues },
  });
  const { errors, isSubmitting } = form.formState;

  const submit = form.handleSubmit(async (values) => {
    try {
      await onSubmit(values);
    } catch (error) {
      if (!applyFieldErrors(error, form.setError)) {
        toast.error(getErrorMessage(error, "Could not save the customer."));
      }
    }
  });

  return (
    <form onSubmit={submit} className="space-y-4" noValidate>
      <FormField id="customer-name" label="Name" error={errors.name?.message}>
        <Input
          autoComplete="off"
          className={DIALOG_INPUT_CLASS}
          {...form.register("name")}
        />
      </FormField>
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField
          id="customer-email"
          label="Email"
          error={errors.email?.message}
        >
          <Input
            type="email"
            autoComplete="off"
            placeholder="buyer@example.com"
            className={DIALOG_INPUT_CLASS}
            {...form.register("email")}
          />
        </FormField>
        <FormField
          id="customer-phone"
          label="Phone"
          error={errors.phone?.message}
        >
          <Input
            type="tel"
            autoComplete="off"
            placeholder="+92 300 1234567"
            className={DIALOG_INPUT_CLASS}
            {...form.register("phone")}
          />
        </FormField>
      </div>
      <p className="text-xs text-muted-foreground">
        Add an email to send PayPal payment links and order confirmations.
      </p>
      <FormField
        id="customer-notes"
        label="Internal notes"
        error={errors.notes?.message}
      >
        <Textarea
          rows={3}
          placeholder="Sizes, delivery preferences… only your team sees this."
          className="rounded-xl border-foreground bg-card px-4 py-3 text-base"
          {...form.register("notes")}
        />
      </FormField>
      <div className="flex flex-wrap justify-end gap-2">
        {onCancel ? (
          <Button
            type="button"
            variant="outline"
            size="cta"
            onClick={onCancel}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
        ) : null}
        <Button type="submit" size="cta" disabled={isSubmitting}>
          {isSubmitting ? "Saving…" : submitLabel}
        </Button>
      </div>
    </form>
  );
}
