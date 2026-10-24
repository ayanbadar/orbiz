import type { FieldPath, FieldValues, UseFormSetError } from "react-hook-form";

import { ApiError } from "@/lib/api";
import {
  isGenericHttpErrorMessage,
  readApiErrorMessage,
  readFieldErrors,
} from "@/lib/api/errors";

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
  name: "name",
  sku: "sku",
  price: "price",
  description: "description",
  stock_quantity: "stock_quantity",
  low_stock_threshold: "low_stock_threshold",
  image_url: "image_url",
  is_active: "is_active",
  currency: "currency",
  timezone: "timezone",
  business_type: "business_type",
  delta: "delta",
  reason: "reason",
  customer_id: "customer_id",
  lines: "lines",
  delivery_notes: "delivery_notes",
  internal_notes: "internal_notes",
  source_message: "source_message",
};

export function applyFieldErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  fieldMap: Record<string, string> = FIELD_MAP,
): boolean {
  if (!(error instanceof ApiError)) {
    return false;
  }

  const fields = readFieldErrors(error.details);
  let applied = false;
  for (const [key, message] of Object.entries(fields)) {
    const formKey = (fieldMap[key] ?? key) as FieldPath<T>;
    setError(formKey, { message });
    applied = true;
  }
  return applied;
}

export function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    const message = error.message.trim();
    if (message && !isGenericHttpErrorMessage(message)) {
      return message;
    }
    const fromDetails = readApiErrorMessage(error.details)?.trim();
    if (fromDetails && !isGenericHttpErrorMessage(fromDetails)) {
      return fromDetails;
    }
  } else if (error instanceof Error) {
    const message = error.message.trim();
    if (message && !isGenericHttpErrorMessage(message)) {
      return message;
    }
  }
  return fallback;
}
