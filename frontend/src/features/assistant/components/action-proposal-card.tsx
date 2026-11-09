import { useState } from "react";
import { Link } from "react-router-dom";
import { cn } from "cn";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { StatusBadge } from "@/components/status-badge";
import { toast } from "@/components/ui/sonner";
import { ROUTES } from "@/constants/routes";
import {
  useConfirmAssistantAction,
  useRejectAssistantAction,
} from "@/features/assistant/api/assistant.api";
import { getErrorMessage } from "@/features/auth/utils/form-errors";
import type { AssistantAction, AssistantPaymentMethod } from "@/features/assistant/types";

const TITLES: Record<AssistantAction["action_type"], (action: AssistantAction) => string> = {
  refund: (action) => `Refund order ${action.order?.number ?? ""}?`,
  capture: (action) => `Capture payment for order ${action.order?.number ?? ""}?`,
  import_product: (action) =>
    `Import "${action.payload.channel3_payload?.title ?? "this product"}" as a new product?`,
  request_payment: (action) => `How should ${action.order?.number ?? "this order"} be paid?`,
};

const PAYMENT_METHODS: { method: AssistantPaymentMethod; label: string }[] = [
  { method: "email_link", label: "Email the pay-now link" },
  { method: "invoice", label: "Send a PayPal invoice" },
  { method: "checkout", label: "Give me a pay-now link" },
];

const STATUS_TONE: Record<AssistantAction["status"], string> = {
  pending: "bg-muted text-foreground",
  confirmed: "bg-primary/10 text-primary",
  rejected: "bg-destructive/10 text-destructive",
  expired: "bg-muted text-muted-foreground",
};

