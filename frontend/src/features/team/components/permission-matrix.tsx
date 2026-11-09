import { Checkbox } from "@/components/ui/checkbox";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { PermissionCatalog } from "@/features/team/types";

/**
 * Resources × actions grid. "View" is the base permission: granting any other
 * action also grants view, and removing view removes the rest.
 */
export function PermissionMatrix({
  catalog,
  value,
  onChange,
}: {
  catalog: PermissionCatalog;
  value: string[];
  onChange: (next: string[]) => void;
}) {
  const selected = new Set(value);

  const toggle = (resource: string, action: string, checked: boolean) => {
    const next = new Set(selected);
    const code = `${resource}.${action}`;
    if (checked) {
      next.add(code);
      next.add(`${resource}.read`);
    } else if (action === "read") {
      for (const a of catalog.actions) next.delete(`${resource}.${a.key}`);
    } else {
      next.delete(code);
    }
    onChange(catalog.permissions.filter((p) => next.has(p)));
  };

  return (
    <div className="rounded-xl border border-border">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead>Area</TableHead>
            {catalog.actions.map((action) => (
              <TableHead key={action.key} className="text-center">
                {action.label}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {catalog.resources.map((resource) => (
            <TableRow key={resource.key}>
              <TableCell className="font-semibold">{resource.label}</TableCell>
              {catalog.actions.map((action) => {
                const code = `${resource.key}.${action.key}`;
                return (
                  <TableCell key={action.key} className="text-center">
                    <Checkbox
                      checked={selected.has(code)}
                      aria-label={`${resource.label}: ${action.label}`}
                      onCheckedChange={(checked) =>
                        toggle(resource.key, action.key, checked === true)
                      }
                    />
                  </TableCell>
                );
              })}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
