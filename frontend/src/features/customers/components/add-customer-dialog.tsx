import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { toast } from "@/components/ui/sonner";
import { useCreateCustomer } from "@/features/customers/api/customers.api";
import { CustomerForm } from "@/features/customers/components/customer-form";
import type { CustomerSummary } from "@/features/customers/types";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: (customer: CustomerSummary) => void;
  description?: string;
};

/** Create a customer without leaving the current screen (e.g. the order form). */
export function AddCustomerDialog({
  open,
  onOpenChange,
  onCreated,
  description = "They are selected on this order once saved.",
}: Props) {
  const createCustomer = useCreateCustomer();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Add customer</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        {/* Rendered only while open, so each opening starts with an empty form. */}
        {open ? (
          <CustomerForm
            submitLabel="Add customer"
            onCancel={() => onOpenChange(false)}
            onSubmit={async (values) => {
              const customer = await createCustomer.mutateAsync(values);
              toast.success(`${customer.name} added.`);
              onCreated(customer);
              onOpenChange(false);
            }}
          />
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
