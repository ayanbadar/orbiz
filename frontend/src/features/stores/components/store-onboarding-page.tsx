import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { Controller, useForm } from "react-hook-form";
import { Navigate, useNavigate } from "react-router-dom";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SearchableSelect } from "@/components/searchable-select";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "@/components/ui/sonner";
import { ROUTES } from "@/constants/routes";
import {
  applyFieldErrors,
  getErrorMessage,
} from "@/features/auth/utils/form-errors";
import {
  useCurrentStore,
  useUpdateStore,
} from "@/features/stores/api/stores.api";
import {
  detectTimezone,
  getCurrencyOptions,
  getTimezoneOptions,
} from "@/features/stores/utils/locale-options";

const CURRENCY_OPTIONS = getCurrencyOptions();
const TIMEZONE_OPTIONS = getTimezoneOptions();
const CURRENCY_CODES = new Set(CURRENCY_OPTIONS.map((o) => o.value));
const TIMEZONES = new Set(TIMEZONE_OPTIONS.map((o) => o.value));

const schema = z.object({
  name: z.string().trim().min(1, "Enter a store name."),
  currency: z
    .string()
    .refine((v) => CURRENCY_CODES.has(v), "Select a currency from the list."),
  timezone: z
    .string()
    .refine((v) => TIMEZONES.has(v), "Select a timezone from the list."),
  business_type: z.enum(["social", "storefront", "wholesale", "other"]),
});

type FormValues = z.infer<typeof schema>;

export function StoreOnboardingPage() {
  const navigate = useNavigate();
  const storeQuery = useCurrentStore();
  const store = storeQuery.data;
  const updateStore = useUpdateStore(store?.id);
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: "",
      currency: "USD",
      timezone: detectTimezone(TIMEZONE_OPTIONS),
      business_type: "social",
    },
  });

  useEffect(() => {
    if (!store) return;
    form.reset({
      name: store.name,
      currency: store.currency,
      timezone: store.timezone || form.getValues("timezone"),
      business_type: store.business_type,
    });
  }, [store, form]);

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      const saved = await updateStore.mutateAsync(values);
      toast.success("Store details saved.");
      // Unpaid stores continue to activation; paid ones go to work.
      navigate(
        saved.status === "pending_payment" ? ROUTES.billing() : ROUTES.root(),
        { replace: true },
      );
    } catch (error) {
      if (!applyFieldErrors(error, form.setError)) {
        toast.error(getErrorMessage(error, "Could not save store details."));
      }
    }
  });

  if (storeQuery.isLoading) {
    return (
      <p className="text-sm text-muted-foreground" role="status">
        Loading…
      </p>
    );
  }
  if (store && !store.is_store_admin) {
    return <Navigate to={ROUTES.root()} replace />;
  }

  return (
    <div className="mx-auto flex w-full max-w-lg flex-col gap-6">
      <header className="space-y-2">
        <h1 className="text-[32px] font-semibold tracking-tight text-foreground">
          Set up your store
        </h1>
        <p className="text-body">
          Confirm your currency and timezone. Next you&apos;ll activate the
          $5/month plan.
        </p>
      </header>

      <form
        onSubmit={onSubmit}
        className="space-y-4 rounded-[24px] bg-card p-6"
      >
        <div className="space-y-2">
          <Label htmlFor="name">Store name</Label>
          <Input
            id="name"
            {...form.register("name")}
            aria-invalid={!!form.formState.errors.name}
          />
          {form.formState.errors.name ? (
            <p className="text-sm text-destructive" role="alert">
              {form.formState.errors.name.message}
            </p>
          ) : null}
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <SearchableSelect
            id="currency"
            label="Currency"
            name="currency"
            control={form.control}
            options={CURRENCY_OPTIONS}
            placeholder="Search currency…"
            error={form.formState.errors.currency?.message}
          />
          <SearchableSelect
            id="timezone"
            label="Timezone"
            name="timezone"
            control={form.control}
            options={TIMEZONE_OPTIONS}
            placeholder="Search timezone…"
            error={form.formState.errors.timezone?.message}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="business_type">Business type</Label>
          <Controller
            control={form.control}
            name="business_type"
            render={({ field }) => (
              <Select value={field.value} onValueChange={field.onChange}>
                <SelectTrigger
                  id="business_type"
                  className="h-12 w-full min-w-0 rounded-[12px] px-3 text-sm"
                  aria-invalid={
                    Boolean(form.formState.errors.business_type) || undefined
                  }
                >
                  <SelectValue placeholder="Select business type…" />
                </SelectTrigger>
                <SelectContent position="popper" align="start">
                  <SelectItem value="social">Social commerce</SelectItem>
                  <SelectItem value="storefront">Online storefront</SelectItem>
                  <SelectItem value="wholesale">Wholesale</SelectItem>
                  <SelectItem value="other">Other</SelectItem>
                </SelectContent>
              </Select>
            )}
          />
          {form.formState.errors.business_type ? (
            <p className="text-sm text-destructive" role="alert">
              {form.formState.errors.business_type.message}
            </p>
          ) : null}
        </div>

        <Button
          type="submit"
          disabled={form.formState.isSubmitting || updateStore.isPending}
          className="h-12 rounded-[24px] px-6 font-semibold"
        >
          {updateStore.isPending ? "Saving…" : "Save and continue"}
        </Button>
      </form>
    </div>
  );
}
