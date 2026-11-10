import type { UseFormRegisterReturn } from "react-hook-form";

import { FormField } from "@/components/form-field";
import { PasswordInput } from "@/components/password-input";
import { Input } from "@/components/ui/input";

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
    className: "h-12 rounded-xl border-foreground bg-card px-4 text-base",
    ...registration,
  };

  return (
    <FormField id={id} label={label} error={error}>
      {type === "password" ? (
        <PasswordInput {...fieldProps} />
      ) : (
        <Input type={type} {...fieldProps} />
      )}
    </FormField>
  );
}
