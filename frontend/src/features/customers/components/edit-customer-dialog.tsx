import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { toast } from "@/components/ui/sonner";
import { useUpdateCustomer } from "@/features/customers/api/customers.api";
import { CustomerForm } from "@/features/customers/components/customer-form";
import type { CustomerSummary } from "@/features/customers/types";

type Props = {
  customer: CustomerSummary;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

/** Edit a customer without leaving their profile. */
export function EditCustomerDialog({ customer, open, onOpenChange }: Props) {
  const updateCustomer = useUpdateCustomer(customer.id);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Edit customer</DialogTitle>
          <DialogDescription>
            Update {customer.name}&apos;s details.
          </DialogDescription>
        </DialogHeader>
        {/* Rendered only while open, so each opening starts from the latest values. */}
        {open ? (
          <CustomerForm
            defaultValues={{
              name: customer.name,
              email: customer.email,
              phone: customer.phone,
              notes: customer.notes,
            }}
            submitLabel="Save customer"
            onCancel={() => onOpenChange(false)}
            onSubmit={async (values) => {
              await updateCustomer.mutateAsync(values);
              toast.success("Customer updated.");
              onOpenChange(false);
            }}
          />
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
