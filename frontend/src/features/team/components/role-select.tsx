import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Role } from "@/features/team/types";

/** Role picker used by the invite and edit dialogs. Value is the role id as a string. */
export function RoleSelect({
  id,
  roles,
  value,
  onChange,
  invalid,
}: {
  id: string;
  roles: Role[];
  value: string;
  onChange: (value: string) => void;
  invalid?: boolean;
}) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger
        id={id}
        aria-invalid={invalid || undefined}
        className="h-12 w-full min-w-0 rounded-xl border-foreground bg-card px-3 text-base"
      >
        <SelectValue placeholder="Choose a role…" />
      </SelectTrigger>
      <SelectContent position="popper" align="start">
        {roles.map((role) => (
          <SelectItem key={role.id} value={String(role.id)}>
            {role.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
