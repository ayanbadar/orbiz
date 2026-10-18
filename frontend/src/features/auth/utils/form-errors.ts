import type { FieldPath, FieldValues, UseFormSetError } from "react-hook-form";

import { ApiError } from "@/lib/api";
import { readFieldErrors } from "@/lib/api/errors";

const FIELD_MAP: Record<string, string> = {
  email: "email",
  password: "password",
  password_confirm: "passwordConfirm",
  first_name: "firstName",
  last_name: "lastName",
  current_password: "currentPassword",
  new_password: "newPassword",
  new_password_confirm: "newPasswordConfirm",
  token: "token",
};

export function applyFieldErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
): boolean {
  if (!(error instanceof ApiError)) {
    return false;
  }

  const fields = readFieldErrors(error.details);
  let applied = false;
  for (const [key, message] of Object.entries(fields)) {
    const formKey = FIELD_MAP[key];
    if (!formKey) {
      continue;
    }
    setError(formKey as FieldPath<T>, { message });
    applied = true;
  }
  return applied;
}

export function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError && error.message.trim()) {
    return error.message;
  }
  return fallback;
}
