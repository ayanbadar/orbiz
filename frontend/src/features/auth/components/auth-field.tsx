import type { UseFormRegisterReturn } from "react-hook-form";

import { PasswordInput } from "@/components/password-input";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type AuthFieldProps = {
  id: string;
  label: string;
  type?: string;
  autoComplete?: string;
  error?: string;
  registration: UseFormRegisterReturn;
};

export function AuthField({
  id,
  label,
  type = "text",
  autoComplete,
  error,
  registration,
}: AuthFieldProps) {
  const fieldProps = {
    id,
    autoComplete,
    "aria-invalid": Boolean(error) || undefined,
    className: "h-12 rounded-xl border-foreground bg-card px-4 text-base",
    ...registration,
  };

  return (
    <div className="space-y-2">
      <Label htmlFor={id} className="text-sm font-semibold">
        {label}
      </Label>
      {type === "password" ? (
        <PasswordInput {...fieldProps} />
      ) : (
        <Input type={type} {...fieldProps} />
      )}
      {error ? (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
