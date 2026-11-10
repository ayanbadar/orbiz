import type { UserProfile } from "@/features/auth/types";

export function displayName(user: UserProfile): string {
  const name = [user.first_name, user.last_name].filter(Boolean).join(" ");
  return name || user.email;
}
