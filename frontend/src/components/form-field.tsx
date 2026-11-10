import {
  cloneElement,
  isValidElement,
  type ReactElement,
  type ReactNode,
} from "react";

import { Label } from "@/components/ui/label";
import { cn } from "cn";

type FormFieldProps = {
  id: string;
  label: string;
  error?: string;
  className?: string;
  /**
   * Prefer a single control element (Input, etc.). When the child is a single
   * element, `id` / `aria-invalid` / `aria-describedby` are applied automatically.
   * For compound layouts, set those props on the focusable control yourself.
   */
  children: ReactNode;
};

/**
 * Shared labeled field with accessible error wiring.
 * Use for products, orders, and auth-style forms instead of one-off Field helpers.
 */
export function FormField({
  id,
  label,
  error,
  className,
  children,
}: FormFieldProps) {
  const errorId = `${id}-error`;

  const control = isValidElement(children)
    ? cloneElement(children as ReactElement<Record<string, unknown>>, {
        id: (children.props as { id?: string }).id ?? id,
        "aria-invalid":
          (children.props as { "aria-invalid"?: boolean | "true" | "false" })[
            "aria-invalid"
          ] ?? (Boolean(error) || undefined),
        "aria-describedby":
          (children.props as { "aria-describedby"?: string })[
            "aria-describedby"
          ] ?? (error ? errorId : undefined),
      })
    : children;

  return (
    <div className={cn("space-y-2", className)}>
      <Label htmlFor={id} className="text-sm font-semibold">
        {label}
      </Label>
      {control}
      {error ? (
        <p id={errorId} className="text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
