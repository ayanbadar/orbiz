import { STATUS_TONES, StatusBadge } from "@/components/status-badge";
import type { StoreStatus } from "@/features/stores/types";

const STATUS: Record<StoreStatus, { label: string; tone: string }> = {
  active: { label: "Active", tone: STATUS_TONES.positive },
  pending_payment: { label: "Unpaid", tone: STATUS_TONES.warning },
  suspended: { label: "Suspended", tone: STATUS_TONES.negative },
};

export function StoreStatusBadge({ status }: { status: StoreStatus }) {
  const { label, tone } = STATUS[status];
  return <StatusBadge toneClassName={tone}>{label}</StatusBadge>;
}
