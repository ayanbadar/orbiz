import type { FulfilmentStatus, PaymentStatus } from "@/features/orders/types";

const FULFILMENT_LABELS: Record<FulfilmentStatus, string> = {
  draft: "Draft",
  unfulfilled: "Unfulfilled",
  processing: "Processing",
  shipped: "Shipped",
  completed: "Completed",
  cancelled: "Cancelled",
};

const PAYMENT_LABELS: Record<PaymentStatus, string> = {
  unpaid: "Unpaid",
  pending: "Pending",
  paid: "Paid",
  failed: "Failed",
  cancelled: "Cancelled",
};

const FULFILMENT_STATUSES = Object.keys(
  FULFILMENT_LABELS,
) as FulfilmentStatus[];
const PAYMENT_STATUSES = Object.keys(PAYMENT_LABELS) as PaymentStatus[];

export function getFulfilmentLabel(status: FulfilmentStatus): string {
  return FULFILMENT_LABELS[status] ?? status;
}

export function getPaymentLabel(status: PaymentStatus): string {
  return PAYMENT_LABELS[status] ?? status;
}

/** Match status code or display label (case-insensitive). */
export function parseFulfilmentStatus(
  raw: string,
): FulfilmentStatus | null {
  const needle = raw.trim().toLowerCase();
  if (!needle) return null;
  const byCode = FULFILMENT_STATUSES.find((status) => status === needle);
  if (byCode) return byCode;
  return (
    FULFILMENT_STATUSES.find(
      (status) => FULFILMENT_LABELS[status].toLowerCase() === needle,
    ) ?? null
  );
}

export function parsePaymentStatus(raw: string): PaymentStatus | null {
  const needle = raw.trim().toLowerCase();
  if (!needle) return null;
  const byCode = PAYMENT_STATUSES.find((status) => status === needle);
  if (byCode) return byCode;
  return (
    PAYMENT_STATUSES.find(
      (status) => PAYMENT_LABELS[status].toLowerCase() === needle,
    ) ?? null
  );
}

/** Pill classes per DESIGN.md — never use lime CTA for paid. */
export function getFulfilmentBadgeClassName(status: FulfilmentStatus): string {
  switch (status) {
    case "completed":
      return "bg-muted text-positive-deep";
    case "unfulfilled":
    case "processing":
    case "shipped":
      return "bg-warning text-warning-content";
    case "cancelled":
      return "bg-negative-bg text-white";
    case "draft":
    default:
      return "bg-secondary text-muted-foreground";
  }
}

export function getPaymentBadgeClassName(status: PaymentStatus): string {
  switch (status) {
    case "paid":
      return "bg-muted text-positive-deep";
    case "pending":
      return "bg-warning text-warning-content";
    case "failed":
    case "cancelled":
      return "bg-negative-bg text-white";
    case "unpaid":
    default:
      return "bg-secondary text-muted-foreground";
  }
}
