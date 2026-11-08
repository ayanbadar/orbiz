import type { Member } from "@/features/team/types";

export function memberName(
  member: Pick<Member, "first_name" | "last_name" | "email">,
): string {
  const name = `${member.first_name} ${member.last_name}`.trim();
  return name || member.email;
}

export function memberRoleLabel(
  member: Pick<Member, "is_store_admin" | "role">,
): string {
  if (member.is_store_admin) return "Store admin";
  return member.role?.name ?? "No role";
}
