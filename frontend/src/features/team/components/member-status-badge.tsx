import { STATUS_TONES, StatusBadge } from "@/components/status-badge";

export function MemberStatusBadge({ isActive }: { isActive: boolean }) {
  return (
    <StatusBadge
      toneClassName={isActive ? STATUS_TONES.positive : STATUS_TONES.neutral}
    >
      {isActive ? "Active" : "Deactivated"}
    </StatusBadge>
  );
}