export function ActionProposalCard({ action }: { action: AssistantAction }) {
  const confirmAction = useConfirmAssistantAction();
  const rejectAction = useRejectAssistantAction();
  const [amount, setAmount] = useState(action.payload.amount ?? "");
  const [sku, setSku] = useState(action.payload.sku ?? "");
  const [price, setPrice] = useState(action.payload.price ?? "");
  const [stockQuantity, setStockQuantity] = useState(
    String(action.payload.stock_quantity ?? ""),
  );
  const [error, setError] = useState("");
  const [pendingMethod, setPendingMethod] = useState<AssistantPaymentMethod | null>(null);

  const isPending = action.status === "pending";
  const isConfirmed = action.status === "confirmed";
  const isRejected = action.status === "rejected";
  const needsProductFields =
    action.action_type === "import_product" && (!sku || !price || !stockQuantity);

  const handleChooseMethod = async (method: AssistantPaymentMethod) => {
    setError("");
    setPendingMethod(method);
    try {
      await confirmAction.mutateAsync({ id: action.id, overrides: { method } });
      toast.success("Done.");
    } catch (confirmError) {
      setError(getErrorMessage(confirmError, "Could not do that."));
    } finally {
      setPendingMethod(null);
    }
  };

  const handleConfirm = async () => {
    setError("");
    try {
      await confirmAction.mutateAsync({
        id: action.id,
        overrides:
          action.action_type === "refund"
            ? { amount: amount || undefined }
            : action.action_type === "import_product"
              ? {
                  sku,
                  price,
                  stock_quantity: stockQuantity ? Number(stockQuantity) : undefined,
                }
              : {},
      });
      toast.success("Confirmed.");
    } catch (confirmError) {
      setError(getErrorMessage(confirmError, "Could not confirm this action."));
    }
  };

  const handleReject = async () => {
    try {
      await rejectAction.mutateAsync(action.id);
    } catch (rejectError) {
      toast.error(getErrorMessage(rejectError, "Could not dismiss this action."));
    }
  };

  return (
    <Card className="max-w-md">
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center justify-between gap-2">
          <span>{TITLES[action.action_type](action)}</span>
          <StatusBadge toneClassName={STATUS_TONE[action.status]}>{action.status}</StatusBadge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        {action.order ? (
          <Link
            to={ROUTES.orders.detail(action.order.id)}
            className="text-primary underline-offset-4 hover:underline"
          >
            View {action.order.number}
          </Link>
        ) : null}

        {action.action_type === "refund" && isPending ? (
          <div className="space-y-1">
            <Label htmlFor={`refund-amount-${action.id}`}>
              Amount (leave blank for a full refund)
            </Label>
            <Input
              id={`refund-amount-${action.id}`}
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
              placeholder="Full amount"
            />
          </div>
        ) : null}

        {action.action_type === "import_product" ? (
          <div className="space-y-3">
            {action.payload.channel3_payload?.image_url ? (
              <img
                src={action.payload.channel3_payload.image_url}
                alt=""
                className="h-24 w-24 rounded-md object-cover"
              />
            ) : null}
            {action.payload.channel3_payload?.brand ? (
              <p className="text-muted-foreground">{action.payload.channel3_payload.brand}</p>
            ) : null}
            {isPending ? (
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label htmlFor={`sku-${action.id}`}>SKU</Label>
                  <Input id={`sku-${action.id}`} value={sku} onChange={(e) => setSku(e.target.value)} />
                </div>
                <div className="space-y-1">
                  <Label htmlFor={`price-${action.id}`}>Price</Label>
                  <Input
                    id={`price-${action.id}`}
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                  />
                </div>
                <div className="col-span-2 space-y-1">
                  <Label htmlFor={`stock-${action.id}`}>Stock quantity</Label>
                  <Input
                    id={`stock-${action.id}`}
                    type="number"
                    min={0}
                    value={stockQuantity}
                    onChange={(e) => setStockQuantity(e.target.value)}
                  />
                </div>
              </div>
            ) : null}
          </div>
        ) : null}

        {action.result_message ? <p className="text-muted-foreground">{action.result_message}</p> : null}
        {error ? (
          <p className="text-destructive" role="alert">
            {error}
          </p>
        ) : null}
      </CardContent>
      {action.action_type === "request_payment" ? (
        <CardFooter className="flex flex-wrap items-center gap-2">
          {PAYMENT_METHODS.map(({ method, label }) => {
            const chosen = action.payload.method === method;
            const isWorking = confirmAction.isPending && pendingMethod === method;
            return (
              <Button
                key={method}
                size="sm"
                variant={chosen ? "default" : "outline"}
                onClick={() => void handleChooseMethod(method)}
                disabled={!isPending || confirmAction.isPending}
                className={cn(chosen && "disabled:opacity-100 ring-2 ring-primary/30")}
              >
                {isWorking ? "Working…" : chosen ? `${label} ✓` : label}
              </Button>
            );
          })}
          {isPending ? (
            <Button
              size="sm"
              variant="ghost"
              onClick={handleReject}
              disabled={rejectAction.isPending}
              className="text-muted-foreground"
            >
              {rejectAction.isPending ? "…" : "Never mind"}
            </Button>
          ) : isRejected ? (
            <span className="text-xs text-muted-foreground">Dismissed</span>
          ) : null}
        </CardFooter>
      ) : (
        <CardFooter className="flex gap-2">
          <Button
            size="sm"
            onClick={handleConfirm}
            disabled={!isPending || confirmAction.isPending || needsProductFields}
            className={cn(isConfirmed && "disabled:opacity-100 ring-2 ring-primary/30")}
          >
            {confirmAction.isPending ? "Confirming…" : isConfirmed ? "Confirmed" : "Confirm"}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={handleReject}
            disabled={!isPending || rejectAction.isPending}
            className={cn(
              isRejected && "border-destructive/40 bg-destructive/10 text-destructive disabled:opacity-100",
            )}
          >
            {rejectAction.isPending ? "Rejecting…" : isRejected ? "Rejected" : "Reject"}
          </Button>
        </CardFooter>
      )}
    </Card>
  );
}
