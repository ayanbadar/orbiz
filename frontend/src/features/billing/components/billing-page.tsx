import { CreditCard, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { QueryState } from "@/components/query-state";
import { STATUS_TONES, StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "@/components/ui/sonner";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { FormattedTime } from "@/components/formatted-time";
import { ROUTES } from "@/constants/routes";
import { useConfirmDialog } from "@/components/confirm-dialog";
import {
  useBilling,
  useCancelSubscription,
  useCheckout,
} from "@/features/billing/api/billing.api";
import type { Billing } from "@/features/billing/types";
import { getErrorMessage } from "@/features/auth/utils/form-errors";

function formatMoney(cents: number): string {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "USD",
  }).format(cents / 100);
}

function planBadge(billing: Billing) {
  if (billing.store_status === "suspended") {
    return { label: "Suspended", tone: STATUS_TONES.negative };
  }
  if (billing.store_status === "pending_payment") {
    return { label: "Payment required", tone: STATUS_TONES.warning };
  }
  if (billing.subscription_status === "canceled") {
    return { label: "Ends at period end", tone: STATUS_TONES.neutral };
  }
  return { label: "Active", tone: STATUS_TONES.positive };
}

export function BillingPage() {
  const billingQuery = useBilling();
  const checkout = useCheckout();
  const cancel = useCancelSubscription();
  const navigate = useNavigate();
  const { confirm, dialog } = useConfirmDialog();
  const [card, setCard] = useState("4242 4242 4242 4242");
  const [simulateFailure, setSimulateFailure] = useState(false);
  const billing = billingQuery.data;

  const onPay = async () => {
    try {
      const result = await checkout.mutateAsync({
        card_number: card.replace(/\s/g, ""),
        simulate_failure: simulateFailure,
      });
      toast.success("Payment received. Your store is active.");
      if (result.store_status === "active") {
        navigate(ROUTES.root(), { replace: true });
      }
    } catch (error) {
      toast.error(getErrorMessage(error, "The payment didn't go through."));
    }
  };

  const onCancel = async () => {
    const ok = await confirm({
      title: "Cancel renewal?",
      description:
        "You keep access until the end of the paid period. After that the store is locked until you pay again.",
      confirmLabel: "Cancel plan",
      variant: "destructive",
    });
    if (!ok) return;
    try {
      await cancel.mutateAsync();
      toast.success("Renewal cancelled.");
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not cancel."));
    }
  };

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-[28px] font-semibold tracking-tight sm:text-[32px]">
          Billing
        </h1>
        <p className="text-body">
          Your store runs on a flat $5/month plan. Payments here are a sandbox —
          no real card is charged.
        </p>
      </header>

      <QueryState
        isLoading={billingQuery.isLoading}
        isError={billingQuery.isError}
        errorMessage="Could not load billing."
        onRetry={() => void billingQuery.refetch()}
      >
        {billing ? (
          <div className="grid gap-6 lg:grid-cols-2">
            <Card className="rounded-[24px] bg-card py-0 ring-0">
              <CardHeader className="px-6 pt-6">
                <CardTitle className="flex items-center justify-between gap-3 text-xl font-semibold">
                  Orbiz Store plan
                  <StatusBadge toneClassName={planBadge(billing).tone}>
                    {planBadge(billing).label}
                  </StatusBadge>
                </CardTitle>
                <CardDescription>
                  Orders, products, customers and your team.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 px-6 pb-6">
                <p className="text-4xl font-black tracking-tight">
                  {formatMoney(billing.plan_price_cents)}
                  <span className="text-base font-medium text-body">
                    {" "}
                    / month
                  </span>
                </p>
                {billing.current_period_end ? (
                  <p className="text-sm text-body">
                    {billing.subscription_status === "canceled"
                      ? "Access until "
                      : "Renews on "}
                    <FormattedTime
                      value={billing.current_period_end}
                      variant="date"
                      className="font-semibold text-foreground"
                    />
                  </p>
                ) : (
                  <p className="text-sm text-body">
                    Not paid yet. Activate to start using your store.
                  </p>
                )}
                {billing.subscription_status === "active" &&
                billing.store_status === "active" ? (
                  <Button
                    type="button"
                    variant="outline"
                    className="rounded-[24px]"
                    disabled={cancel.isPending}
                    onClick={() => void onCancel()}
                  >
                    Cancel renewal
                  </Button>
                ) : null}
              </CardContent>
            </Card>

            {billing.store_status === "suspended" ? null : (
              <Card className="rounded-[24px] bg-card py-0 ring-0">
                <CardHeader className="px-6 pt-6">
                  <CardTitle className="flex items-center gap-2 text-xl font-semibold">
                    <CreditCard className="size-5" aria-hidden />
                    {billing.store_status === "pending_payment"
                      ? "Activate your store"
                      : "Pay early / renew"}
                  </CardTitle>
                  <CardDescription>
                    Sandbox checkout. Any card number works.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4 px-6 pb-6">
                  <div className="space-y-2">
                    <Label htmlFor="card">Card number</Label>
                    <Input
                      id="card"
                      inputMode="numeric"
                      autoComplete="off"
                      value={card}
                      onChange={(event) => setCard(event.target.value)}
                      className="h-12 rounded-xl border-foreground bg-card px-4 text-base"
                    />
                  </div>
                  {import.meta.env.DEV ? (
                    <label className="flex items-center gap-2 text-sm text-body">
                      <input
                        type="checkbox"
                        checked={simulateFailure}
                        onChange={(event) =>
                          setSimulateFailure(event.target.checked)
                        }
                      />
                      Simulate a declined card (dev only)
                    </label>
                  ) : null}
                  <Button
                    type="button"
                    disabled={checkout.isPending}
                    onClick={() => void onPay()}
                    className="h-12 w-full rounded-[24px] font-semibold"
                  >
                    {checkout.isPending
                      ? "Processing…"
                      : `Pay ${formatMoney(billing.plan_price_cents)}`}
                  </Button>
                  <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <ShieldCheck className="size-3.5" aria-hidden />
                    Mock payment — nothing is charged and no card is stored.
                  </p>
                </CardContent>
              </Card>
            )}

            <Card className="rounded-[24px] bg-card py-0 ring-0 lg:col-span-2">
              <CardHeader className="px-6 pt-6">
                <CardTitle className="text-xl font-semibold">
                  Payment history
                </CardTitle>
              </CardHeader>
              <CardContent className="px-2 pb-4">
                {billing.payments.length === 0 ? (
                  <p className="px-4 py-6 text-sm text-muted-foreground">
                    No payments yet.
                  </p>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow className="hover:bg-transparent">
                        <TableHead>Date</TableHead>
                        <TableHead>Reference</TableHead>
                        <TableHead>Amount</TableHead>
                        <TableHead>Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {billing.payments.map((payment) => (
                        <TableRow key={payment.id}>
                          <TableCell>
                            <FormattedTime
                              value={payment.created_at}
                              variant="datetime"
                            />
                          </TableCell>
                          <TableCell className="font-mono text-xs">
                            {payment.reference}
                          </TableCell>
                          <TableCell>
                            {formatMoney(payment.amount_cents)}
                          </TableCell>
                          <TableCell>
                            <StatusBadge
                              toneClassName={
                                payment.status === "succeeded"
                                  ? STATUS_TONES.positive
                                  : STATUS_TONES.negative
                              }
                            >
                              {payment.status === "succeeded"
                                ? "Paid"
                                : "Declined"}
                            </StatusBadge>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </div>
        ) : null}
      </QueryState>
      {dialog}
    </div>
  );
}
