import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { Controller, useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import { z } from "zod";

import { FormField } from "@/components/form-field";
import { QueryState } from "@/components/query-state";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
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
import { ApiError } from "@/lib/api";

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

const inputClassName =
  "h-12 rounded-xl border-foreground bg-card px-4 text-base";

const selectTriggerClassName =
  "h-12 w-full min-w-0 rounded-xl border-foreground bg-card px-3 text-base";

/** Account workspace card — view/edit the current default store. */
export function WorkspaceCard() {
  const storeQuery = useCurrentStore();
  const store = storeQuery.data;
  const updateStore = useUpdateStore(store?.id);
  const missingStore =
    storeQuery.isError &&
    storeQuery.error instanceof ApiError &&
    storeQuery.error.status === 404;
  const canEdit = store?.role === "owner";

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: "",
      currency: "USD",
      timezone: "UTC",
      business_type: "social",
    },
  });

  useEffect(() => {
    if (!store) {
      return;
    }
    form.reset({
      name: store.name,
      currency: store.currency,
      timezone: store.timezone,
      business_type: store.business_type,
    });
  }, [store, form]);

  const onSave = form.handleSubmit(async (values) => {
    try {
      await updateStore.mutateAsync(values);
      toast.success("Workspace saved.");
    } catch (error) {
      if (!applyFieldErrors(error, form.setError)) {
        toast.error(getErrorMessage(error, "Could not save workspace."));
      }
    }
  });

  return (
    <Card className="rounded-[24px] bg-card py-0 ring-0">
      <CardHeader className="px-6 pt-6">
        <CardTitle className="text-xl font-semibold">Workspace</CardTitle>
        <CardDescription>
          Store name, currency, and timezone used across products and orders.
        </CardDescription>
      </CardHeader>
      <CardContent className="px-6 pb-6">
        {missingStore ? (
          <div className="space-y-4">
            <p className="text-sm text-body">
              You do not have a store workspace yet.
            </p>
            <Button asChild className="h-12 rounded-[24px] px-6 font-semibold">
              <Link to={ROUTES.stores.onboarding()}>Create store</Link>
            </Button>
          </div>
        ) : (
          <QueryState
            isLoading={storeQuery.isLoading}
            isError={storeQuery.isError}
            errorMessage={
              storeQuery.error instanceof Error
                ? storeQuery.error.message
                : "Failed to load workspace."
            }
            onRetry={() => {
              void storeQuery.refetch();
            }}
          >
            {store ? (
              <form className="space-y-4" onSubmit={onSave} noValidate>
                <FormField
                  id="workspace-name"
                  label="Store name"
                  error={form.formState.errors.name?.message}
                >
                  <Input
                    className={inputClassName}
                    disabled={!canEdit}
                    {...form.register("name")}
                  />
                </FormField>
                <div className="grid gap-4 sm:grid-cols-2">
                  <FormField
                    id="workspace-currency"
                    label="Currency"
                    error={form.formState.errors.currency?.message}
                  >
                    <Input
                      className={inputClassName}
                      disabled={!canEdit}
                      {...form.register("currency")}
                    />
                  </FormField>
                  <FormField
                    id="workspace-timezone"
                    label="Timezone"
                    error={form.formState.errors.timezone?.message}
                  >
                    <Input
                      className={inputClassName}
                      disabled={!canEdit}
                      {...form.register("timezone")}
                    />
                  </FormField>
                </div>
                <FormField
                  id="workspace-business-type"
                  label="Business type"
                  error={form.formState.errors.business_type?.message}
                >
                  <Controller
                    control={form.control}
                    name="business_type"
                    render={({ field }) => (
                      <Select
                        value={field.value}
                        onValueChange={field.onChange}
                        disabled={!canEdit}
                      >
                        <SelectTrigger
                          id="workspace-business-type"
                          className={selectTriggerClassName}
                          aria-invalid={
                            Boolean(form.formState.errors.business_type) ||
                            undefined
                          }
                          aria-describedby={
                            form.formState.errors.business_type
                              ? "workspace-business-type-error"
                              : undefined
                          }
                        >
                          <SelectValue placeholder="Select business type…" />
                        </SelectTrigger>
                        <SelectContent position="popper" align="start">
                          <SelectItem value="social">Social commerce</SelectItem>
                          <SelectItem value="storefront">
                            Online storefront
                          </SelectItem>
                          <SelectItem value="wholesale">Wholesale</SelectItem>
                          <SelectItem value="other">Other</SelectItem>
                        </SelectContent>
                      </Select>
                    )}
                  />
                </FormField>
                {!canEdit ? (
                  <p className="text-sm text-muted-foreground">
                    Only store owners can edit workspace settings.
                  </p>
                ) : (
                  <Button
                    type="submit"
                    disabled={
                      form.formState.isSubmitting || updateStore.isPending
                    }
                    className="h-12 rounded-[24px] px-6 font-semibold"
                  >
                    {updateStore.isPending ? "Saving…" : "Save workspace"}
                  </Button>
                )}
              </form>
            ) : null}
          </QueryState>
        )}
      </CardContent>
    </Card>
  );
}
