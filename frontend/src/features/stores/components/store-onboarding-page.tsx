import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "@/components/ui/sonner";
import { ROUTES } from "@/constants/routes";
import {
  applyFieldErrors,
  getErrorMessage,
} from "@/features/auth/utils/form-errors";
import { useCreateStore } from "@/features/stores/api/stores.api";

const schema = z.object({
  name: z.string().trim().min(1, "Enter a store name."),
  currency: z
    .string()
    .trim()
    .toUpperCase()
    .regex(/^[A-Z]{3}$/, "Use a 3-letter currency code."),
  timezone: z.string().trim().min(1, "Enter a timezone."),
  business_type: z.enum(["social", "storefront", "wholesale", "other"]),
});

type FormValues = z.infer<typeof schema>;

export function StoreOnboardingPage() {
  const navigate = useNavigate();
  const createStore = useCreateStore();
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: "",
      currency: "USD",
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
      business_type: "social",
    },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      await createStore.mutateAsync(values);
      toast.success("Store workspace created.");
      navigate(ROUTES.products.root(), { replace: true });
    } catch (error) {
      if (!applyFieldErrors(error, form.setError)) {
        toast.error(getErrorMessage(error, "Could not create store."));
      }
    }
  });

  return (
    <div className="mx-auto flex w-full max-w-lg flex-col gap-6">
      <header className="space-y-2">
        <h1 className="text-[32px] font-semibold tracking-tight text-foreground">
          Create your store
        </h1>
        <p className="text-body">
          Set up a workspace with currency and timezone before adding products.
        </p>
      </header>

      <form onSubmit={onSubmit} className="space-y-4 rounded-[24px] bg-card p-6">
        <div className="space-y-2">
          <Label htmlFor="name">Store name</Label>
          <Input id="name" {...form.register("name")} aria-invalid={!!form.formState.errors.name} />
          {form.formState.errors.name ? (
            <p className="text-sm text-destructive" role="alert">
              {form.formState.errors.name.message}
            </p>
          ) : null}
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="currency">Currency</Label>
            <Input id="currency" {...form.register("currency")} />
            {form.formState.errors.currency ? (
              <p className="text-sm text-destructive" role="alert">
                {form.formState.errors.currency.message}
              </p>
            ) : null}
          </div>
          <div className="space-y-2">
            <Label htmlFor="timezone">Timezone</Label>
            <Input id="timezone" {...form.register("timezone")} />
            {form.formState.errors.timezone ? (
              <p className="text-sm text-destructive" role="alert">
                {form.formState.errors.timezone.message}
              </p>
            ) : null}
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="business_type">Business type</Label>
          <select
            id="business_type"
            className="flex h-12 w-full rounded-[12px] border border-input bg-transparent px-3 text-sm"
            {...form.register("business_type")}
          >
            <option value="social">Social commerce</option>
            <option value="storefront">Online storefront</option>
            <option value="wholesale">Wholesale</option>
            <option value="other">Other</option>
          </select>
        </div>

        <Button
          type="submit"
          disabled={form.formState.isSubmitting || createStore.isPending}
          className="h-12 rounded-[24px] px-6 font-semibold"
        >
          {createStore.isPending ? "Creating…" : "Create store"}
        </Button>
      </form>
    </div>
  );
}
