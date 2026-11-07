import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import type { Order } from "@/features/orders/types";

type FormProps = {
  order: Order;
  pending: boolean;
  onSubmit: (notifyCustomer: boolean) => void;
};

function ConfirmForm({ order, pending, onSubmit }: FormProps) {
  // Opt-in on purpose: a seller may not want every customer emailed automatically.
  const [notify, setNotify] = useState(false);
  const email = order.customer.email;

  return (
    <form
      className="space-y-4"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(notify && Boolean(email));
      }}
    >
      <div className="flex items-start gap-3">
        <Checkbox
          id="notify-customer"
          checked={notify && Boolean(email)}
          disabled={!email}
          onCheckedChange={(checked) => setNotify(checked === true)}
          className="mt-0.5"
        />
        <div className="space-y-1">
          <Label htmlFor="notify-customer" className="leading-5">
            Email {email ? email : "the customer"} an order confirmation
          </Label>
          <p className="text-sm text-muted-foreground">
            {email
              ? "A copy of what they ordered. A PayPal payment request is a separate email."
              : "This customer has no email on file. Add one to send confirmations."}
          </p>
        </div>
      </div>
      <div className="flex justify-end gap-2">
        <DialogClose asChild>
          <Button type="button" variant="outline" className="rounded-[24px]">
            Cancel
          </Button>
        </DialogClose>
        <Button type="submit" disabled={pending} className="rounded-[24px]">
          {pending ? "Confirming…" : "Confirm order"}
        </Button>
      </div>
    </form>
  );
}

type Props = {
  order: Order;
  open: boolean;
  pending: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (notifyCustomer: boolean) => void;
};

export function OrderConfirmDialog({
  order,
  open,
  pending,
  onOpenChange,
  onSubmit,
}: Props) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Confirm this order?</DialogTitle>
          <DialogDescription>
            Stock will be deducted for each line of {order.number}.
          </DialogDescription>
        </DialogHeader>
        <ConfirmForm order={order} pending={pending} onSubmit={onSubmit} />
      </DialogContent>
    </Dialog>
  );
}
