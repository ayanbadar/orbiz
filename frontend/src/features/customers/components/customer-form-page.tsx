import { useNavigate, useParams } from "react-router-dom";

import { PageBackLink } from "@/components/page-back-link";
import { QueryState } from "@/components/query-state";
import { toast } from "@/components/ui/sonner";
import { ROUTES } from "@/constants/routes";
import { getErrorMessage } from "@/features/auth/utils/form-errors";
import {
  useCreateCustomer,
  useCustomer,
  useUpdateCustomer,
} from "@/features/customers/api/customers.api";
import { CustomerForm } from "@/features/customers/components/customer-form";
import type { CustomerFormValues } from "@/features/customers/utils/customer-form-schema";

export function CustomerFormPage() {
  const { id } = useParams();
  const customerId = id ? Number(id) : 0;
  const isEdit = Number.isFinite(customerId) && customerId > 0;
  const navigate = useNavigate();
  const existing = useCustomer(isEdit ? customerId : 0);
  const createCustomer = useCreateCustomer();
  const updateCustomer = useUpdateCustomer(isEdit ? customerId : 0);

  const onSubmit = async (values: CustomerFormValues) => {
    const customer = isEdit
      ? await updateCustomer.mutateAsync(values)
      : await createCustomer.mutateAsync(values);
    toast.success(isEdit ? "Customer updated." : "Customer added.");
    void navigate(ROUTES.customers.detail(customer.id));
  };

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <header className="space-y-3">
        <PageBackLink
          to={isEdit ? ROUTES.customers.detail(customerId) : ROUTES.customers.root()}
        >
          {isEdit ? "Customer" : "Customers"}
        </PageBackLink>
        <h1 className="text-[32px] font-semibold tracking-tight text-foreground">
          {isEdit ? "Edit customer" : "Add customer"}
        </h1>
      </header>

      <div className="rounded-[24px] bg-card p-6">
        {isEdit ? (
          <QueryState
            isLoading={existing.isLoading}
            isError={existing.isError}
            errorMessage={getErrorMessage(existing.error, "Customer not found.")}
            onRetry={() => {
              void existing.refetch();
            }}
          >
            {existing.data ? (
              <CustomerForm
                // Remount per customer so the loaded values become the defaults.
                key={existing.data.id}
                defaultValues={{
                  name: existing.data.name,
                  email: existing.data.email,
                  phone: existing.data.phone,
                  notes: existing.data.notes,
                }}
                submitLabel="Save customer"
                onSubmit={onSubmit}
              />
            ) : null}
          </QueryState>
        ) : (
          <CustomerForm submitLabel="Add customer" onSubmit={onSubmit} />
        )}
      </div>
    </div>
  );
}
